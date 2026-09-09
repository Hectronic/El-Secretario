"""Non-Qt editing session state for :mod:`audio_editor.widget`."""

import numpy as np

from .editing_state import (
    AudioChunk,
    ChunkEditHistory,
    adjust_chunk_boundary,
    build_preview_ranges,
    split_chunk,
)


class AudioEditorSession:
    """Own editable audio/chunk state independently from Qt presentation."""

    def __init__(self):
        self.current_audio = None
        self.sample_rate = 16000
        self.duration = 0.0
        self.preview_audio = None
        self.preview_ranges = []
        self.chunks = []
        self.active_chunk_index = -1
        self.selection_start = 0.0
        self.selection_end = 0.0
        self.has_unsaved_changes = False
        self.history = ChunkEditHistory()
        self.boundary_drag_history_pending = False

    def load_audio(self, audio, sample_rate):
        self.current_audio = audio
        self.sample_rate = int(sample_rate)
        self.duration = float(len(audio) / sample_rate) if len(audio) else 0.0
        self.chunks = [AudioChunk(0.0, self.duration)] if self.duration else []
        self.active_chunk_index = 0 if self.chunks else -1
        self.selection_start = 0.0
        self.selection_end = 0.0
        self.clear_history()
        self.mark_clean()
        return self.rebuild_preview()

    def rebuild_preview(self):
        if not self.chunks or self.current_audio is None:
            self.preview_audio = None
            self.preview_ranges = []
            return self.preview_audio
        self.preview_ranges = build_preview_ranges(self.chunks)
        parts = []
        for chunk in self.chunks:
            start = max(0, min(round(chunk.source_start * self.sample_rate), len(self.current_audio)))
            end = max(start, min(round(chunk.source_end * self.sample_rate), len(self.current_audio)))
            part = self.current_audio[start:end]
            if len(part):
                parts.append(part)
        self.preview_audio = (
            np.concatenate(parts, axis=0)
            if parts else np.zeros((0, self.current_audio.shape[1]), dtype=np.float32)
        )
        return self.preview_audio

    def active_range(self):
        if 0 <= self.active_chunk_index < len(self.preview_ranges):
            return self.preview_ranges[self.active_chunk_index]
        return None

    def set_selection(self, start, end):
        self.selection_start = float(start)
        self.selection_end = float(end)

    def selection_range(self):
        active = self.active_range()
        if active is None:
            raise ValueError("Select a range first.")
        if self.selection_end <= self.selection_start:
            raise ValueError("Select a range first.")
        if self.selection_start < active["output_start"] or self.selection_end > active["output_end"]:
            raise ValueError("The selection must stay inside the active chunk.")
        return active

    def _before_edit(self):
        self.history.push(self.chunks, self.active_chunk_index)

    def _finish_edit(self):
        self.rebuild_preview()
        self.mark_dirty()

    def split_selection(self):
        active = self.selection_range()
        self._before_edit()
        left, middle, right = split_chunk(
            self.chunks[self.active_chunk_index], active, self.selection_start, self.selection_end, keep_middle=True
        )
        replacement = [chunk for chunk in (left, middle, right) if chunk]
        self.chunks[self.active_chunk_index:self.active_chunk_index + 1] = replacement
        self.active_chunk_index = min(self.active_chunk_index + (1 if left else 0), len(self.chunks) - 1)
        self._finish_edit()

    def cut_selection(self):
        active = self.selection_range()
        self._before_edit()
        left, _, right = split_chunk(
            self.chunks[self.active_chunk_index], active, self.selection_start, self.selection_end, keep_middle=False
        )
        self.chunks[self.active_chunk_index:self.active_chunk_index + 1] = [chunk for chunk in (left, right) if chunk]
        self.active_chunk_index = min(self.active_chunk_index, max(0, len(self.chunks) - 1))
        self._finish_edit()

    def delete_active_chunk(self):
        if not (0 <= self.active_chunk_index < len(self.chunks)):
            return False
        if len(self.chunks) == 1:
            raise ValueError("You need at least one chunk.")
        self._before_edit()
        del self.chunks[self.active_chunk_index]
        self.active_chunk_index = min(self.active_chunk_index, len(self.chunks) - 1)
        self._finish_edit()
        return True

    def move_active_chunk(self, offset):
        target = self.active_chunk_index + int(offset)
        if not (0 <= self.active_chunk_index < len(self.chunks)) or not (0 <= target < len(self.chunks)):
            return False
        self._before_edit()
        self.chunks[self.active_chunk_index], self.chunks[target] = self.chunks[target], self.chunks[self.active_chunk_index]
        self.active_chunk_index = target
        self._finish_edit()
        return True

    def adjust_active_boundary(self, side, boundary_time):
        if not (0 <= self.active_chunk_index < len(self.chunks)) or not self.preview_ranges:
            return False
        if self.boundary_drag_history_pending:
            self._before_edit()
            self.boundary_drag_history_pending = False
        if not adjust_chunk_boundary(
            self.chunks, self.active_chunk_index, self.preview_ranges, side, boundary_time, self.duration
        ):
            return False
        self._finish_edit()
        return True

    def reset(self):
        if self.duration <= 0:
            return False
        self._before_edit()
        self.chunks = [AudioChunk(0.0, self.duration)]
        self.active_chunk_index = 0
        self._finish_edit()
        return True

    def undo(self):
        restored = self.history.undo(self.chunks, self.active_chunk_index)
        if restored is None:
            return False
        self.chunks, self.active_chunk_index = restored
        self._finish_edit()
        return True

    def redo(self):
        restored = self.history.redo(self.chunks, self.active_chunk_index)
        if restored is None:
            return False
        self.chunks, self.active_chunk_index = restored
        self._finish_edit()
        return True

    def accept_saved_preview(self, duration):
        self.duration = float(duration)
        self.current_audio = self.preview_audio
        self.chunks = [AudioChunk(0.0, self.duration)]
        self.active_chunk_index = 0
        self.clear_history()
        self.mark_clean()
        self.rebuild_preview()

    def mark_dirty(self):
        self.has_unsaved_changes = True

    def mark_clean(self):
        self.has_unsaved_changes = False

    def clear_history(self):
        self.history.clear()
        self.boundary_drag_history_pending = False
