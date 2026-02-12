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
import markdown
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QLineEdit, QPushButton, QComboBox, QLabel, QApplication,
                             QFrame, QDialog, QListWidget, QListWidgetItem, QTabWidget,
                             QDateEdit, QDialogButtonBox, QScrollArea)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QSize
from PyQt6.QtGui import QCursor, QIcon
from src.worker import ChatThread
from src.database import DBManager
from src.ui.styles import TEXT_EDIT_STYLE, BUTTON_PRIMARY_STYLE
from src.notebook_database import NotebookDBManager

class ContextChip(QFrame):
    removed = pyqtSignal(object) # Emits self

    def __init__(self, context_type, value, label, parent=None):
        super().__init__(parent)
        self.context_type = context_type
        self.value = value
        self.label_text = label
        
        self.setStyleSheet("""
            ContextChip {
                background-color: #E3F2FD;
                border: 1px solid #2196F3;
                border-radius: 15px;
            }
        """)
        self.setFixedHeight(30)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0)
        layout.setSpacing(5)
        
        lbl = QLabel(label)
        lbl.setStyleSheet("border: none; color: #1565C0; font-weight: bold;")
        layout.addWidget(lbl)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #1565C0;
                font-weight: bold;
                font-size: 16px;
                background: transparent;
            }
            QPushButton:hover {
                color: red;
            }
        """)
        close_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(close_btn)

    def to_dict(self):
        return {
            "type": self.context_type,
            "value": self.value,
            "label": self.label_text
        }

class ContextBar(QWidget):
    context_added = pyqtSignal(dict)
    context_removed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chips = []
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.add_btn = QPushButton("+ Context")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px dashed #999;
                border-radius: 15px;
                padding: 5px 10px;
                color: #555;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                color: #333;
            }
        """)
        self.layout.addWidget(self.add_btn)

    def add_context(self, context_type, value, label):
        # Check duplicates
        for chip in self.chips:
            if chip.context_type == context_type and chip.value == value:
                return

        chip = ContextChip(context_type, value, label)
        chip.removed.connect(self.remove_chip)
        
        self.layout.insertWidget(self.layout.count() - 1, chip)
        self.chips.append(chip)
        
        self.context_added.emit(chip.to_dict())

    def remove_chip(self, chip):
        self.layout.removeWidget(chip)
        self.chips.remove(chip)
        chip.deleteLater()
        self.context_removed.emit(chip.to_dict())

    def get_contexts(self):
        return [chip.to_dict() for chip in self.chips]

    def clear(self):
        for chip in self.chips:
            self.layout.removeWidget(chip)
            chip.deleteLater()
        self.chips = []

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

    def __init__(self, rag_engine, session_id=None, parent=None, initial_contexts=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        self.notebook_db = NotebookDBManager()
        self.chat_history = [] 
        self.chat_thread = None
        self.current_session_id = session_id
        
        self.init_ui()
        
        # Load initial contexts if provided (for new chats)
        if initial_contexts:
            for ctx in initial_contexts:
                self.context_bar.add_context(ctx['type'], ctx['value'], ctx['label'])
        
        if self.current_session_id:
            self.load_session(self.current_session_id)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Context Bar
        self.context_bar = ContextBar()
        self.context_bar.add_btn.clicked.connect(self.open_add_context_dialog)
        layout.addWidget(self.context_bar)

        # Chat Display
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setPlaceholderText("Ask anything about your notes...")
        self.display.setStyleSheet(TEXT_EDIT_STYLE)
        layout.addWidget(self.display)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your question here...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet(BUTTON_PRIMARY_STYLE)
        input_layout.addWidget(self.send_btn)

        layout.addLayout(input_layout)

    def open_add_context_dialog(self):
        dialog = AddContextDialog(self.db, self.notebook_db, self)
        if dialog.exec():
            ctx = dialog.selected_context
            self.context_bar.add_context(ctx['type'], ctx['value'], ctx['label'])

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
                    self.context_bar.clear()
                    for ctx in contexts:
                        self.context_bar.add_context(ctx['type'], ctx['value'], ctx['label'])
                except:
                    pass
            else:
                # Legacy support: try to load from filter_date/tags
                if session.get('filter_date'):
                    self.context_bar.add_context('date', session['filter_date'], session['filter_date'])
                if session.get('filter_tags'):
                    tags = session['filter_tags'].split(',')
                    for tag in tags:
                        if tag.strip():
                            self.context_bar.add_context('tag', tag.strip(), tag.strip())
            
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

        # Gather Context
        contexts = self.context_bar.get_contexts()
        context_text_parts = []
        
        # 1. Notebooks
        notebook_ids = [c['value'] for c in contexts if c['type'] == 'notebook']
        for nid in notebook_ids:
            entries = self.notebook_db.get_entries(nid)
            for entry in entries:
                content = entry['content']
                title = entry['title'] or "Untitled"
                context_text_parts.append(f"[Notebook Note: {title}]\n{content}")

        # 2. Tags & Dates (RAG Filter)
        tags = [c['value'] for c in contexts if c['type'] == 'tag']
        dates = [c['value'] for c in contexts if c['type'] == 'date']
        
        rag_ids = None
        if tags or dates:
            # If dates are present, we use them. If multiple dates, we might need fetch_by_dates
            # Current DB supports fetch_by_date_range or fetch_by_dates
            # Let's use fetch_by_dates if dates are present
            records = []
            if dates:
                records = self.db.fetch_by_dates(dates, tags=tags if tags else None)
            elif tags:
                # Only tags, all time
                # We can use fetch_all with tag filter, but fetch_all only supports single tag string match
                # fetch_by_date_range supports list of tags
                records = self.db.fetch_by_date_range("1970-01-01", "2099-12-31", tags)
            
            if records:
                rag_ids = [str(r['id']) for r in records]
            else:
                if not notebook_ids: # Only warn if no other context
                    context_text_parts.append("No recordings found for the selected tags/dates.")

        # 3. RAG Search
        # If we have specific RAG IDs (from filters) OR no context at all (global search)
        if rag_ids or (not contexts):
            try:
                results = self.rag.search(query, n_results=5, ids=rag_ids)
                for r in results:
                    context_text_parts.append(f"[Recording: {r['metadata'].get('title', 'Unknown')}]\n{r['text']}")
            except Exception as e:
                print(f"RAG Search error: {e}")

        context_text = "\n\n".join(context_text_parts)
        if not context_text:
            context_text = "No relevant context found."

        # Start Chat Thread
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
        contexts = self.context_bar.get_contexts()
        context_json = json.dumps(contexts)
        
        # Legacy fields for backward compatibility (optional, but good for list view if we want to show tags)
        # Let's just use context_data primarily
        
        if self.current_session_id:
            self.db.update_chat_session(self.current_session_id, messages_json, context_data=context_json)
            self.session_updated.emit()
        else:
            # Create new session
            name = self.chat_history[0]['content'][:30] + "..."
            
            # Derive collection name from contexts
            collection = "General"
            if contexts:
                labels = [c['label'] for c in contexts]
                collection = ", ".join(labels[:2])
                if len(labels) > 2:
                    collection += "..."
            
            self.current_session_id = self.db.save_chat_session(name, collection, messages_json, context_data=context_json)
            self.session_updated.emit()

    def on_chat_error(self, error_msg):
        self.set_busy(False)
        self.append_to_chat("System", f"Error: {error_msg}")

    def append_to_chat(self, role, text):
        color = "blue" if role == "User" else "green" if role == "Assistant" else "red"
        html_content = markdown.markdown(text)
        formatted_text = f"<b><span style='color: {color};'>{role}:</span></b><br>{html_content}<br>"
        self.display.append(formatted_text)
        self.display.verticalScrollBar().setValue(self.display.verticalScrollBar().maximum())

    def set_busy(self, busy):
        self.send_btn.setEnabled(not busy)
        self.input_field.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()
