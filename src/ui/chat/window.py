"""Standalone chat dialog composed from focused chat helpers."""

import json

import markdown
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QDialog

from src.database import DBManager
from src.ui.chat.conversation_runtime import ChatConversationRuntime
from src.ui.chat.window_layout import build_chat_window_layout
from src.ui.chat.window_state import (
    build_window_context,
    load_window_session,
    save_window_session,
)


class ChatWindow(QDialog):
    """Compatible standalone dialog for collection-scoped RAG chat."""

    session_updated = pyqtSignal()

    def __init__(self, rag_engine, session_id=None, parent=None, persistence=None, runtime=None):
        super().__init__(parent)
        self.setWindowTitle("Chat with your Notes")
        self.resize(700, 600)
        self.rag = rag_engine
        self.db = persistence if persistence is not None else DBManager()
        self.runtime = runtime or ChatConversationRuntime()
        self.chat_history = []
        self.current_session_id = session_id
        self.chat_thread = None  # Compatibility view of the active runtime thread.

        self.init_ui()
        self.refresh_collections()
        if self.current_session_id:
            self.load_session(self.current_session_id)

    def init_ui(self):
        build_chat_window_layout(self)

    def refresh_collections(self):
        self.collection_combo.clear()
        self.collection_combo.addItem("All")
        self.collection_combo.addItems(self.db.get_all_tags())

    def load_session(self, session_id):
        session = load_window_session(self.db, session_id)
        if not session:
            return
        self.current_session_id = session["id"]
        self.chat_history = json.loads(session["messages"])
        self.collection_combo.setCurrentText(session["collection"])
        self.display.clear()
        for message in self.chat_history:
            self.append_to_chat("User" if message["role"] == "user" else "Assistant", message["content"])

    def send_message(self):
        query = self.input_field.text().strip()
        if not query:
            return
        self.input_field.clear()
        self.append_to_chat("User", query)
        self.chat_history.append({"role": "user", "content": query})
        try:
            context_text = build_window_context(self.rag, query, self.collection_combo.currentText())
        except Exception as error:
            self.append_to_chat("System", f"Error searching notes: {error}")
            return

        result = self.runtime.start(
            query,
            context_text,
            self.chat_history,
            self.on_chat_finished,
            self.on_chat_error,
            on_started=lambda: self.set_busy(True),
        )
        self.chat_thread = self.runtime.thread
        if not result.started and result.validation_error:
            self.append_to_chat("System", f"Error: {result.validation_error}")

    def on_chat_finished(self, response):
        self.set_busy(False)
        self.append_to_chat("Assistant", response)
        self.chat_history.append({"role": "assistant", "content": response})
        self.current_session_id = save_window_session(
            self.db,
            self.current_session_id,
            self.chat_history,
            self.collection_combo.currentText(),
        )
        self.session_updated.emit()

    def on_chat_error(self, error_msg):
        self.set_busy(False)
        self.append_to_chat("System", f"Error: {error_msg}")

    def append_to_chat(self, role, text):
        color = "blue" if role == "User" else "green" if role == "Assistant" else "red"
        formatted = f"<b><span style='color: {color};'>{role}:</span></b><br>{markdown.markdown(text)}<br>"
        self.display.append(formatted)
        self.display.verticalScrollBar().setValue(self.display.verticalScrollBar().maximum())

    def set_busy(self, busy):
        self.send_btn.setEnabled(not busy)
        self.input_field.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()

    def closeEvent(self, event):
        self.runtime.cleanup()
        super().closeEvent(event)
