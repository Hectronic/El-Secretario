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

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QFormLayout, 
                             QLineEdit, QGroupBox, QTabWidget, QFrame, 
                             QMessageBox, QApplication, QSplitter, QListWidget, QListWidgetItem, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings
from src.database import DBManager
from src.ui.components import TagsLineEdit
from src.ai_assistant import AIAssistant
from src.ui.tasks_list_widget import TasksListWidget

class NoteWidget(QWidget):
    note_saved = pyqtSignal()
    close_requested = pyqtSignal()
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    def __init__(self, rag_engine, record_id=None, task_queue=None, parent=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        self.current_record_id = record_id
        self.summary_task_queue = task_queue
        self.ai_thread = None

        self.init_ui()
        if self.current_record_id:
            self.load_note(self.current_record_id)
        else:
            self.status_changed.emit("New Note")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Meta data
        meta_group = QGroupBox("Note Details")
        meta_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter title...")
        
        self.save_btn = QPushButton("Save Note")
        self.save_btn.clicked.connect(self.save_note)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        title_row = QHBoxLayout()
        title_row.addWidget(self.title_input)
        title_row.addWidget(self.save_btn)
        meta_layout.addRow("Title:", title_row)
        
        self.tags_input = TagsLineEdit()
        all_tags = self.db.get_all_tags()
        self.tags_input.set_tags(all_tags)
        meta_layout.addRow("Tags:", self.tags_input)
        
        self.date_label = QLabel("-")
        meta_layout.addRow("Date:", self.date_label)
        
        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)

        # Editor and Preview
        self.tabs = QTabWidget()
        
        # Editor Tab
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        self.content_editor = QTextEdit()
        self.content_editor.setPlaceholderText("Write your note here using Markdown...")
        self.content_editor.textChanged.connect(self.update_preview)
        editor_layout.addWidget(self.content_editor)
        self.tabs.addTab(editor_widget, "Editor")
        
        # Preview Tab
        self.preview_display = QTextEdit()
        self.preview_display.setReadOnly(True)
        self.tabs.addTab(self.preview_display, "Preview")
        
        # Summary Tab
        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setPlaceholderText("Summary will appear here...")
        self.tabs.addTab(self.summary_display, "Summary")

        # Tasks Tab
        self.tasks_widget = TasksListWidget(self.db, record_id=self.current_record_id, parent=self)
        self.tabs.addTab(self.tasks_widget, "Tasks")

        layout.addWidget(self.tabs)

        # AI Buttons
        ai_layout = QHBoxLayout()
        self.summarize_btn = QPushButton("Summarize (AI)")
        self.summarize_btn.clicked.connect(lambda: self.run_ai_task("summary"))
        ai_layout.addWidget(self.summarize_btn)

        self.extract_tasks_btn = QPushButton("Extract Tasks (AI)")
        self.extract_tasks_btn.clicked.connect(lambda: self.run_ai_task("task_extraction"))
        ai_layout.addWidget(self.extract_tasks_btn)
        
        layout.addLayout(ai_layout)

        # Delete button
        self.delete_btn = QPushButton("Delete Note")
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_note)
        layout.addWidget(self.delete_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def update_preview(self):
        self.preview_display.setMarkdown(self.content_editor.toPlainText())

    def load_note(self, record_id):
        record = self.db.fetch_record(record_id)
        if record:
            self.current_record_id = record['id']
            self.title_input.setText(record['title'] or "")
            self.content_editor.setPlainText(record['transcription'] or "")
            self.tags_input.setText(record['tags'] or "")
            self.summary_display.setText(record['summary'] or "")
            self.date_label.setText(record['created_at'])
            self.update_preview()
            self.tasks_widget.record_id = self.current_record_id
            self.tasks_widget.refresh()

    def save_note(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Warning", "Please enter a title.")
            return
        
        content = self.content_editor.toPlainText()
        tags = self.tags_input.text().strip()
        
        if self.current_record_id:
            self.db.update_title(self.current_record_id, title)
            self.db.update_transcription(self.current_record_id, content)
            self.db.update_tags(self.current_record_id, tags)
        else:
            self.current_record_id = self.db.save(filename="", text=content, duration=0.0, title=title, type='note')
            self.db.update_tags(self.current_record_id, tags)
            # Reload to get date
            self.load_note(self.current_record_id)
            
        if self.rag:
            settings = QSettings("Hectronic", "Secretario")
            if settings.value("auto_index_rag", True, type=bool):
                self.rag.add_document(self.current_record_id, content, {"title": title, "type": "note", "tags": tags})
            
        self.note_saved.emit()
        self.status_changed.emit("Note saved.")

    def run_ai_task(self, task_type):
        text = self.content_editor.toPlainText()
        if not text: return
        
        if self.summary_task_queue:
            if task_type == "summary":
                self.summary_task_queue.enqueue_recording_summary(
                    self.current_record_id, 
                    text, 
                    self.title_input.text() or f"Note {self.current_record_id}"
                )
                return
            elif task_type == "task_extraction":
                self.summary_task_queue.enqueue_task_extraction(
                    self.current_record_id, 
                    text, 
                    self.tags_input.text(),
                    self.title_input.text() or f"Note {self.current_record_id}"
                )
                return

        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        if not is_valid:
            QMessageBox.warning(self, "Error", error_msg)
            return

        self.status_changed.emit(f"Running {task_type}...")
        self.progress_changed.emit(-1)
        self.ai_thread = AIAssistant("", task_type, text)
        self.ai_thread.task_completed.connect(self.on_ai_finished)
        self.ai_thread.error.connect(self.on_ai_error)
        self.ai_thread.finished.connect(self._clear_ai_thread_ref)
        self.ai_thread.start()

    def on_ai_finished(self, task_type, result):
        self.status_changed.emit("AI Task Done.")
        self.progress_changed.emit(-2)
        if task_type == "summary":
            self.summary_display.setText(result)
            self.db.update_ai_content(self.current_record_id, summary=result)
            self.tabs.setCurrentIndex(2) # Summary tab
        elif task_type == "task_extraction":
            self.tasks_widget.refresh()
            self._refresh_global_tasks_sidebar()

    def _refresh_global_tasks_sidebar(self):
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "refresh_tasks_sidebar"):
                widget.refresh_tasks_sidebar()

    def on_ai_error(self, err):
        self.status_changed.emit("AI Task Failed.")
        self.progress_changed.emit(-2)
        QMessageBox.critical(self, "Error", err)

    def _clear_ai_thread_ref(self):
        self.ai_thread = None

    def delete_note(self):
        if self.current_record_id:
            if QMessageBox.question(self, "Delete", "Are you sure you want to delete this note?") == QMessageBox.StandardButton.Yes:
                self.db.delete(self.current_record_id)
                if self.rag:
                    try: self.rag.delete_document(str(self.current_record_id))
                    except Exception: pass
                self.note_saved.emit()
                self.close_requested.emit()
        else:
            self.close_requested.emit()

    def cleanup(self):
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.requestInterruption()
            self.ai_thread.quit()
            self.ai_thread.wait(3000)
