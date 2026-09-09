import numpy as np
import pytest

from src.ui.audio_editor.session import AudioEditorSession


def _session():
    session = AudioEditorSession()
    session.load_audio(np.arange(16, dtype=np.float32).reshape(-1, 1), 4)
    return session


def test_session_cut_reorders_preview_and_restores_with_undo_redo():
    session = _session()
    session.set_selection(1.0, 3.0)

    session.cut_selection()

    assert [(chunk.source_start, chunk.source_end) for chunk in session.chunks] == [(0.0, 1.0), (3.0, 4.0)]
    assert session.has_unsaved_changes is True
    assert len(session.preview_audio) == 8

    assert session.undo() is True
    assert [(chunk.source_start, chunk.source_end) for chunk in session.chunks] == [(0.0, 4.0)]
    assert session.redo() is True
    assert [(chunk.source_start, chunk.source_end) for chunk in session.chunks] == [(0.0, 1.0), (3.0, 4.0)]


def test_session_rejects_selection_outside_the_active_chunk():
    session = _session()
    session.set_selection(-0.1, 1.0)

    with pytest.raises(ValueError, match="active chunk"):
        session.cut_selection()


def test_session_boundary_drag_is_one_undoable_operation():
    session = _session()
    session.set_selection(1.0, 2.0)
    session.split_selection()
    session.active_chunk_index = 0
    session.boundary_drag_history_pending = True

    assert session.adjust_active_boundary("right", 0.5) is True
    assert session.chunks[0].source_end == 0.5
    assert session.undo() is True
    assert session.chunks[0].source_end == 1.0
