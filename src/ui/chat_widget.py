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

import json
import re
import markdown
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QComboBox, QLabel, QApplication,
                             QFrame, QDialog, QListWidget, QListWidgetItem, QTabWidget,
                             QDateEdit, QDialogButtonBox, QScrollArea, QSplitter,
                             QGroupBox, QCheckBox, QCalendarWidget, QToolButton,
                             QMessageBox)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QSize, QDate, QEvent
from PyQt6.QtGui import QCursor, QIcon, QTextCharFormat, QColor, QPalette
from src.worker import ChatThread
from src.database import DBManager
from src.ui.styles import TEXT_EDIT_STYLE, BUTTON_PRIMARY_STYLE
from src.notebook_database import NotebookDBManager

class ContextManagerPanel(QWidget):
    """Side panel for ChatWidget to manage context synchronized with main sidebar."""
    context_changed = pyqtSignal()
    toggle_requested = pyqtSignal()
    COLLAPSED_WIDTH = 44
    
    def __init__(self, db, notebook_db, parent=None):
        super().__init__(parent)
        self.db = db
        self.notebook_db = notebook_db
        self._collapsed = False
        
        # Selection State (Synced from Global)
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
        self.toggle_btn.setStyleSheet("""
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
        """)
        header_layout.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(header)

        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        # --- Entries (Context) List ---
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
        
        # --- Context Status ---
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
        
        # --- Notebooks Section ---
        nb_group = QGroupBox("Include Notebooks")
        nb_layout = QVBoxLayout(nb_group)
        self.nb_list = QListWidget()
        self.nb_list.setFixedHeight(120)
        self.nb_list.itemChanged.connect(self.on_metadata_changed)
        nb_layout.addWidget(self.nb_list)
        content_layout.addWidget(nb_group)
        
        # --- Tools ---
        self.add_context_btn = QPushButton("Add Context")
        self.add_context_btn.clicked.connect(self.parent().add_context)
        content_layout.addWidget(self.add_context_btn)

        self.reset_context_btn = QPushButton("Reset Extra Context")
        self.reset_context_btn.clicked.connect(self.parent().reset_extra_context)
        content_layout.addWidget(self.reset_context_btn)

        self.clear_chat_btn = QPushButton("Clear Chat History")
        self.clear_chat_btn.clicked.connect(self.parent().clear_history)
        content_layout.addWidget(self.clear_chat_btn)

        layout.addWidget(self.content_widget)
        
        layout.addStretch()

    def load_notebooks(self):
        self.nb_list.clear()
        notebooks = self.notebook_db.get_notebooks()
        for nb in notebooks:
            item = QListWidgetItem(f"📓 {nb['name']}")
            item.setData(Qt.ItemDataRole.UserRole, nb['id'])
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
        self.active_global_tags = [t.strip() for t in tags_str.split(',')] if tags_str else []
        
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

        # Always include forced meeting contexts first.
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
            records = self.db.fetch_by_date_range(start_date, end_date, self.active_global_tags if self.active_global_tags else None)
        elif self.current_date_filter:
            records = self.db.fetch_by_dates([self.current_date_filter], self.active_global_tags if self.active_global_tags else None)
        elif self.active_global_tags:
            records = self.db.fetch_by_date_range("1970-01-01", "2099-12-31", self.active_global_tags)
        
        # Display Recordings
        for r in records:
            rid = r.get("id")
            if rid is not None and int(rid) in seen_record_ids:
                continue
            if rid is not None:
                seen_record_ids.add(int(rid))
            icon = "🎤" if r.get('type') == 'recording' else "📝"
            item = QListWidgetItem(f"{icon} {r['title'] or 'Untitled'}")
            item.setToolTip(f"{r['created_at']}")
            self.entries_list.addItem(item)
            
        # Display Notebooks
        for nid in self.get_active_notebooks():
            nb_entries = self.notebook_db.get_entries(nid)
            for e in nb_entries:
                item = QListWidgetItem(f"📓 {e['title'] or 'Notebook note'}")
                self.entries_list.addItem(item)
                
        self.entries_count_lbl.setText(f"{self.entries_list.count()} entries in context")

    def set_collapsed(self, collapsed):
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
        self.tags_lbl.setText(
            f"Tags: {', '.join(self.active_global_tags) if self.active_global_tags else 'all'}"
        )

