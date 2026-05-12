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
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QLineEdit, QPushButton, QComboBox, QLabel, QApplication,
                             QFrame, QDialog, QScrollArea, QSplitter,
                             QGroupBox, QCheckBox, QCalendarWidget, QToolButton,
                             QMessageBox)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QCursor, QIcon, QTextCharFormat, QColor, QPalette
from src.worker_components.threads import ChatThread
from src.database import DBManager
from src.ui.styles import TEXT_EDIT_STYLE, BUTTON_PRIMARY_STYLE
from src.notebook_database import NotebookDBManager
from src.ui.context_manager_panel import ContextManagerPanel
from src.ui.chat.add_context_dialog import AddContextDialog
from src.ui.chat.context_builder import build_chat_context_text
from src.ui.chat.context_state import parse_chat_context_state
from src.ui.chat.message_renderer import render_chat_message_html
from src.ui.chat.busy_state import build_chat_busy_state
from src.ui.chat.session_loader import load_chat_session_state
from src.ui.chat.session_applier import apply_loaded_chat_session
from src.ui.chat.header_state import build_chat_header_state
from src.ui.chat.session_state import (
    persist_chat_session,
    resolve_chat_display_title,
)
from src.ui.chat.theme_styles import build_chat_widget_theme

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
        self.context_panel.add_context_requested.connect(self.add_context)
        self.context_panel.reset_extra_context_requested.connect(self.reset_extra_context)
        self.context_panel.clear_chat_requested.connect(self.clear_history)
        self.splitter.addWidget(self.context_panel)
        self.splitter.splitterMoved.connect(self._remember_context_panel_sizes)
        
        self.splitter.setSizes([900, 350])
        main_layout.addWidget(self.splitter)
        root_layout.addWidget(self.content_container)
        self._apply_theme_styles()
        self.set_display_mode("tab")
        self._refresh_title()

    def _apply_theme_styles(self):
        theme = build_chat_widget_theme(self._is_dark_theme())
        header_bg = theme["header_bg"]
        header_border = theme["header_border"]
        title_color = theme["title_color"]
        btn_color = theme["btn_color"]
        btn_hover = theme["btn_hover"]
        display_bg = theme["display_bg"]
        display_text = theme["display_text"]
        input_bg = theme["input_bg"]
        input_border = theme["input_border"]
        display_border = theme["display_border"]

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
        if not session:
            return

        loaded = load_chat_session_state(session)
        apply_loaded_chat_session(self, loaded)

    def send_message(self):
        query = self.input_field.text().strip()
        if not query:
            return

        self.input_field.clear()
        self.append_to_chat("User", query)
        self.chat_history.append({"role": "user", "content": query})
        context_text = build_chat_context_text(
            db=self.db,
            notebook_db=self.notebook_db,
            rag=self.rag,
            query=query,
            context_panel=self.context_panel,
            forced_record_ids=self.forced_record_ids,
        )

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

        self.current_session_id = persist_chat_session(
            self.db,
            self.current_session_id,
            self.chat_history,
            self.context_panel,
            self.forced_record_ids,
        )
        self.session_updated.emit()
        self._refresh_title()

    def on_chat_error(self, error_msg):
        self.set_busy(False)
        self.append_to_chat("System", f"Error: {error_msg}")

    def append_to_chat(self, role, text):
        is_dark = self._is_dark_theme()
        header_html, body_html, text_color = render_chat_message_html(role, text, is_dark)
        cursor = self.display.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(header_html)
        body_start = cursor.position()
        cursor.insertHtml(body_html)
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

    def set_busy(self, busy):
        state = build_chat_busy_state(busy)
        self.send_btn.setEnabled(state["send_enabled"])
        self.input_field.setEnabled(state["input_enabled"])
        if state["cursor_shape"] == "wait":
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
        parsed = parse_chat_context_state(contexts)
        self.context_panel.current_week_monday = parsed["current_week_monday"]
        self.context_panel.current_date_filter = parsed["current_date_filter"]
        self.context_panel.active_global_tags = list(parsed["active_global_tags"])
        self.forced_record_ids = set(parsed["forced_record_ids"])
        self.forced_record_labels = list(parsed["forced_record_labels"])

        for i in range(self.context_panel.nb_list.count()):
            item = self.context_panel.nb_list.item(i)
            item.setCheckState(
                Qt.CheckState.Checked
                if item.data(Qt.ItemDataRole.UserRole) in parsed["notebook_ids"]
                else Qt.CheckState.Unchecked
            )

        if parsed["has_recording_context"]:
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
        state = build_chat_header_state(self.display_mode, self.floating_minimized)

        self.layout().setContentsMargins(
            state["layout_margin"],
            state["layout_margin"],
            state["layout_margin"],
            state["layout_margin"],
        )
        self.header.setVisible(state["header_visible"])
        self.mode_btn.setText(state["mode_btn_text"])
        self.mode_btn.setToolTip(state["mode_btn_tooltip"])
        self.minimize_btn.setVisible(state["minimize_visible"])
        self.content_container.setVisible(state["content_visible"])
        self.minimize_btn.setText(state["minimize_btn_text"])
        self.minimize_btn.setToolTip(state["minimize_btn_tooltip"])
        cursor_shape = (
            Qt.CursorShape.PointingHandCursor if state["cursor"] == "pointing" else Qt.CursorShape.ArrowCursor
        )
        self.header.setCursor(cursor_shape)
        self.title_label.setCursor(cursor_shape)
        self._apply_context_panel_visibility()
        self.splitter.setSizes(
            [740, 0]
            if self.display_mode == "floating"
            else (
                self._context_panel_saved_sizes
                if not self.context_panel_collapsed
                else [max(1, self.width() - self.context_panel.COLLAPSED_WIDTH), self.context_panel.COLLAPSED_WIDTH]
            )
        )

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
        return resolve_chat_display_title(
            None,
            self.chat_history,
            self.forced_record_labels,
            self.context_panel.get_active_tags(),
            self.context_panel.current_date_filter,
        )

    def _refresh_title(self, title=None):
        resolved_title = (title or self.get_chat_title() or "New Chat").strip()
        self.title_label.setText(resolved_title)
        self.title_changed.emit(self, resolved_title)
