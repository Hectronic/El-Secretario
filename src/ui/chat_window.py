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
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QComboBox, QLabel, QApplication,
                             QWidget)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QCursor
from src.worker import ChatThread
from src.database import DBManager

class ChatWindow(QDialog):
    session_updated = pyqtSignal() # Signal to notify MainWindow to refresh its list

    def __init__(self, rag_engine, session_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chat with your Notes")
        self.resize(700, 600)
        self.rag = rag_engine
        self.db = DBManager()
        self.chat_history = [] # List of dicts {'role': 'user/assistant', 'content': '...'}
        self.chat_thread = None
        self.current_session_id = session_id

        self.init_ui()
        self.refresh_collections()
        
        if self.current_session_id:
            self.load_session(self.current_session_id)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Top Bar: Collection Selector
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Collection:"))
        self.collection_combo = QComboBox()
        self.collection_combo.addItem("All")
        top_layout.addWidget(self.collection_combo)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)

        # Chat Display
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setPlaceholderText("Ask anything about your notes...")
        layout.addWidget(self.display)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your question here...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

        # Apply border to the entire window
        self.setStyleSheet("""
            ChatWindow {
                border: 3px solid #2196F3;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
        """)

    def refresh_collections(self):
        tags = self.db.get_all_tags()
        self.collection_combo.clear()
        self.collection_combo.addItem("All")
        self.collection_combo.addItems(tags)

    def load_session(self, session_id):
        sessions = self.db.fetch_chat_sessions()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if session:
            self.current_session_id = session['id']
            self.chat_history = json.loads(session['messages'])
            self.collection_combo.setCurrentText(session['collection'])
            
            self.display.clear()
            for msg in self.chat_history:
                role_name = "User" if msg['role'] == 'user' else "Assistant"
                self.append_to_chat(role_name, msg['content'])

    def send_message(self):
        query = self.input_field.text().strip()
        if not query:
            return

        self.input_field.clear()
        self.append_to_chat("User", query)
        self.chat_history.append({"role": "user", "content": query})

        # 1. Search RAG for context
        tag_filter = self.collection_combo.currentText()
        try:
            results = self.rag.search(query, n_results=5, tag_filter=tag_filter)
            context_text = "\n\n".join([f"Note: {r['text']}" for r in results])
            if not context_text:
                context_text = "No relevant notes found for this query."
        except Exception as e:
            self.append_to_chat("System", f"Error searching notes: {e}")
            return

        # 2. Start Chat Thread
        settings = QSettings("Hectronic", "Secretario")
        
        # Validate AI provider configuration
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        
        if not is_valid:
            self.append_to_chat("System", f"Error: {error_msg}")
            return

        self.set_busy(True)
        # api_key parameter kept for backward compatibility
        self.chat_thread = ChatThread("", query, context_text, self.chat_history)
        self.chat_thread.finished.connect(self.on_chat_finished)
        self.chat_thread.error.connect(self.on_chat_error)
        self.chat_thread.start()

    def on_chat_finished(self, response):
        self.set_busy(False)
        self.append_to_chat("Assistant", response)
        self.chat_history.append({"role": "assistant", "content": response})
        
        # Save/Update Session
        messages_json = json.dumps(self.chat_history)
        if self.current_session_id:
            self.db.update_chat_session(self.current_session_id, messages_json)
            self.session_updated.emit()
        else:
            # Create new session
            name = self.chat_history[0]['content'][:30] + "..."
            collection = self.collection_combo.currentText()
            self.current_session_id = self.db.save_chat_session(name, collection, messages_json)
            self.session_updated.emit()

    def on_chat_error(self, error_msg):
        self.set_busy(False)
        self.append_to_chat("System", f"Error: {error_msg}")

    def append_to_chat(self, role, text):
        import markdown
        color = "blue" if role == "User" else "green" if role == "Assistant" else "red"
        
        # Convert markdown to HTML
        html_content = markdown.markdown(text)
        
        formatted_text = f"<b><span style='color: {color};'>{role}:</span></b><br>{html_content}<br>"
        self.display.append(formatted_text)
        # Scroll to bottom
        self.display.verticalScrollBar().setValue(self.display.verticalScrollBar().maximum())

    def set_busy(self, busy):
        self.send_btn.setEnabled(not busy)
        self.input_field.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()
