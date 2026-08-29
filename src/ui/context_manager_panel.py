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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        is_dark = self.palette().color(self.backgroundRole()).lightness() < 128
        panel_bg = "#262b33" if is_dark else "#ffffff"
        panel_border = "#4a5463" if is_dark else "#c6d2e2"
        panel_text = "#e8eef7" if is_dark else "#2b3b52"
        meta_text = "#b8c1cf" if is_dark else "#666666"

        header = QWidget()
        self.header = header
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        self.header_label = QLabel("Chat Context")
        self.header_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        header_layout.addWidget(self.header_label, 1)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setAutoRaise(True)
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setToolTip("Collapse context panel")
        self.toggle_btn.clicked.connect(self.toggle_requested.emit)
        self.toggle_btn.setText("⟩")
        self.toggle_btn.setStyleSheet(
            """
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 0px;
                background: transparent;
                color: #607D8B;
                font-size: 15px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: rgba(33, 150, 243, 0.14);
                color: #2196F3;
            }
            """
        )
        header_layout.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(header)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        entries_group = QGroupBox("Detected Context Entries")
        entries_layout = QVBoxLayout(entries_group)

        self.entries_list = QListWidget()
        self.entries_list.setStyleSheet(
            f"font-size: 11px; background-color: {panel_bg}; color: {panel_text}; "
            f"border: 1px solid {panel_border}; border-radius: 8px;"
        )
        entries_layout.addWidget(self.entries_list)

        self.entries_count_lbl = QLabel("0 entries found")
        self.entries_count_lbl.setStyleSheet(f"color: {meta_text}; font-size: 11px;")
        entries_layout.addWidget(self.entries_count_lbl)

        content_layout.addWidget(entries_group)

        status_group = QGroupBox("Selection Context")
        status_layout = QVBoxLayout(status_group)

        self.sync_cb = QCheckBox("Sync with App")
        self.sync_cb.setChecked(True)
        self.sync_cb.setStyleSheet("font-weight: bold; color: #2196F3;")
        status_layout.addWidget(self.sync_cb)

        self.date_lbl = QLabel("Dates: all history")
        date_color = "#8fb8ff" if is_dark else "#1565C0"
        self.date_lbl.setStyleSheet(f"font-size: 11px; color: {date_color}; font-weight: bold;")
        self.date_lbl.setWordWrap(True)
        status_layout.addWidget(self.date_lbl)

        self.tags_lbl = QLabel("Tags: all")
        self.tags_lbl.setStyleSheet(f"font-size: 11px; color: {meta_text};")
        self.tags_lbl.setWordWrap(True)
        status_layout.addWidget(self.tags_lbl)

        content_layout.addWidget(status_group)

        nb_group = QGroupBox("Include Notebooks")
        nb_layout = QVBoxLayout(nb_group)
        self.nb_list = QListWidget()
        self.nb_list.setFixedHeight(120)
        self.nb_list.itemChanged.connect(self.on_metadata_changed)
        nb_layout.addWidget(self.nb_list)
        content_layout.addWidget(nb_group)

        self.add_context_btn = QPushButton("Add Context")
        self.add_context_btn.clicked.connect(self.add_context_requested.emit)
        content_layout.addWidget(self.add_context_btn)

        self.reset_context_btn = QPushButton("Reset Extra Context")
        self.reset_context_btn.clicked.connect(self.reset_extra_context_requested.emit)
        content_layout.addWidget(self.reset_context_btn)

        self.clear_chat_btn = QPushButton("Clear Chat History")
        self.clear_chat_btn.clicked.connect(self.clear_chat_requested.emit)
        content_layout.addWidget(self.clear_chat_btn)

        layout.addWidget(self.content_widget)
        layout.addStretch()

        self.set_interactive(self._interactive)
        self.header.setVisible(self._show_header)
        self.toggle_btn.setVisible(self._show_header)
        if not self._show_header:
            self.content_widget.setVisible(True)

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

        records = []
        seen_record_ids = set()

        for fr in self.forced_records:
            rid = fr.get("id")
            if rid is None:
                continue
            seen_record_ids.add(int(rid))
            title = fr.get("title") or "Untitled"
            created_at = fr.get("created_at") or ""
            item = QListWidgetItem(f"📌 🎤 {title}")
            if created_at:
                item.setToolTip(created_at)
            self.entries_list.addItem(item)

        if self.current_week_monday:
            start_date = self.current_week_monday.toString("yyyy-MM-dd")
            end_date = self.current_date_filter
            records = self.db.fetch_by_date_range(
                start_date,
                end_date,
                self.active_global_tags if self.active_global_tags else None,
            )
        elif self.current_date_filter:
            records = self.db.fetch_by_dates(
                [self.current_date_filter],
                self.active_global_tags if self.active_global_tags else None,
            )
        elif self.active_global_tags:
            records = self.db.fetch_by_date_range("1970-01-01", "2099-12-31", self.active_global_tags)

        for r in records:
            rid = r.get("id")
            if rid is not None and int(rid) in seen_record_ids:
                continue
            if rid is not None:
                seen_record_ids.add(int(rid))
            icon = "🎤" if r.get("type") == "recording" else "📝"
            item = QListWidgetItem(f"{icon} {r['title'] or 'Untitled'}")
            item.setToolTip(f"{r['created_at']}")
            self.entries_list.addItem(item)

        for nid in self.get_active_notebooks():
            nb_entries = self.notebook_db.get_entries(nid)
            for e in nb_entries:
                item = QListWidgetItem(f"📓 {e['title'] or 'Notebook note'}")
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
        if self.current_week_monday:
            mon_s = self.current_week_monday.toString("yyyy-MM-dd")
            self.date_lbl.setText(f"Dates: {mon_s} to {self.current_date_filter}")
        elif self.current_date_filter:
            self.date_lbl.setText(f"Date: {self.current_date_filter}")
        else:
            self.date_lbl.setText("Dates: all history")
        self.tags_lbl.setText(f"Tags: {', '.join(self.active_global_tags) if self.active_global_tags else 'all'}")

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
        notebook_ids = []
        for i in range(self.nb_list.count()):
            item = self.nb_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                notebook_ids.append(item.data(Qt.ItemDataRole.UserRole))

        return {
            "current_week_monday": self.current_week_monday.toString("yyyy-MM-dd") if self.current_week_monday else None,
            "current_date_filter": self.current_date_filter,
            "active_global_tags": list(self.active_global_tags),
            "notebook_ids": notebook_ids,
            "forced_records": [dict(record) for record in self.forced_records],
            "sync_enabled": self.sync_cb.isChecked(),
            "collapsed": self.is_collapsed(),
        }

    def apply_state(self, state):
        state = state or {}
        monday_text = state.get("current_week_monday")
        monday = QDate.fromString(str(monday_text or ""), "yyyy-MM-dd") if monday_text else QDate()
        self.current_week_monday = monday if monday.isValid() else None
        date_filter = state.get("current_date_filter")
        self.current_date_filter = str(date_filter) if date_filter else None
        self.active_global_tags = [str(tag).strip() for tag in state.get("active_global_tags") or [] if str(tag).strip()]

        notebook_ids = {item_id for item_id in state.get("notebook_ids") or []}
        self.nb_list.blockSignals(True)
        for i in range(self.nb_list.count()):
            item = self.nb_list.item(i)
            item.setCheckState(
                Qt.CheckState.Checked
                if item.data(Qt.ItemDataRole.UserRole) in notebook_ids
                else Qt.CheckState.Unchecked
            )
        self.nb_list.blockSignals(False)

        self.forced_records = [dict(record) for record in state.get("forced_records") or []]
        self.sync_cb.setChecked(bool(state.get("sync_enabled", True)))
        self._collapsed = bool(state.get("collapsed", False))
        self._update_status_labels()
        self.refresh_entries()
        self.set_collapsed(self._collapsed)

    def restore_from_panel(self, panel):
        if panel is None:
            return
        self.apply_state(panel.serialize_state())
