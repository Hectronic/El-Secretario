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
                             QDateEdit, QDialogButtonBox, QScrollArea, QSplitter,
                             QGroupBox, QCheckBox, QCalendarWidget)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QSize, QDate
from PyQt6.QtGui import QCursor, QIcon, QTextCharFormat, QColor
from src.worker import ChatThread
from src.database import DBManager
from src.ui.styles import TEXT_EDIT_STYLE, BUTTON_PRIMARY_STYLE
from src.notebook_database import NotebookDBManager

class ContextManagerPanel(QWidget):
    """Side panel for ChatWidget to manage context synchronized with main sidebar."""
    context_changed = pyqtSignal()
    
    def __init__(self, db, notebook_db, parent=None):
        super().__init__(parent)
        self.db = db
        self.notebook_db = notebook_db
        
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
        
        layout.addWidget(entries_group)
        
        # --- Context Status ---
        status_group = QGroupBox("Chat Context")
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
        
        layout.addWidget(status_group)
        
        # --- Notebooks Section ---
        nb_group = QGroupBox("Include Notebooks")
        nb_layout = QVBoxLayout(nb_group)
        self.nb_list = QListWidget()
        self.nb_list.setFixedHeight(120)
        self.nb_list.itemChanged.connect(self.on_metadata_changed)
        nb_layout.addWidget(self.nb_list)
        layout.addWidget(nb_group)
        
        # --- Tools ---
        self.add_context_btn = QPushButton("Add Context")
        self.add_context_btn.clicked.connect(self.parent().add_context)
        layout.addWidget(self.add_context_btn)

        self.reset_context_btn = QPushButton("Reset Extra Context")
        self.reset_context_btn.clicked.connect(self.parent().reset_extra_context)
        layout.addWidget(self.reset_context_btn)

        self.clear_chat_btn = QPushButton("Clear Chat History")
        self.clear_chat_btn.clicked.connect(self.parent().clear_history)
        layout.addWidget(self.clear_chat_btn)
        
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
        
        self.init_ui()
        
        # Load initial contexts if provided (for new chats)
        if initial_contexts:
            self._apply_contexts(initial_contexts)
        
        if self.current_session_id:
            self.load_session(self.current_session_id)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
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
        self.display.setStyleSheet(TEXT_EDIT_STYLE)
        chat_layout.addWidget(self.display)

        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe tu pregunta aquí...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setStyleSheet(BUTTON_PRIMARY_STYLE)
        input_layout.addWidget(self.send_btn)

        chat_layout.addLayout(input_layout)
        
        self.splitter.addWidget(chat_container)
        
        # --- Right Side: Context Manager Panel ---
        self.context_panel = ContextManagerPanel(self.db, self.notebook_db, self)
        self.splitter.addWidget(self.context_panel)
        
        self.splitter.setSizes([900, 350])
        main_layout.addWidget(self.splitter)

    def update_from_global_selection(self, monday, date_str, tags_str):
        """Called by MainWindow when sidebar selection changes."""
        self.context_panel.sync_with_global(monday, date_str, tags_str)

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
        
        rag_ids = None
        if records:
            rag_ids = [str(r['id']) for r in records]
            for r in records:
                composed = self.db.compose_ai_text(r.get("transcription"), r.get("recording_notes"))
                context_text_parts.append(
                    f"[Meeting: {r['title'] or 'Untitled'} ({r['created_at']})]\n{composed}"
                )

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
        if self.context_panel.current_date_filter:
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
