from PyQt6.QtWidgets import QDoubleSpinBox, QListWidget

from src.ui.audio_editor.selection import AudioEditorSelectionController
from src.ui.audio_editor.session import AudioEditorSession


class _Waveform:
    def __init__(self):
        self.selection = None
        self.chunk_ranges = None

    def set_selection(self, start, end):
        self.selection = (start, end)

    def set_chunk_ranges(self, ranges, active_index):
        self.chunk_ranges = (ranges, active_index)


def _controller(qtbot):
    session = AudioEditorSession()
    session.preview_ranges = [
        {"output_start": 0.0, "output_end": 1.5},
        {"output_start": 1.5, "output_end": 3.0},
    ]
    session.active_chunk_index = 0
    waveform = _Waveform()
    chunks = QListWidget()
    start = QDoubleSpinBox()
    end = QDoubleSpinBox()
    qtbot.addWidget(chunks)
    return session, waveform, chunks, start, end, AudioEditorSelectionController(
        session, waveform, chunks, start, end, lambda value: f"{value:.1f}s"
    )


def test_selection_controller_refreshes_chunk_list_and_active_range(qtbot):
    _session, waveform, chunks, start, end, controller = _controller(qtbot)

    controller.refresh_chunks()
    controller.sync_active_selection()

    assert chunks.count() == 2
    assert chunks.currentRow() == 0
    assert chunks.item(0).text() == "1. 0.0s - 1.5s"
    assert (start.value(), end.value()) == (0.0, 1.5)
    assert waveform.selection == (0.0, 1.5)


def test_selection_controller_normalizes_spin_ranges_and_updates_waveform(qtbot):
    session, waveform, _chunks, start, end, controller = _controller(qtbot)

    start.setValue(2.8)
    end.setValue(1.7)
    changed = controller.from_spins()

    assert changed is True
    assert (session.selection_start, session.selection_end) == (1.7, 2.8)
    assert waveform.selection == (1.7, 2.8)
    assert session.has_unsaved_changes is True


def test_selection_controller_selects_chunk_from_waveform(qtbot):
    session, waveform, chunks, _start, _end, controller = _controller(qtbot)
    controller.refresh_chunks()

    assert controller.select_waveform_chunk(1) is True

    assert session.active_chunk_index == 1
    assert chunks.currentRow() == 1
    assert waveform.chunk_ranges[1] == 1