class AddContextDialog(QDialog):
    def __init__(self, db_manager, notebook_db, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.notebook_db = notebook_db
        self.selected_context = None
        
        self.setWindowTitle("Add Context")
        self.resize(400, 500)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Notebooks Tab
        self.nb_list = QListWidget()
        self.load_notebooks()
        self.tabs.addTab(self.nb_list, "Notebooks")
        
        # Tags Tab
        self.tag_list = QListWidget()
        self.load_tags()
        self.tabs.addTab(self.tag_list, "Tags")
        
        # Date Tab
        date_widget = QWidget()
        date_layout = QVBoxLayout(date_widget)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(datetime.now().date())
        date_layout.addWidget(QLabel("Select Date:"))
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        self.tabs.addTab(date_widget, "Date")
        
        layout.addWidget(self.tabs)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_notebooks(self):
        notebooks = self.notebook_db.get_notebooks()
        for nb in notebooks:
            item = QListWidgetItem(f"📓 {nb['name']}")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "notebook", "value": nb['id'], "label": nb['name']})
            self.nb_list.addItem(item)

    def load_tags(self):
        tags = self.db.get_all_tags()
        for tag in tags:
            item = QListWidgetItem(f"🏷 {tag}")
            item.setData(Qt.ItemDataRole.UserRole, {"type": "tag", "value": tag, "label": tag})
            self.tag_list.addItem(item)

    def on_accept(self):
        idx = self.tabs.currentIndex()
        if idx == 0: # Notebooks
            item = self.nb_list.currentItem()
            if item:
                self.selected_context = item.data(Qt.ItemDataRole.UserRole)
        elif idx == 1: # Tags
            item = self.tag_list.currentItem()
            if item:
                self.selected_context = item.data(Qt.ItemDataRole.UserRole)
        elif idx == 2: # Date
            date_str = self.date_edit.date().toString("yyyy-MM-dd")
            self.selected_context = {"type": "date", "value": date_str, "label": date_str}
            
        if self.selected_context:
            self.accept()
        else:
            self.reject() # Or show warning

