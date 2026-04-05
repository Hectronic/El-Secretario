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

import os
import shutil
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QInputDialog, QMessageBox, 
                             QLabel, QTextEdit, QDialog, QDialogButtonBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings
from src.ui.styles import LIST_WIDGET_STYLE
from src.worker import TranscriberThread, get_transcription_preflight_error
from src.transcription_options import get_saved_transcription_model

class NoteEntryWidget(QWidget):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QHBoxLayout()
        title_text = entry['title'] if entry['title'] else entry['created_at']
        type_icon = "🎤" if entry['type'] == 'audio' else "📝"
        
        title = QLabel(f"{type_icon} <b>{title_text}</b>")
        header.addWidget(title)
        header.addStretch()
        
        if entry['type'] == 'audio':
            duration = entry.get('duration', 0) or 0
            mins = int(duration // 60)
            secs = int(duration % 60)
            header.addWidget(QLabel(f"{mins}m {secs}s"))
            
        # Delete Button
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #f44336;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #333;
                border-radius: 15px;
            }
        """)
        del_btn.clicked.connect(self.on_delete_clicked)
        header.addWidget(del_btn)
            
        layout.addLayout(header)
        
        # Content
        content = QLabel(entry['content'])
        content.setWordWrap(True)
        content.setStyleSheet("color: #ccc; margin-top: 5px;")
        layout.addWidget(content)

    def on_delete_clicked(self):
        # We need to signal the parent to delete this entry
        # Since we are inside a QListWidget, we can't easily emit a signal up to NotebookWidget 
        # without defining a custom signal on this widget class.
        if self.parent():
            # Try to find the NotebookWidget parent
            parent = self.parent()
            while parent:
                if isinstance(parent, QListWidget):
                    # We found the list widget, but we need the NotebookWidget
                    # The NotebookWidget is the parent of the QListWidget (usually)
                    # But cleaner way is to emit a signal from this widget
                    break
                parent = parent.parent()
        
        # Let's define a signal on the class
        self.delete_requested.emit()

    delete_requested = pyqtSignal()

class NotebookWidget(QWidget):
    chat_requested = pyqtSignal(int, str) # id, name

    def __init__(self, db_manager, notebook_id, notebook_name, recorder, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.notebook_id = notebook_id
        self.notebook_name = notebook_name
        self.recorder = recorder
        self.transcriber_thread = None
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_seconds = 0
        
        self.init_ui()
        self.load_entries()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel(f"Notebook: {self.notebook_name}")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        add_note_btn = QPushButton("📝 Add Note")
        add_note_btn.clicked.connect(self.add_text_note)
        header.addWidget(add_note_btn)
        
        self.record_btn = QPushButton("🎤 Record Voice Note")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border-radius: 5px;
            }
        """)
        header.addWidget(self.record_btn)
        
        chat_btn = QPushButton("💬 Chat")
        chat_btn.clicked.connect(lambda: self.chat_requested.emit(self.notebook_id, self.notebook_name))
        header.addWidget(chat_btn)
        
        layout.addLayout(header)
        
        # Recording Status (Hidden by default)
        status_layout = QHBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.rec_indicator = QLabel()
        self.rec_indicator.setFixedSize(16, 16)
        self.rec_indicator.setStyleSheet("background-color: red; border-radius: 8px;")
        self.rec_indicator.hide()
        status_layout.addWidget(self.rec_indicator)
        
        self.rec_status = QLabel("Recording: 00:00")
        self.rec_status.setStyleSheet("color: #f44336; font-weight: bold; font-size: 14px;")
        self.rec_status.hide()
        status_layout.addWidget(self.rec_status)
        
        # VU Meter
        self.vu_meter = QProgressBar()
        self.vu_meter.setRange(0, 100)
        self.vu_meter.setTextVisible(False)
        self.vu_meter.setFixedWidth(150)
        self.vu_meter.setFixedHeight(10)
        self.vu_meter.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.vu_meter.hide()
        status_layout.addWidget(self.vu_meter)
        
        layout.addLayout(status_layout)
        
        # Connect recorder amplitude signal
        self.recorder.amplitude_changed.connect(self.update_vu_meter)
        self._amplitude_connected = True
        
        # Entries List
        self.entries_list = QListWidget()
        self.entries_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.entries_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.entries_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entries_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.entries_list)

    def load_entries(self):
        self.entries_list.clear()
        entries = self.db.get_entries(self.notebook_id)
        
        for entry in entries:
            item = QListWidgetItem(self.entries_list)
            widget = NoteEntryWidget(entry)
            widget.delete_requested.connect(lambda e=entry: self.delete_entry(e))
            item.setSizeHint(widget.sizeHint())
            self.entries_list.addItem(item)
            self.entries_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, entry)

    def add_text_note(self):
        text, ok = QInputDialog.getMultiLineText(self, "New Note", "Content:")
        if ok and text.strip():
            self.db.add_text_entry(self.notebook_id, text.strip())
            self.load_entries()

    def toggle_recording(self):
        if self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        try:
            # Ensure directory exists
            audio_dir = os.path.join(os.getcwd(), "notebooks_audio")
            os.makedirs(audio_dir, exist_ok=True)
            
            # We define the target path here, but we'll move the file after recording
            filename = f"note_{self.notebook_id}_{int(self.recording_timer.timerId() or 0)}_{len(self.entries_list)}.wav"
            self.current_audio_path = os.path.join(audio_dir, filename)
            
            self.recorder.start()
            self.recording_seconds = 0
            self.update_recording_time()
            self.recording_timer.start(500) # Update every 500ms for blinking effect
            
            self.record_btn.setText("⏹ Stop Recording")
            self.rec_status.show()
            self.rec_indicator.show()
            self.vu_meter.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start recording: {e}")

    def stop_recording(self):
        # Stop returns the path to the temporary recording
        temp_path = self.recorder.stop()
        self.recording_timer.stop()
        self.record_btn.setText("🎤 Record Voice Note")
        self.rec_status.hide()
        self.rec_indicator.hide()
        self.vu_meter.hide()
        self.vu_meter.setValue(0)
        
        if temp_path and os.path.exists(temp_path):
            # Move to our desired location
            shutil.move(temp_path, self.current_audio_path)
            
            # Add entry to DB
            duration = self.recorder.get_duration(self.current_audio_path)
            entry_id = self.db.add_audio_entry(self.notebook_id, self.current_audio_path, duration)
            
            self.load_entries()
            
            # Start transcription
            self.start_transcription(entry_id, self.current_audio_path)
        else:
            QMessageBox.warning(self, "Warning", "Recording failed or was empty.")

    def update_vu_meter(self, amplitude):
        if self.recorder.is_recording:
            value = int(amplitude * 1000)
            self.vu_meter.setValue(min(value, 100))

    def update_recording_time(self):
        # Blink indicator
        if self.rec_indicator.isVisible():
            current_style = self.rec_indicator.styleSheet()
            if "background-color: red" in current_style:
                self.rec_indicator.setStyleSheet("background-color: #550000; border-radius: 8px;")
            else:
                self.rec_indicator.setStyleSheet("background-color: red; border-radius: 8px;")
        
        # Update time only every second (approx)
        # Since timer is 500ms, we update time every 2 ticks? 
        # Actually simplest is to calculate from start time, but let's just increment by 0.5s logic
        # Or just keep simple seconds counter and update text.
        # Let's just toggle blink every 500ms and update text every 1000ms
        
        # We can use a counter
        if not hasattr(self, '_blink_counter'):
            self._blink_counter = 0
        self._blink_counter += 1
        
        if self._blink_counter % 2 == 0:
            self.recording_seconds += 1
            mins = self.recording_seconds // 60
            secs = self.recording_seconds % 60
            self.rec_status.setText(f"Recording: {mins:02d}:{secs:02d}")

    def start_transcription(self, entry_id, file_path):
        # Use existing worker logic with auto GPU detection
        settings = QSettings("Hectronic", "Secretario")
        force_cpu = settings.value("force_cpu", False, type=bool)
        compute_type = settings.value("compute_type", "auto")
        transcription_backend = settings.value("transcription_backend", "auto")
        model_size = get_saved_transcription_model(settings)
        preflight_error = get_transcription_preflight_error(model_size, settings)
        if preflight_error:
            QMessageBox.critical(self, "Transcription Error", preflight_error)
            return
        if compute_type == "auto":
            compute_type = None

        self._cleanup_transcriber_thread()
        self.transcriber_thread = TranscriberThread(
            file_path,
            model_size=model_size,
            compute_type=compute_type,
            force_cpu=force_cpu,
            backend_preference=transcription_backend,
        )
        self.transcriber_thread.finished.connect(lambda res: self.on_transcription_finished(entry_id, res))
        self.transcriber_thread.error.connect(lambda err: self.on_transcription_error(entry_id, err))
        self.transcriber_thread.finished.connect(self._clear_transcriber_thread_ref)
        self.transcriber_thread.start()

    def on_transcription_finished(self, entry_id, result):
        text = result.get('text', '')
        self.db.update_entry_content(entry_id, text)
        self.load_entries()

    def on_transcription_error(self, entry_id, error):
        self.db.update_entry_content(entry_id, f"Transcription Failed: {error}")
        self.load_entries()

    def on_item_double_clicked(self, item):
        entry = item.data(Qt.ItemDataRole.UserRole)
        
        dialog = NoteDetailDialog(entry, self)
        if dialog.exec():
            new_content = dialog.get_content()
            if new_content != entry['content']:
                self.db.update_entry_content(entry['id'], new_content)
                self.load_entries()

    def show_context_menu(self, pos):
        item = self.entries_list.itemAt(pos)
        if not item:
            return
            
        entry = item.data(Qt.ItemDataRole.UserRole)
        
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        menu = QMenu(self)
        
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self.rename_entry(entry))
        menu.addAction(rename_action)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(lambda: self.delete_entry(entry))
        menu.addAction(delete_action)
        
        menu.exec(self.entries_list.mapToGlobal(pos))

    def rename_entry(self, entry):
        current_title = entry['title'] if entry['title'] else ""
        new_title, ok = QInputDialog.getText(self, "Rename Note", "New Title:", text=current_title)
        if ok:
            self.db.rename_entry(entry['id'], new_title.strip())
            self.load_entries()

    def delete_entry(self, entry):
        reply = QMessageBox.question(self, "Delete Note", 
                                   "Are you sure you want to delete this note?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            file_path = self.db.delete_entry(entry['id'])
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file: {e}")
            self.load_entries()

    def _clear_transcriber_thread_ref(self, *args):
        thread = self.transcriber_thread
        self.transcriber_thread = None
        if thread:
            thread.deleteLater()

    def _cleanup_transcriber_thread(self):
        if self.transcriber_thread and self.transcriber_thread.isRunning():
            try:
                self.transcriber_thread.requestInterruption()
                self.transcriber_thread.quit()
                self.transcriber_thread.wait(3000)
            except Exception:
                pass
        if self.transcriber_thread:
            try:
                self.transcriber_thread.deleteLater()
            except Exception:
                pass
        self.transcriber_thread = None

    def cleanup(self):
        self.recording_timer.stop()
        if self.recorder.is_recording:
            try:
                self.recorder.stop()
            except Exception:
                pass
        if self._amplitude_connected:
            try:
                self.recorder.amplitude_changed.disconnect(self.update_vu_meter)
            except Exception:
                pass
            self._amplitude_connected = False
        self._cleanup_transcriber_thread()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

class NoteDetailDialog(QDialog):
    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.setWindowTitle(entry['title'] if entry['title'] else "Note Details")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Title (Editable if needed, but let's stick to content for now as per request "appear larger")
        # Actually user might want to edit title too, but let's focus on content.
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(entry['content'])
        self.text_edit.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.text_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_content(self):
        return self.text_edit.toPlainText()
