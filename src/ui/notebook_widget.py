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
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from src.ui.styles import LIST_WIDGET_STYLE
from src.ui.notebooks.actions import (
    add_text_entry,
    apply_transcription_error,
    apply_transcription_result,
    delete_entry_and_audio,
    rename_entry,
)
from src.ui.notebooks.entry_widget import NoteEntryWidget
from src.ui.notebooks.transcription_runtime import NotebookTranscriptionRuntime
from src.ui.notebooks.detail_dialog import NoteDetailDialog
from src.ui.notebooks.view import build_notebook_view

class NotebookWidget(QWidget):
    chat_requested = pyqtSignal(int, str) # id, name
    entries_changed = pyqtSignal()

    def __init__(
        self,
        db_manager,
        notebook_id,
        notebook_name,
        recorder,
        parent=None,
        transcription_runtime=None,
    ):
        super().__init__(parent)
        self.db = db_manager
        self.notebook_id = notebook_id
        self.notebook_name = notebook_name
        self.recorder = recorder
        self.transcription_runtime = transcription_runtime or NotebookTranscriptionRuntime()
        self.recording_timer = QTimer()
        self.recording_timer.timeout.connect(self.update_recording_time)
        self.recording_seconds = 0
        
        self.init_ui()
        self.load_entries()

    def init_ui(self):
        """Build the visual shell through the focused notebooks view owner."""
        build_notebook_view(self)
        self.recorder.amplitude_changed.connect(self.update_vu_meter)
        self._amplitude_connected = True

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
        self.entries_changed.emit()

    def add_text_note(self):
        text, ok = QInputDialog.getMultiLineText(self, "New Note", "Content:")
        if ok and text.strip():
            add_text_entry(self.db, self.notebook_id, text)
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
        self.transcription_runtime.cleanup()
        result = self.transcription_runtime.start(
            file_path,
            lambda response: self.on_transcription_finished(entry_id, response),
            lambda error: self.on_transcription_error(entry_id, error),
        )
        if result.preflight_error:
            QMessageBox.critical(self, "Transcription Error", result.preflight_error)

    def on_transcription_finished(self, entry_id, result):
        apply_transcription_result(self.db, entry_id, result)
        self.load_entries()

    def on_transcription_error(self, entry_id, error):
        apply_transcription_error(self.db, entry_id, error)
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
            rename_entry(self.db, entry['id'], new_title)
            self.load_entries()

    def delete_entry(self, entry):
        reply = QMessageBox.question(self, "Delete Note", 
                                   "Are you sure you want to delete this note?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_entry_and_audio(self.db, entry['id'])
            self.load_entries()

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
        self.transcription_runtime.cleanup()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
