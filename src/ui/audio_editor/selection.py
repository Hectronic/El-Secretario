"""Selection and chunk-list synchronization for the waveform editor."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem


class AudioEditorSelectionController:
    """Keep waveform, chunk list and selection spin boxes in one state contract."""

    def __init__(self, session, waveform, chunk_list, start_spin, end_spin, formatter):
        self.session = session
        self.waveform = waveform
        self.chunk_list = chunk_list
        self.start_spin = start_spin
        self.end_spin = end_spin
        self.formatter = formatter
        self.suppress_signals = False

    def refresh_chunks(self):
        self.suppress_signals = True
        self.chunk_list.clear()
        for index, chunk in enumerate(self.session.preview_ranges):
            item = QListWidgetItem(
                f"{index + 1}. {self.formatter(chunk['output_start'])} - {self.formatter(chunk['output_end'])}"
            )
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.chunk_list.addItem(item)
        if 0 <= self.session.active_chunk_index < self.chunk_list.count():
            self.chunk_list.setCurrentRow(self.session.active_chunk_index)
        self.suppress_signals = False

    def sync_active_selection(self):
        active = self.session.active_range()
        if active is None:
            self._set_selection_widgets(0.0, 0.0, None)
            return
        self._set_selection_widgets(active["output_start"], active["output_end"], active)

    def from_waveform(self, start, end):
        if self.suppress_signals:
            return False
        self.session.set_selection(start, end)
        self._set_spin_values(start, end)
        self.session.mark_dirty()
        return True

    def from_spins(self):
        if self.suppress_signals:
            return False
        start, end = sorted((self.start_spin.value(), self.end_spin.value()))
        self.session.set_selection(start, end)
        self.waveform.set_selection(start, end)
        self.session.mark_dirty()
        return True

    def select_chunk(self, row):
        if self.suppress_signals or row < 0:
            return False
        self.session.active_chunk_index = row
        self.waveform.set_chunk_ranges(self.session.preview_ranges, row)
        self.sync_active_selection()
        return True

    def select_waveform_chunk(self, index):
        if not 0 <= index < len(self.session.preview_ranges):
            return False
        if self.chunk_list.currentRow() != index:
            self.chunk_list.setCurrentRow(index)
        # The Qt signal normally reaches ``select_chunk`` through the widget,
        # but calling it here keeps this controller correct when used directly.
        self.select_chunk(index)
        return True

    def _set_selection_widgets(self, start, end, active):
        self._set_spin_values(start, end, active)
        self.waveform.set_selection(start, end)

    def _set_spin_values(self, start, end, active=None):
        self.start_spin.blockSignals(True)
        self.end_spin.blockSignals(True)
        if active is not None:
            self.start_spin.setRange(active["output_start"], active["output_end"])
            self.end_spin.setRange(active["output_start"], active["output_end"])
        self.start_spin.setValue(start)
        self.end_spin.setValue(end)
        self.start_spin.blockSignals(False)
        self.end_spin.blockSignals(False)
