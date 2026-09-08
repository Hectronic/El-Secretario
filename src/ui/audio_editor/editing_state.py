"""Pure segment-editing state used by the waveform editor."""

from dataclasses import dataclass


MIN_CHUNK_DURATION = 0.001


@dataclass
class AudioChunk:
    source_start: float
    source_end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)


def build_preview_ranges(chunks):
    cursor = 0.0
    ranges = []
    for index, chunk in enumerate(chunks):
        output_start = cursor
        cursor += chunk.duration
        ranges.append(
            {
                "output_start": output_start,
                "output_end": cursor,
                "source_start": chunk.source_start,
                "source_end": chunk.source_end,
                "chunk_index": index,
            }
        )
    return ranges


def split_chunk(chunk, active_range, selection_start, selection_end, keep_middle):
    """Map an output selection to up to three source chunks."""
    output_start = active_range["output_start"]
    selection_start = max(output_start, selection_start)
    selection_end = min(active_range["output_end"], selection_end)
    if selection_end <= selection_start:
        raise ValueError("The selection must have a positive duration.")

    left_duration = selection_start - output_start
    middle_duration = selection_end - selection_start
    right_duration = active_range["output_end"] - selection_end
    left = (
        AudioChunk(chunk.source_start, chunk.source_start + left_duration)
        if left_duration > MIN_CHUNK_DURATION
        else None
    )
    middle = (
        AudioChunk(
            chunk.source_start + left_duration,
            chunk.source_start + left_duration + middle_duration,
        )
        if middle_duration > MIN_CHUNK_DURATION
        else None
    )
    right = (
        AudioChunk(chunk.source_end - right_duration, chunk.source_end)
        if right_duration > MIN_CHUNK_DURATION
        else None
    )
    return left, middle if keep_middle else None, right


def adjust_chunk_boundary(chunks, active_index, preview_ranges, side, boundary_time, duration):
    """Retiming one boundary while preserving adjacent chunk continuity."""
    if not (0 <= active_index < len(chunks)) or not preview_ranges:
        return False
    active_range = preview_ranges[active_index]
    boundary_time = float(boundary_time)
    if side == "left":
        current_chunk = chunks[active_index]
        if active_index > 0:
            previous_range = preview_ranges[active_index - 1]
            boundary_time = max(
                previous_range["output_start"] + MIN_CHUNK_DURATION,
                min(boundary_time, active_range["output_end"] - MIN_CHUNK_DURATION),
            )
            previous_chunk = chunks[active_index - 1]
            total = previous_chunk.duration + current_chunk.duration
            left_duration = max(MIN_CHUNK_DURATION, boundary_time - previous_range["output_start"])
            right_duration = max(MIN_CHUNK_DURATION, total - left_duration)
            previous_chunk.source_end = previous_chunk.source_start + left_duration
            current_chunk.source_start = current_chunk.source_end - right_duration
        else:
            current_chunk.source_start = max(
                0.0, min(boundary_time, current_chunk.source_end - MIN_CHUNK_DURATION)
            )
    elif side == "right":
        current_chunk = chunks[active_index]
        if active_index < len(chunks) - 1:
            next_range = preview_ranges[active_index + 1]
            boundary_time = max(
                active_range["output_start"] + MIN_CHUNK_DURATION,
                min(boundary_time, next_range["output_end"] - MIN_CHUNK_DURATION),
            )
            next_chunk = chunks[active_index + 1]
            total = current_chunk.duration + next_chunk.duration
            left_duration = max(MIN_CHUNK_DURATION, boundary_time - active_range["output_start"])
            right_duration = max(MIN_CHUNK_DURATION, total - left_duration)
            current_chunk.source_end = current_chunk.source_start + left_duration
            next_chunk.source_start = next_chunk.source_end - right_duration
        else:
            current_chunk.source_end = max(
                current_chunk.source_start + MIN_CHUNK_DURATION,
                min(boundary_time, duration),
            )
    else:
        return False
    return True


def snapshot_chunks(chunks, active_index):
    return ([(chunk.source_start, chunk.source_end) for chunk in chunks], int(active_index))


def restore_chunks(snapshot):
    chunk_pairs, active_index = snapshot
    chunks = [AudioChunk(float(start), float(end)) for start, end in chunk_pairs]
    return chunks, max(-1, min(int(active_index), len(chunks) - 1))


class ChunkEditHistory:
    """Bounded undo/redo history for a list of source chunks."""

    def __init__(self, limit=200):
        self.limit = limit
        self.undo_stack = []
        self.redo_stack = []

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()

    def push(self, chunks, active_index):
        snapshot = snapshot_chunks(chunks, active_index)
        if self.undo_stack and self.undo_stack[-1] == snapshot:
            return
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.limit:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, chunks, active_index):
        if not self.undo_stack:
            return None
        self.redo_stack.append(snapshot_chunks(chunks, active_index))
        return restore_chunks(self.undo_stack.pop())

    def redo(self, chunks, active_index):
        if not self.redo_stack:
            return None
        self.undo_stack.append(snapshot_chunks(chunks, active_index))
        return restore_chunks(self.redo_stack.pop())
