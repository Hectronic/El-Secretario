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
                             QMessageBox, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QCursor, QIcon, QPalette
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
from src.ui.chat.context_actions import apply_initial_contexts
from src.ui.chat.display_mode import apply_context_panel_visibility, apply_display_mode
from src.ui.chat.session_state import (
    persist_chat_session,
    resolve_chat_display_title,
)
from src.ui.chat.conversation_runtime import ChatConversationRuntime
from src.ui.chat import layout as chat_layout
from src.ui.chat.workflows import context_summary, source_cards, starter_prompts

class ChatWidget(QWidget):
    session_updated = pyqtSignal()
    float_requested = pyqtSignal(object)
    tab_requested = pyqtSignal(object)
    minimize_requested = pyqtSignal(object)
    restore_requested = pyqtSignal(object)
    close_requested = pyqtSignal(object)
    title_changed = pyqtSignal(object, str)
    source_requested = pyqtSignal(int)
    context_edit_requested = pyqtSignal(object)

    def __init__(
        self,
        rag_engine,
        session_id=None,
        parent=None,
        initial_contexts=None,
        persistence=None,
        notebook_persistence=None,
        conversation_runtime=None,
    ):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = persistence if persistence is not None else DBManager()
        self.notebook_db = (
            notebook_persistence if notebook_persistence is not None else NotebookDBManager()
        )
        self.chat_history = [] 
        self.conversation_runtime = conversation_runtime or ChatConversationRuntime()
        self.current_session_id = session_id
        self.forced_record_ids = set()
        self.forced_record_labels = []
        self.display_mode = "tab"
        self.floating_minimized = False
        self.context_panel_collapsed = False
        self.floating_context_editor_open = False
        self._context_panel_saved_sizes = [900, 350]
        self._pending_message = None
        self._pending_sources = []
        self._pending_retrieval_degraded = False
        self._latest_assistant_card = None
        
        self.init_ui()
        
        # Load initial contexts if provided (for new chats)
        if initial_contexts:
            self._apply_contexts(initial_contexts)
        
        if self.current_session_id:
            self.load_session(self.current_session_id)
        self.context_panel.context_changed.connect(self._refresh_context_summary)
        self._refresh_context_summary()
        self._refresh_starters()

    def _is_dark_theme(self):
        app = QApplication.instance()
        sheet = (app.styleSheet() if app else "").lower()
        if "#2b2b2b" in sheet and "#eeeeee" in sheet:
            return True
        if "#f5f5f5" in sheet and "#333333" in sheet:
            return False
        return self.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def init_ui(self):
        chat_layout.build_chat_layout(self)

    def _apply_theme_styles(self):
        chat_layout.apply_chat_theme(self)

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
        apply_context_panel_visibility(self)

    def clear_history(self):
        reply = QMessageBox.question(self, "Clear History", "Are you sure you want to clear this chat history?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.chat_history = []
            self.display.clear()
            self._latest_assistant_card = None
            self._clear_actions(self.response_actions_layout)
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
        self._refresh_starters()
        self._refresh_context_summary()

    def send_message(self):
        query = self.input_field.text().strip()
        if not query or self._pending_message is not None:
            return
        self._start_request(query, add_user=True)

    def _start_request(self, query, *, add_user):
        if add_user:
            self._pending_message = query
            self.chat_history.append({"role": "user", "content": query})
            self.append_to_chat("User", query)
            self.input_field.clear()
        self._remove_failure_row()
        context_text, raw_sources, self._pending_retrieval_degraded = build_chat_context_text(
            db=self.db,
            notebook_db=self.notebook_db,
            rag=self.rag,
            query=query,
            context_panel=self.context_panel,
            forced_record_ids=self.forced_record_ids,
            return_sources=True,
        )
        self._pending_sources = source_cards(raw_sources)

        result = self.conversation_runtime.start(
            query,
            context_text,
            self.chat_history,
            self.on_chat_finished,
            self.on_chat_error,
            lambda: self.set_busy(True),
        )
        if result.validation_error:
            self.on_chat_error(result.validation_error)
        elif not result.started:
            self.set_busy(False)
            self._show_failure("Ya hay una respuesta en curso. Espera o cancélala.")

    def on_chat_finished(self, response):
        self.set_busy(False)
        self.append_to_chat("Assistant", response)
        assistant_message = {"role": "assistant", "content": response}
        if self._pending_sources or self._pending_retrieval_degraded:
            assistant_message["sources"] = list(self._pending_sources)
            assistant_message["retrieval_degraded"] = self._pending_retrieval_degraded
        self.chat_history.append(assistant_message)
        self._pending_message = None

        self.current_session_id = persist_chat_session(
            self.db,
            self.current_session_id,
            self.chat_history,
            self.context_panel,
            self.forced_record_ids,
        )
        self.session_updated.emit()
        self._refresh_title()
        self._show_response_actions(response)
        self._show_sources(self._pending_sources, self._pending_retrieval_degraded)
        self._refresh_starters()

    def on_chat_error(self, error_msg):
        self.set_busy(False)
        self._show_failure(error_msg)

    @staticmethod
    def _clear_actions(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _show_failure(self, error_msg):
        self.status_label.setText("No se pudo completar la respuesta. Puedes reintentar o editar el mensaje.")
        self.status_label.setVisible(True)
        self._remove_failure_row()
        row, row_layout = self._new_action_row(self.response_actions_layout)
        self._failure_row = row
        retry = QPushButton("Reintentar")
        retry.setAccessibleName("Retry failed chat request")
        retry.clicked.connect(self.retry_request)
        edit = QPushButton("Editar mensaje")
        edit.setAccessibleName("Edit failed chat message")
        edit.clicked.connect(self.edit_failed_message)
        row_layout.addWidget(retry)
        row_layout.addWidget(edit)

    def retry_request(self):
        if self._pending_message is None or self.conversation_runtime.thread is not None:
            return
        self._start_request(self._pending_message, add_user=False)

    def edit_failed_message(self):
        if self._pending_message is None:
            return
        message = self._pending_message
        if self.chat_history and self.chat_history[-1] == {"role": "user", "content": message}:
            self.chat_history.pop()
        self._pending_message = None
        self.input_field.setPlainText(message)
        self.input_field.setFocus()
        self._render_history()
        self._remove_failure_row()
        self.status_label.setVisible(False)
        self._refresh_starters()

    def cancel_request(self):
        message = self._pending_message
        if message is None:
            return
        self.conversation_runtime.cancel()
        if self.chat_history and self.chat_history[-1] == {"role": "user", "content": message}:
            self.chat_history.pop()
        self._pending_message = None
        self.input_field.setPlainText(message)
        self.set_busy(False)
        self.status_label.setText("Solicitud cancelada. El mensaje queda disponible para editar.")
        self.status_label.setVisible(True)
        self._render_history()
        self._refresh_starters()

    def _render_history(self):
        self.display.clear()
        self._latest_assistant_card = None
        for message in self.chat_history:
            role = "User" if message.get("role") == "user" else "Assistant"
            self.append_to_chat(role, message.get("content", ""))
            if role == "Assistant":
                self._show_response_actions(message.get("content", ""))
                self._show_sources(message.get("sources", []), message.get("retrieval_degraded", False))

    def _refresh_context_summary(self, *_args):
        self.context_summary.setText(context_summary(self.context_panel, self.forced_record_labels))

    @staticmethod
    def _new_action_row(parent_layout):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(2, 2, 2, 2)
        parent_layout.addWidget(row)
        return row, row_layout

    def _remove_failure_row(self):
        row = getattr(self, "_failure_row", None)
        if row is not None:
            self.response_actions_layout.removeWidget(row)
            row.deleteLater()
            self._failure_row = None

    def inspect_context(self):
        if self.display_mode == "floating":
            if self.floating_minimized:
                return
            self.floating_context_editor_open = not self.floating_context_editor_open
            self._apply_context_panel_visibility()
        else:
            self.context_edit_requested.emit(self)
        if self.context_panel.isVisible():
            self.context_panel.setFocus()

    def show_remove_context_menu(self):
        """Offer explicit per-item removal from the selected chat context."""
        menu = QMenu(self)
        for record_id in sorted(self.forced_record_ids):
            record = self.db.fetch_record(record_id) or {}
            label = record.get("title") or f"Registro {record_id}"
            menu.addAction(f"Quitar registro: {label}", lambda rid=record_id: self.remove_context_item("record", rid))
        for tag in self.context_panel.get_active_tags():
            menu.addAction(f"Quitar etiqueta: {tag}", lambda value=tag: self.remove_context_item("tag", value))
        if self.context_panel.current_date_filter:
            menu.addAction(f"Quitar fecha: {self.context_panel.current_date_filter}", lambda: self.remove_context_item("date"))
        for index in range(self.context_panel.nb_list.count()):
            item = self.context_panel.nb_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                menu.addAction(f"Quitar cuaderno: {item.text()}", lambda nid=item.data(Qt.ItemDataRole.UserRole): self.remove_context_item("notebook", nid))
        if menu.actions():
            menu.exec(QCursor.pos())

    def remove_context_item(self, kind, value=None):
        if kind == "record":
            record_id = int(value)
            self.forced_record_ids.discard(record_id)
            self.forced_record_labels = [
                (self.db.fetch_record(selected_id) or {}).get("title") or f"Recording {selected_id}"
                for selected_id in sorted(self.forced_record_ids)
            ]
            self.context_panel.forced_records = [
                record for record in self.context_panel.forced_records if int(record.get("id", -1)) != int(value)
            ]
            self.context_panel.refresh_entries()
        elif kind == "tag":
            self.context_panel.active_global_tags = [tag for tag in self.context_panel.get_active_tags() if tag != value]
        elif kind == "date":
            self.context_panel.current_date_filter = None
            self.context_panel.current_week_monday = None
        elif kind == "notebook":
            for index in range(self.context_panel.nb_list.count()):
                item = self.context_panel.nb_list.item(index)
                if item.data(Qt.ItemDataRole.UserRole) == value:
                    item.setCheckState(Qt.CheckState.Unchecked)
                    break
        self.context_panel._update_status_labels()
        self.context_panel.refresh_entries()
        self.context_panel.context_changed.emit()
        self._refresh_context_summary()
        self._refresh_title()

    def _refresh_starters(self):
        self._clear_actions(self.starters_layout)
        if self.chat_history or self._pending_message is not None:
            self.starters_container.setVisible(False)
            return
        self.starters_container.setVisible(True)
        for prompt in starter_prompts(
            self.forced_record_labels, self.context_panel.get_active_tags(),
            bool(self.context_panel.current_date_filter), bool(self.context_panel.get_active_notebooks()),
        ):
            button = QPushButton(prompt)
            button.setAccessibleName(f"Use suggestion: {prompt}")
            button.clicked.connect(lambda _checked=False, value=prompt: self._use_starter(value))
            self.starters_layout.addWidget(button)

    def _use_starter(self, prompt):
        self.input_field.setPlainText(prompt)
        self.input_field.setFocus()

    def _show_response_actions(self, response):
        card = self._latest_assistant_card
        if card is None:
            return
        copy = QPushButton("Copiar")
        copy.setAccessibleName("Copy assistant response")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(response))
        followup = QPushButton("Preguntar sobre esta respuesta")
        followup.setAccessibleName("Ask a follow-up about this response")
        followup.clicked.connect(lambda: self._use_starter("Amplía esta respuesta con ejemplos: " + response[:160]))
        card.add_action(copy)
        card.add_action(followup)
        self.status_label.setVisible(False)

    def _show_sources(self, sources=None, degraded=None):
        card = self._latest_assistant_card
        if card is None:
            return
        sources = self._pending_sources if sources is None else sources
        degraded = self._pending_retrieval_degraded if degraded is None else degraded
        card.set_sources(sources, degraded)

    def append_to_chat(self, role, text):
        is_dark = self._is_dark_theme()
        header_html, body_html, _text_color = render_chat_message_html(role, text, is_dark)
        card = self.display.add_message(role, header_html + body_html)
        if role == "Assistant":
            self._latest_assistant_card = card
            card.source_requested.connect(self.source_requested.emit)
        return card

    def apply_context_state(self, state):
        """Apply context edits made in the main window's active-chat section."""
        self.context_panel.apply_state(state)
        self.forced_record_ids = {
            int(record["id"])
            for record in self.context_panel.forced_records
            if record.get("id") is not None
        }
        self.forced_record_labels = [
            record.get("title") or f"Recording {record.get('id')}"
            for record in self.context_panel.forced_records
        ]
        self._refresh_context_summary()
        self._refresh_starters()
        self._refresh_title()

    def set_busy(self, busy):
        state = build_chat_busy_state(busy)
        self.send_btn.setEnabled(state["send_enabled"])
        self.input_field.setEnabled(state["input_enabled"])
        self.cancel_btn.setVisible(bool(busy))
        if busy:
            self.status_label.setText("Generando respuesta…")
            self.status_label.setVisible(True)
        if state["cursor_shape"] == "wait":
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()

    def cleanup(self):
        self.conversation_runtime.cleanup()
        QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def _apply_contexts(self, contexts):
        apply_initial_contexts(self, contexts)

    def set_display_mode(self, mode):
        apply_display_mode(self, mode)

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
        if self.display_mode == "floating":
            if self.floating_minimized:
                return
            self.floating_context_editor_open = not self.floating_context_editor_open
            self._apply_context_panel_visibility()
            return
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
