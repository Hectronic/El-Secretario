# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Context panel used by chat widgets to scope notebook, tag and date filters."""

from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from src.ui.context_manager.entries import entry_descriptors, fetch_context_records
from src.ui.context_manager.state import ContextPanelState, state_from_dict, status_labels
from src.ui.context_manager.view import build_context_panel_view


class ContextManagerPanel(QWidget):
    """Side panel for chat widgets to manage synchronized search context."""

    context_changed = pyqtSignal()
    toggle_requested = pyqtSignal()
    add_context_requested = pyqtSignal()
    reset_extra_context_requested = pyqtSignal()
    clear_chat_requested = pyqtSignal()
    COLLAPSED_WIDTH = 44

    def __init__(self, db, notebook_db, parent=None, show_header=True, interactive=True):
        super().__init__(parent)
        self.db = db
        self.notebook_db = notebook_db
        self._collapsed = False
        self._show_header = bool(show_header)
        self._interactive = bool(interactive)

        # Selection state synced from the main app.
        self.current_week_monday = None
        self.current_date_filter = None
        self.active_global_tags = []
        self.forced_records = []

        self.init_ui()
        self.load_notebooks()

    def init_ui(self):
        """Build the Qt shell through the focused context-manager view owner."""
        build_context_panel_view(self)

    def load_notebooks(self):
        self.nb_list.clear()
        notebooks = self.notebook_db.get_notebooks()
        for nb in notebooks:
            item = QListWidgetItem(f"📓 {nb['name']}")
            item.setData(Qt.ItemDataRole.UserRole, nb["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.nb_list.addItem(item)

    def on_metadata_changed(self):
        self.refresh_entries()
        self.context_changed.emit()

    def sync_with_global(self, monday, date_str, tags_str):
        if not self.sync_cb.isChecked():
            return

        self.current_week_monday = monday
        self.current_date_filter = date_str
        self.active_global_tags = [t.strip() for t in tags_str.split(",")] if tags_str else []

        self._update_status_labels()
        self.refresh_entries()
        self.context_changed.emit()

    def get_active_tags(self):
        return self.active_global_tags

    def get_active_notebooks(self):
        ids = []
        for i in range(self.nb_list.count()):
            item = self.nb_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def refresh_entries(self):
        """Fetch records matching current filters and display them."""
        self.entries_list.clear()
        state = self._context_state()
        notebook_entries = [
            entry
            for notebook_id in state.notebook_ids
            for entry in self.notebook_db.get_entries(notebook_id)
        ]
        for text, tooltip in entry_descriptors(
            state.forced_records, fetch_context_records(self.db, state), notebook_entries
        ):
            item = QListWidgetItem(text)
            if tooltip:
                item.setToolTip(tooltip)
            self.entries_list.addItem(item)

        self.entries_count_lbl.setText(f"{self.entries_list.count()} entries in context")

    def set_collapsed(self, collapsed):
        if not self._show_header:
            self._collapsed = False
            self.header_label.setVisible(True)
            self.content_widget.setVisible(True)
            self.toggle_btn.setText("⟩")
            self.toggle_btn.setToolTip("Collapse context panel")
            return
        self._collapsed = bool(collapsed)
        self.header_label.setVisible(not self._collapsed)
        self.content_widget.setVisible(not self._collapsed)
        self.toggle_btn.setText("⟨" if self._collapsed else "⟩")
        self.toggle_btn.setToolTip("Expand context panel" if self._collapsed else "Collapse context panel")

    def is_collapsed(self):
        return self._collapsed

    def reset_all(self):
        self.current_date_filter = None
        self.current_week_monday = None
        self.active_global_tags = []
        self.forced_records = []
        for i in range(self.nb_list.count()):
            self.nb_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._update_status_labels()
        self.refresh_entries()

    def set_forced_records(self, records):
        self.forced_records = list(records or [])
        self.refresh_entries()
        self._update_status_labels()

    def clear_extra_context(self):
        self.current_date_filter = None
        self.current_week_monday = None
        self.active_global_tags = []
        for i in range(self.nb_list.count()):
            self.nb_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self._update_status_labels()
        self.refresh_entries()
        self.context_changed.emit()

    def _update_status_labels(self):
        date_label, tags_label = status_labels(self._context_state())
        self.date_lbl.setText(date_label)
        self.tags_lbl.setText(tags_label)

    def set_interactive(self, interactive: bool):
        self._interactive = bool(interactive)
        for widget in (
            self.sync_cb,
            self.nb_list,
            self.add_context_btn,
            self.reset_context_btn,
            self.clear_chat_btn,
            self.toggle_btn,
        ):
            widget.setEnabled(self._interactive)
        if not self._show_header:
            self.toggle_btn.setVisible(False)

    def serialize_state(self):
        return self._context_state().as_dict()

    def apply_state(self, state):
        state = state_from_dict(state)
        self.current_week_monday = state.week_monday
        self.current_date_filter = state.date_filter
        self.active_global_tags = state.tags

        notebook_ids = set(state.notebook_ids)
        self.nb_list.blockSignals(True)
        for i in range(self.nb_list.count()):
            item = self.nb_list.item(i)
            item.setCheckState(
                Qt.CheckState.Checked
                if item.data(Qt.ItemDataRole.UserRole) in notebook_ids
                else Qt.CheckState.Unchecked
            )
        self.nb_list.blockSignals(False)

        self.forced_records = state.forced_records
        self.sync_cb.setChecked(state.sync_enabled)
        self._collapsed = state.collapsed
        self._update_status_labels()
        self.refresh_entries()
        self.set_collapsed(self._collapsed)

    def restore_from_panel(self, panel):
        if panel is None:
            return
        self.apply_state(panel.serialize_state())

    def _context_state(self):
        return ContextPanelState(
            week_monday=self.current_week_monday,
            date_filter=self.current_date_filter,
            tags=list(self.active_global_tags),
            notebook_ids=self.get_active_notebooks(),
            forced_records=[dict(record) for record in self.forced_records],
            sync_enabled=self.sync_cb.isChecked(),
            collapsed=self.is_collapsed(),
        )