class ChatWidget(QWidget):
    session_updated = pyqtSignal()
    float_requested = pyqtSignal(object)
    tab_requested = pyqtSignal(object)
    minimize_requested = pyqtSignal(object)
    restore_requested = pyqtSignal(object)
    close_requested = pyqtSignal(object)
    title_changed = pyqtSignal(object, str)

    def __init__(self, rag_engine, session_id=None, parent=None, initial_contexts=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        self.notebook_db = NotebookDBManager()
        self.chat_history = [] 
        self.chat_thread = None
        self.current_session_id = session_id
        self.forced_record_ids = set()
        self.forced_record_labels = []
        self.display_mode = "tab"
        self.floating_minimized = False
        self.context_panel_collapsed = False
        self._context_panel_saved_sizes = [900, 350]
        
        self.init_ui()
        
        # Load initial contexts if provided (for new chats)
        if initial_contexts:
            self._apply_contexts(initial_contexts)
        
        if self.current_session_id:
            self.load_session(self.current_session_id)

    def _is_dark_theme(self):
        app = QApplication.instance()
        sheet = (app.styleSheet() if app else "").lower()
        if "#2b2b2b" in sheet and "#eeeeee" in sheet:
            return True
        if "#f5f5f5" in sheet and "#333333" in sheet:
            return False
        return self.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("chatWidgetHeader")
        self.header.setFixedHeight(32)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 3, 6, 3)
        header_layout.setSpacing(4)

        self.title_label = QLabel("New Chat")
        header_layout.addWidget(self.title_label, 1)
        self.header.installEventFilter(self)
        self.title_label.installEventFilter(self)

        self.mode_btn = QToolButton()
        self.mode_btn.setAutoRaise(True)
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setFixedSize(20, 20)
        self.mode_btn.clicked.connect(self._toggle_display_mode)
        header_layout.addWidget(self.mode_btn)

        self.minimize_btn = QToolButton()
        self.minimize_btn.setText("_")
        self.minimize_btn.setToolTip("Minimize to compact chip")
        self.minimize_btn.setAutoRaise(True)
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minimize_btn.setFixedSize(20, 20)
        self.minimize_btn.clicked.connect(self._toggle_minimized_state)
        header_layout.addWidget(self.minimize_btn)

        self.close_btn = QToolButton()
        self.close_btn.setText("×")
        self.close_btn.setToolTip("Close chat")
        self.close_btn.setAutoRaise(True)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        header_layout.addWidget(self.close_btn)

        root_layout.addWidget(self.header)

        self.content_container = QWidget()
        main_layout = QHBoxLayout(self.content_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Side: Chat ---
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)

        # Chat Display
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setPlaceholderText("Pregunta cualquier cosa sobre tus notas...")
        chat_layout.addWidget(self.display)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe tu pregunta aquí...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setProperty("class", "calendar-primary-btn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFixedHeight(36)
        input_layout.addWidget(self.send_btn)

        chat_layout.addLayout(input_layout)
        
        self.splitter.addWidget(chat_container)
        
        # --- Right Side: Context Manager Panel ---
        self.context_panel = ContextManagerPanel(self.db, self.notebook_db, self)
        self.context_panel.toggle_requested.connect(self.toggle_context_panel)
        self.splitter.addWidget(self.context_panel)
        self.splitter.splitterMoved.connect(self._remember_context_panel_sizes)
        
        self.splitter.setSizes([900, 350])
        main_layout.addWidget(self.splitter)
        root_layout.addWidget(self.content_container)
        self._apply_theme_styles()
        self.set_display_mode("tab")
        self._refresh_title()

    def _apply_theme_styles(self):
        is_dark = self._is_dark_theme()
        header_bg = "rgba(33, 150, 243, 0.15)" if is_dark else "rgba(33, 150, 243, 0.10)"
        header_border = "rgba(33, 150, 243, 0.45)" if is_dark else "rgba(33, 150, 243, 0.35)"
        title_color = "#e8eef7" if is_dark else "#2b3b52"
        btn_color = "#94a3b8" if is_dark else "#546E7A"
        btn_hover = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.05)"
        display_bg = "#1f232a" if is_dark else "#ffffff"
        display_text = "#f3f6fb" if is_dark else "#1a1c1e"
        input_bg = "#2a2f37" if is_dark else "#f5f5f5"
        input_border = "#4f5b6f" if is_dark else "#cccccc"
        display_border = "#404b5c" if is_dark else "#cccccc"

        self.header.setStyleSheet(f"""
            QFrame#chatWidgetHeader {{
                background-color: {header_bg};
                border-bottom: 1px solid {header_border};
                border-top-left-radius: 11px;
                border-top-right-radius: 11px;
            }}
        """)
        self.title_label.setStyleSheet(
            f"font-weight: 600; font-size: 12px; color: {title_color};"
        )

        action_btn_style = f"""
            QToolButton {{
                border: none;
                border-radius: 6px;
                padding: 1px;
                background: transparent;
                color: {btn_color};
                font-size: 11px;
                font-weight: 700;
            }}
            QToolButton:hover {{
                background-color: {btn_hover};
                color: #2196F3;
            }}
        """
        self.mode_btn.setStyleSheet(action_btn_style)
        self.minimize_btn.setStyleSheet(action_btn_style)
        self.close_btn.setStyleSheet(
            action_btn_style
            + """
            QToolButton:hover {
                background-color: rgba(244, 67, 54, 0.15);
                color: #f44336;
            }
            """
        )
        self.display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {display_bg};
                color: {display_text};
                border: 1px solid {display_border};
                border-radius: 8px;
                font-size: 14px;
                padding: 10px;
                line-height: 1.5;
            }}
        """)
        self.display.document().setDefaultStyleSheet(
            f"body {{ color: {display_text}; }} a {{ color: #64b5f6; }}"
        )
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {display_text};
                border: 1px solid {input_border};
                border-radius: 18px;
                padding: 8px 15px;
                font-size: 13px;
            }}
        """)

    def changeEvent(self, event):
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._apply_theme_styles()
        super().changeEvent(event)

    def update_from_global_selection(self, monday, date_str, tags_str):
        """Called by MainWindow when sidebar selection changes."""
        self.context_panel.sync_with_global(monday, date_str, tags_str)

    def _remember_context_panel_sizes(self, *_args):
        if self.display_mode == "floating" or self.floating_minimized or self.context_panel_collapsed:
            return
        sizes = self.splitter.sizes()
        if len(sizes) == 2 and sizes[1] > 0:
            self._context_panel_saved_sizes = list(sizes)

    def _apply_context_panel_visibility(self):
        is_floating = self.display_mode == "floating"
        visible = not is_floating and not self.floating_minimized

        self.context_panel.setVisible(visible)
        if not visible:
            self.context_panel.setMinimumWidth(0)
            self.context_panel.setMaximumWidth(16777215)
            return

        self.context_panel.set_collapsed(self.context_panel_collapsed)
        if self.context_panel_collapsed:
            width = self.context_panel.COLLAPSED_WIDTH
            self.context_panel.setMinimumWidth(width)
            self.context_panel.setMaximumWidth(width)
            self.splitter.setSizes([max(1, self.width() - width), width])
            return

        self.context_panel.setMinimumWidth(280)
        self.context_panel.setMaximumWidth(16777215)
        if len(self._context_panel_saved_sizes) == 2 and sum(self._context_panel_saved_sizes) > 0:
            self.splitter.setSizes(self._context_panel_saved_sizes)
        else:
            self.splitter.setSizes([900, 350])

    def clear_history(self):
        reply = QMessageBox.question(self, "Clear History", "Are you sure you want to clear this chat history?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.chat_history = []
            self.display.clear()
            if self.current_session_id:
                self.db.update_chat_session(self.current_session_id, json.dumps([]))

    def add_context(self):
        dialog = AddContextDialog(self.db, self.notebook_db, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ctx = dialog.selected_context or {}
        ctx_type = ctx.get("type")
        if ctx_type == "date":
            self.context_panel.current_week_monday = None
            self.context_panel.current_date_filter = str(ctx.get("value") or "")
        elif ctx_type == "tag":
            tag = str(ctx.get("value") or "").strip()
            if tag and tag not in self.context_panel.active_global_tags:
                self.context_panel.active_global_tags.append(tag)
        elif ctx_type == "notebook":
            nid = ctx.get("value")
            for i in range(self.context_panel.nb_list.count()):
                item = self.context_panel.nb_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == nid:
                    item.setCheckState(Qt.CheckState.Checked)
                    break
        self.context_panel._update_status_labels()
        self.context_panel.refresh_entries()
        self.context_panel.context_changed.emit()

    def reset_extra_context(self):
        self.context_panel.clear_extra_context()

    def load_session(self, session_id):
        sessions = self.db.fetch_chat_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if session:
            self.current_session_id = session['id']
            self.chat_history = json.loads(session['messages'])
            
            # Load Contexts
            context_data = session.get('context_data')
            if context_data:
                try:
                    contexts = json.loads(context_data)
                    self._apply_contexts(contexts)
                except:
                    pass
            
            self.display.clear()
            for msg in self.chat_history:
                role_name = "User" if msg['role'] == 'user' else "Assistant"
                self.append_to_chat(role_name, msg['content'])
            self._refresh_title(session.get("name"))

    def send_message(self):
        query = self.input_field.text().strip()
        if not query:
            return

        self.input_field.clear()
        self.append_to_chat("User", query)
        self.chat_history.append({"role": "user", "content": query})

        # Gather Context
        context_text_parts = []
        
        # 1. Notebooks
        notebook_ids = self.context_panel.get_active_notebooks()
        for nid in notebook_ids:
            entries = self.notebook_db.get_entries(nid)
            for entry in entries:
                content = entry['content']
                title = entry['title'] or "Untitled"
                context_text_parts.append(f"[Notebook note: {title}]\n{content}")

        # 2. Tags & Dates (RAG Filter)
        tags = self.context_panel.get_active_tags()
        
        records = []
        seen_ids = set()
        for rid in sorted(self.forced_record_ids):
            rec = self.db.fetch_record(rid)
            if isinstance(rec, dict) and rec.get("id") is not None:
                records.append(rec)
                seen_ids.add(int(rec["id"]))
        if self.context_panel.current_week_monday:
            # Multi-day range
            start_date = self.context_panel.current_week_monday.toString("yyyy-MM-dd")
            end_date = self.context_panel.current_date_filter
            for rec in self.db.fetch_by_date_range(start_date, end_date, tags if tags else None):
                rid = int(rec.get("id"))
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    records.append(rec)
        elif self.context_panel.current_date_filter:
            # Single day
            for rec in self.db.fetch_by_dates([self.context_panel.current_date_filter], tags if tags else None):
                rid = int(rec.get("id"))
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    records.append(rec)
        elif tags:
            # Tags only, all time
            for rec in self.db.fetch_by_date_range("1970-01-01", "2099-12-31", tags):
                rid = int(rec.get("id"))
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    records.append(rec)

        tasks = []
        if self.context_panel.current_week_monday:
            start_date = self.context_panel.current_week_monday.toString("yyyy-MM-dd")
            end_date = self.context_panel.current_date_filter
            tasks = self.db.get_tasks_by_date_range(start_date, end_date, ",".join(tags) if tags else None)
        elif self.context_panel.current_date_filter:
            tasks = self.db.get_tasks_by_date(self.context_panel.current_date_filter, ",".join(tags) if tags else None)
        elif tags:
            tasks = self.db.get_tasks_by_date_range("1970-01-01", "2099-12-31", ",".join(tags))
        
        rag_ids = None
        if records:
            rag_ids = [str(r['id']) for r in records]
            for r in records:
                composed = self.db.compose_ai_text(r.get("transcription"), r.get("recording_notes"))
                record_label = "Meeting" if r.get("type") == "recording" else "Note"
                context_text_parts.append(
                    f"[{record_label}: {r['title'] or 'Untitled'} ({r['created_at']})]\n{composed}"
                )

        if tasks:
            task_lines = []
            for task in tasks:
                status = "done" if task.get("is_completed") else "pending"
                origin = (task.get("task_origin") or task.get("record_title") or "").strip()
                origin_suffix = f" [{origin}]" if origin else ""
                task_lines.append(f"- ({status}) {(task.get('content') or '').strip()}{origin_suffix}")
            context_text_parts.append("[Tasks]\n" + "\n".join(task_lines))

        # 3. RAG Search
        if rag_ids or (not tags and not self.context_panel.current_date_filter):
            try:
                results = self.rag.search(query, n_results=5, ids=rag_ids)
                for r in results:
                    context_text_parts.append(f"[Fragmento relevante: {r['metadata'].get('title', 'Desconocido')}]\n{r['text']}")
            except Exception as e:
                print(f"RAG Search error: {e}")

        context_text = "\n\n".join(context_text_parts)
        if not context_text:
            context_text = "No relevant context found."

        # Start Chat Thread
        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        
        if not is_valid:
            self.append_to_chat("System", f"Error: {error_msg}")
            return

        if self.chat_thread and self.chat_thread.isRunning():
            return
        self.set_busy(True)
        self.chat_thread = ChatThread("", query, context_text, self.chat_history)
        self.chat_thread.finished.connect(self.on_chat_finished)
        self.chat_thread.error.connect(self.on_chat_error)
        self.chat_thread.finished.connect(self._clear_chat_thread_ref)
        self.chat_thread.error.connect(self._clear_chat_thread_ref)
        self.chat_thread.start()

    def on_chat_finished(self, response):
        self.set_busy(False)
        self.append_to_chat("Assistant", response)
        self.chat_history.append({"role": "assistant", "content": response})
        
        # Save Session Context
        messages_json = json.dumps(self.chat_history)
        
        # Construct simplified context for saving
        save_contexts = []
        if self.context_panel.current_week_monday and self.context_panel.current_date_filter:
            save_contexts.append(
                {
                    "type": "date_range",
                    "value": {
                        "start": self.context_panel.current_week_monday.toString("yyyy-MM-dd"),
                        "end": self.context_panel.current_date_filter,
                    },
                }
            )
        elif self.context_panel.current_date_filter:
            save_contexts.append({"type": "date", "value": self.context_panel.current_date_filter})
        for t in self.context_panel.get_active_tags():
            save_contexts.append({"type": "tag", "value": t})
        for n in self.context_panel.get_active_notebooks():
            save_contexts.append({"type": "notebook", "value": n})
        for rid in sorted(self.forced_record_ids):
            save_contexts.append({"type": "recording", "value": rid})
            
        context_json = json.dumps(save_contexts)
        
        if self.current_session_id:
            self.db.update_chat_session(self.current_session_id, messages_json, context_data=context_json)
            self.session_updated.emit()
        else:
            name = self.chat_history[0]['content'][:30] + "..."
            collection = "Chat"
            self.current_session_id = self.db.save_chat_session(name, collection, messages_json, context_data=context_json)
            self.session_updated.emit()
        self._refresh_title()

    def on_chat_error(self, error_msg):
        self.set_busy(False)
        self.append_to_chat("System", f"Error: {error_msg}")

    def append_to_chat(self, role, text):
        is_dark = self._is_dark_theme()
        if role == "User":
            color = "#64b5f6" if is_dark else "#1565C0" # Bright blue / Deep blue
        elif role == "Assistant":
            color = "#81c784" if is_dark else "#2e7d32" # Bright green / Deep green
        else:
            color = "#ff8a80" if is_dark else "#d32f2f" # Bright red / Deep red
            
        # Forcing pure white/black for maximum contrast and slightly larger font
        text_color = "#ffffff" if is_dark else "#000000"
        font_size = "13px"
        
        html_content = markdown.markdown(text)
        html_content = self._apply_message_html_theme(html_content, text_color, is_dark)
        cursor = self.display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(
            f"<div style='margin-bottom: 4px;'><b><span style='color: {color}; font-size: 12px;'>{role}:</span></b></div>"
        )
        body_start = cursor.position()
        cursor.insertHtml(
            f"<div style='font-size: {font_size}; line-height: 1.4;'>{html_content}</div>"
        )
        body_end = cursor.position()
        cursor.setPosition(body_start)
        cursor.setPosition(body_end, cursor.MoveMode.KeepAnchor)
        body_format = cursor.charFormat()
        body_format.setForeground(QColor(text_color))
        cursor.mergeCharFormat(body_format)
        cursor.clearSelection()
        cursor.insertBlock()
        self.display.setTextCursor(cursor)
        self.display.verticalScrollBar().setValue(self.display.verticalScrollBar().maximum())

    def _apply_message_html_theme(self, html_content, text_color, is_dark):
        code_bg = "#2a2f37" if is_dark else "#f3f5f7"
        link_color = "#8fb8ff" if is_dark else "#1565C0"
        themed_html = html_content

        tag_styles = {
            "p": f"color: {text_color};",
            "li": f"color: {text_color};",
            "ul": f"color: {text_color};",
            "ol": f"color: {text_color};",
            "strong": f"color: {text_color};",
            "em": f"color: {text_color};",
            "span": f"color: {text_color};",
            "blockquote": f"color: {text_color};",
            "code": f"color: {text_color}; background-color: {code_bg};",
            "pre": f"color: {text_color}; background-color: {code_bg};",
            "a": f"color: {link_color};",
        }

        for tag, style in tag_styles.items():
            themed_html = re.sub(
                rf"<{tag}(?P<attrs>[^>]*)>",
                lambda m: self._merge_inline_style(tag, m.group("attrs"), style),
                themed_html,
                flags=re.IGNORECASE,
            )

        return themed_html

    @staticmethod
    def _merge_inline_style(tag, attrs, style):
        attrs = attrs or ""
        if "style=" in attrs:
            return re.sub(
                r'style=(["\'])(.*?)\1',
                lambda m: f'style={m.group(1)}{m.group(2)} {style}{m.group(1)}',
                f"<{tag}{attrs}>",
                count=1,
                flags=re.IGNORECASE,
            )
        return f"<{tag}{attrs} style=\"{style}\">"

    def set_busy(self, busy):
        self.send_btn.setEnabled(not busy)
        self.input_field.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()

    def _clear_chat_thread_ref(self, *args):
        thread = self.chat_thread
        self.chat_thread = None
        if thread:
            thread.deleteLater()

    def cleanup(self):
        if self.chat_thread and self.chat_thread.isRunning():
            try:
                self.chat_thread.requestInterruption()
                self.chat_thread.quit()
                self.chat_thread.wait(3000)
            except Exception:
                pass
        if self.chat_thread:
            try:
                self.chat_thread.deleteLater()
            except Exception:
                pass
        self.chat_thread = None
        QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def _apply_contexts(self, contexts):
        self.context_panel.reset_all()
        self.forced_record_ids = set()
        self.forced_record_labels = []
        has_recording_context = False
        for ctx in contexts or []:
            ctx_type = (ctx or {}).get("type")
            ctx_value = (ctx or {}).get("value")
            if ctx_type == "date" and ctx_value:
                self.context_panel.current_date_filter = str(ctx_value)
            elif ctx_type == "date_range" and isinstance(ctx_value, dict):
                start = str(ctx_value.get("start") or "").strip()
                end = str(ctx_value.get("end") or "").strip()
                start_date = QDate.fromString(start, "yyyy-MM-dd")
                if start_date.isValid() and end:
                    self.context_panel.current_week_monday = start_date
                    self.context_panel.current_date_filter = end
            elif ctx_type == "tag" and ctx_value:
                tag_value = str(ctx_value).strip()
                if tag_value and tag_value not in self.context_panel.active_global_tags:
                    self.context_panel.active_global_tags.append(tag_value)
            elif ctx_type == "notebook":
                for i in range(self.context_panel.nb_list.count()):
                    item = self.context_panel.nb_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == ctx_value:
                        item.setCheckState(Qt.CheckState.Checked)
            elif ctx_type == "recording":
                has_recording_context = True
                try:
                    rid = int(ctx_value)
                except (TypeError, ValueError):
                    continue
                self.forced_record_ids.add(rid)
                label = ((ctx or {}).get("label") or f"Recording {rid}").strip()
                if label and label not in self.forced_record_labels:
                    self.forced_record_labels.append(label)

        if has_recording_context:
            # Prevent global sidebar sync from polluting a "single meeting" chat by default.
            self.context_panel.sync_cb.setChecked(False)

        forced_records = []
        for rid in sorted(self.forced_record_ids):
            rec = self.db.fetch_record(rid)
            if isinstance(rec, dict):
                forced_records.append(
                    {
                        "id": rid,
                        "title": rec.get("title") or f"Recording {rid}",
                        "created_at": rec.get("created_at") or "",
                    }
                )
            else:
                forced_records.append({"id": rid, "title": f"Recording {rid}", "created_at": ""})
        self.context_panel.set_forced_records(forced_records)
        self._refresh_title()

    def set_display_mode(self, mode):
        self.display_mode = "floating" if mode == "floating" else "tab"
        is_floating = self.display_mode == "floating"
        
        # Adjust margins to show the host's rounded corners and border
        m = 0 if not is_floating else 1
        self.layout().setContentsMargins(m, m, m, m)
        self.header.setVisible(is_floating)
        
        self.mode_btn.setText("⇱" if is_floating else "↗")
        self.mode_btn.setToolTip("Move chat back to tab" if is_floating else "Move chat to floating bar")
        self.minimize_btn.setVisible(is_floating)
        self.content_container.setVisible(not self.floating_minimized)
        self.minimize_btn.setText("□" if self.floating_minimized else "_")
        self.minimize_btn.setToolTip("Restore chat" if self.floating_minimized else "Minimize to title bar")
        self.header.setCursor(
            Qt.CursorShape.PointingHandCursor if self.floating_minimized else Qt.CursorShape.ArrowCursor
        )
        self.title_label.setCursor(
            Qt.CursorShape.PointingHandCursor if self.floating_minimized else Qt.CursorShape.ArrowCursor
        )
        self._apply_context_panel_visibility()
        self.splitter.setSizes([740, 0] if is_floating else (self._context_panel_saved_sizes if not self.context_panel_collapsed else [max(1, self.width() - self.context_panel.COLLAPSED_WIDTH), self.context_panel.COLLAPSED_WIDTH]))

    def _toggle_display_mode(self):
        if self.display_mode == "floating":
            self.tab_requested.emit(self)
        else:
            self.float_requested.emit(self)

    def _toggle_minimized_state(self):
        if self.floating_minimized:
            self.restore_requested.emit(self)
        else:
            self.minimize_requested.emit(self)

    def set_floating_minimized(self, minimized):
        self.floating_minimized = bool(minimized) and self.display_mode == "floating"
        self.set_display_mode(self.display_mode)

    def collapse_context_panel(self):
        if self.display_mode == "floating" or self.floating_minimized:
            return
        if self.context_panel_collapsed:
            return
        sizes = self.splitter.sizes()
        if len(sizes) == 2 and sizes[1] > 0:
            self._context_panel_saved_sizes = list(sizes)
        self.context_panel_collapsed = True
        self._apply_context_panel_visibility()

    def expand_context_panel(self):
        if not self.context_panel_collapsed:
            return
        self.context_panel_collapsed = False
        self._apply_context_panel_visibility()

    def toggle_context_panel(self):
        if self.context_panel_collapsed:
            self.expand_context_panel()
        else:
            self.collapse_context_panel()

    def eventFilter(self, watched, event):
        if (
            watched in (self.header, self.title_label)
            and self.floating_minimized
            and event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.restore_requested.emit(self)
            return True
        return super().eventFilter(watched, event)

    def get_chat_title(self):
        if self.current_session_id:
            sessions = self.db.fetch_chat_sessions()
            session = next((s for s in sessions if s.get("id") == self.current_session_id), None)
            if session and session.get("name"):
                return session["name"]
        if self.chat_history:
            first_message = (self.chat_history[0].get("content") or "").strip()
            if first_message:
                return first_message[:30] + ("..." if len(first_message) > 30 else "")
        labels = list(self.forced_record_labels)
        labels.extend(self.context_panel.get_active_tags())
        if self.context_panel.current_date_filter:
            labels.append(self.context_panel.current_date_filter)
        if labels:
            return ", ".join(labels[:2]) + ("..." if len(labels) > 2 else "")
        return "New Chat"

    def _refresh_title(self, title=None):
        resolved_title = (title or self.get_chat_title() or "New Chat").strip()
        self.title_label.setText(resolved_title)
        self.title_changed.emit(self, resolved_title)
