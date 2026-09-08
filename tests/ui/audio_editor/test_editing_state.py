from src.ui.audio_editor.editing_state import (
    AudioChunk,
    ChunkEditHistory,
    adjust_chunk_boundary,
    build_preview_ranges,
    split_chunk,
)


def test_preview_ranges_follow_chunk_order_and_source_positions():
    ranges = build_preview_ranges([AudioChunk(2.0, 3.5), AudioChunk(0.0, 1.0)])

    assert ranges == [
        {
            "output_start": 0.0,
            "output_end": 1.5,
            "source_start": 2.0,
            "source_end": 3.5,
            "chunk_index": 0,
        },
        {
            "output_start": 1.5,
            "output_end": 2.5,
            "source_start": 0.0,
            "source_end": 1.0,
            "chunk_index": 1,
        },
    ]


def test_split_chunk_maps_output_selection_back_to_source():
    chunk = AudioChunk(10.0, 14.0)
    active_range = {"output_start": 2.0, "output_end": 6.0}

    left, middle, right = split_chunk(chunk, active_range, 3.0, 5.0, keep_middle=True)

    assert (left.source_start, left.source_end) == (10.0, 11.0)
    assert (middle.source_start, middle.source_end) == (11.0, 13.0)
    assert (right.source_start, right.source_end) == (13.0, 14.0)


def test_boundary_adjustment_preserves_neighboring_continuity():
    chunks = [AudioChunk(0.0, 2.0), AudioChunk(2.0, 4.0)]
    ranges = build_preview_ranges(chunks)

    changed = adjust_chunk_boundary(chunks, 0, ranges, "right", 1.5, 4.0)

    assert changed is True
    assert chunks[0].source_end == 1.5
    assert chunks[1].source_start == 1.5


def test_history_restores_chunk_state_for_undo_and_redo():
    history = ChunkEditHistory()
    chunks = [AudioChunk(0.0, 4.0)]
    history.push(chunks, 0)
    chunks = [AudioChunk(0.0, 1.0), AudioChunk(3.0, 4.0)]

    restored = history.undo(chunks, 1)
    redone = history.redo(*restored)

    assert [(chunk.source_start, chunk.source_end) for chunk in restored[0]] == [(0.0, 4.0)]
    assert [(chunk.source_start, chunk.source_end) for chunk in redone[0]] == [(0.0, 1.0), (3.0, 4.0)]
