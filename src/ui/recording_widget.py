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
import re
import soundfile as sf
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QComboBox, QFormLayout, 
                             QLineEdit, QGroupBox, QTabWidget, QFrame, 
                             QMessageBox, QStyle, QSlider, QProgressBar, QApplication, QCheckBox)
from PyQt6.QtCore import Qt, QSettings, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QCursor

from src.database import DBManager
from src.audio import Recorder
from src.worker import TranscriberThread
from src.ai_assistant import AIAssistant
from src.ui.dialogs import SpeakerDialog
from src.ui.components import TagsLineEdit

class RecordingWidget(QWidget):
    recording_saved = pyqtSignal() # To refresh history list in MainWindow
    close_requested = pyqtSignal() # To request closing the tab

    def __init__(self, rag_engine, recorder=None, record_id=None, parent=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        self.recorder = recorder or Recorder()
        # Note: VU meter connection removed - recording is now handled by RecordingInProgressWidget
        self.current_record_id = record_id
        self.current_recording_path = None
        
        # Audio Player Setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.media_state_changed)

        self.init_ui()
        
        if self.current_record_id:
            self.load_record(self.current_record_id)
        else:
            # If no record_id, we are in "New Recording" mode
            self.status_label.setText("Ready to record")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Transcription Controls (for retranscription)
        transcription_layout = QHBoxLayout()
        
        transcription_layout.addWidget(QLabel("Retranscription Options:"))
        
        # Model Selector
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.model_combo.setCurrentText("base")
        transcription_layout.addWidget(QLabel("Model:"))
        transcription_layout.addWidget(self.model_combo)
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Auto", "Spanish", "English"])
        transcription_layout.addWidget(QLabel("Language:"))
        transcription_layout.addWidget(self.lang_combo)

        self.diarization_check = QCheckBox("Diarization")
        self.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
        transcription_layout.addWidget(self.diarization_check)
        
        transcription_layout.addStretch()
        
        layout.addLayout(transcription_layout)

        # Playback Controls
        playback_layout = QHBoxLayout()
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.clicked.connect(self.play_audio)
        self.play_btn.setEnabled(False)
        playback_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.pause_btn.clicked.connect(self.pause_audio)
        self.pause_btn.setEnabled(False)
        playback_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop_audio)
        self.stop_btn.setEnabled(False)
        playback_layout.addWidget(self.stop_btn)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
        playback_layout.addWidget(self.slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        playback_layout.addWidget(self.time_label)

        # Volume Control
        vol_label = QLabel("Vol:")
        playback_layout.addWidget(vol_label)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.audio_output.setVolume)
        self.audio_output.setVolume(0.7)
        playback_layout.addWidget(self.volume_slider)
        
        layout.addLayout(playback_layout)
        
        # Visual Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Metadata Group
        meta_group = QGroupBox("Recording Details")
        meta_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter title...")
        self.title_input.setEnabled(False)
        
        self.save_all_btn = QPushButton("Save All Changes")
        self.save_all_btn.clicked.connect(self.save_all_changes)
        self.save_all_btn.setEnabled(False)
        
        title_row = QHBoxLayout()
        title_row.addWidget(self.title_input)
        title_row.addWidget(self.save_all_btn)
        
        meta_layout.addRow("Title:", title_row)
        
        self.date_label = QLabel("-")
        meta_layout.addRow("Date/Time:", self.date_label)
        
        self.duration_label = QLabel("-")
        meta_layout.addRow("Duration:", self.duration_label)
        
        self.tags_input = TagsLineEdit()
        self.tags_input.setEnabled(False)
        
        # Setup Autocomplete for Tags
        all_tags = self.db.get_all_tags()
        self.tags_input.set_tags(all_tags)
        
        meta_layout.addRow("Tags:", self.tags_input)

        self.is_diarized_check_meta = QCheckBox("Diarized")
        self.is_diarized_check_meta.setEnabled(False)
        meta_layout.addRow("", self.is_diarized_check_meta)
        
        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)
        
        # Tabs for Content
        self.tabs = QTabWidget()
        
        # Original Tab
        original_widget = QWidget()
        original_layout = QVBoxLayout(original_widget)
        
        orig_toolbar = QHBoxLayout()
        self.rename_speakers_btn = QPushButton("Rename Speakers")
        self.rename_speakers_btn.clicked.connect(self.open_speaker_manager)
        self.rename_speakers_btn.setEnabled(False)
        orig_toolbar.addWidget(self.rename_speakers_btn)
        orig_toolbar.addStretch()
        original_layout.addLayout(orig_toolbar)
        
        self.text_display = QTextEdit()
        self.text_display.setPlaceholderText("Transcription will appear here...")
        original_layout.addWidget(self.text_display)
        self.tabs.addTab(original_widget, "Original")
        
        self.cleaned_display = QTextEdit()
        self.cleaned_display.setReadOnly(True)
        self.cleaned_display.setPlaceholderText("Cleaned text will appear here...")
        self.tabs.addTab(self.cleaned_display, "Cleaned")
        
        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setPlaceholderText("Summary will appear here...")
        self.tabs.addTab(self.summary_display, "Summary")
        
        layout.addWidget(self.tabs)
        
        # AI Actions
        ai_layout = QHBoxLayout()
        self.clean_btn = QPushButton("Clean Text (AI)")
        self.clean_btn.clicked.connect(lambda: self.run_ai_task("clean"))
        self.clean_btn.setEnabled(False)
        ai_layout.addWidget(self.clean_btn)
        
        self.summarize_btn = QPushButton("Summarize (AI)")
        self.summarize_btn.clicked.connect(lambda: self.run_ai_task("summary"))
        self.summarize_btn.setEnabled(False)
        ai_layout.addWidget(self.summarize_btn)
        
        layout.addLayout(ai_layout)

        # Management
        mgmt_layout = QHBoxLayout()
        self.retranscribe_btn = QPushButton("Retranscribe")
        self.retranscribe_btn.clicked.connect(self.retranscribe_recording)
        self.retranscribe_btn.setEnabled(False)
        mgmt_layout.addWidget(self.retranscribe_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("color: red;")
        self.delete_btn.clicked.connect(self.delete_recording)
        self.delete_btn.setEnabled(False)
        mgmt_layout.addWidget(self.delete_btn)
        
        layout.addLayout(mgmt_layout)
        
        # Status Bar (Bottom)
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)



    def load_record(self, record_id):
        records = self.db.fetch_all()
        record = next((r for r in records if r['id'] == record_id), None)
        if record:
            self.current_record_id = record['id']
            self.text_display.setText(record['transcription'])
            self.cleaned_display.setText(record['cleaned_text'] if record['cleaned_text'] else "")
            self.summary_display.setText(record['summary'] if record['summary'] else "")
            self.title_input.setText(record['title'] if record['title'] else "")
            self.title_input.setEnabled(True)
            self.tags_input.setText(record['tags'] if record['tags'] else "")
            self.tags_input.setText(record['tags'] if record['tags'] else "")
            self.tags_input.setEnabled(True)
            self.is_diarized_check_meta.setChecked(bool(record['is_diarized']))
            self.is_diarized_check_meta.setEnabled(True)
            self.save_all_btn.setEnabled(True)
            self.date_label.setText(record['created_at'])
            self.duration_label.setText(f"{record['duration']:.1f}s")
            
            has_text = bool(record['transcription'])
            self.clean_btn.setEnabled(has_text)
            self.summarize_btn.setEnabled(has_text)
            self.rename_speakers_btn.setEnabled(has_text)
            
            filename = record['filename']
            self.current_recording_path = os.path.join(os.getcwd(), "recordings", filename)
            
            if os.path.exists(self.current_recording_path):
                self.enable_playback_controls()
                self.player.setSource(QUrl.fromLocalFile(self.current_recording_path))
            else:
                self.disable_playback_controls()
                self.status_label.setText("Audio file not found.")



    def set_transcription_config(self, config):
        """Set transcription configuration from external source."""
        if config.get("model"):
            index = self.model_combo.findText(config["model"])
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        
        if config.get("language") is not None:
            lang_reverse_map = {None: "Auto", "es": "Spanish", "en": "English"}
            lang_text = lang_reverse_map.get(config["language"], "Auto")
            index = self.lang_combo.findText(lang_text)
            if index >= 0:
                self.lang_combo.setCurrentIndex(index)
        
        if config.get("diarization") is not None:
            self.diarization_check.setChecked(config["diarization"])

    def start_transcription_with_config(self, audio_path, config):
        """Start transcription with external configuration."""
        self.set_transcription_config(config)
        self.start_transcription(audio_path)

    def start_transcription(self, audio_path):
        print(f"DEBUG: start_transcription called with {audio_path}")
        self.status_label.setText("Processing transcription...")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.retranscribe_btn.setEnabled(False)
        
        lang_map = {"Auto": None, "Spanish": "es", "English": "en"}
        selected_lang = self.lang_combo.currentText()
        language_code = lang_map.get(selected_lang)
        model_size = self.model_combo.currentText()
        
        settings = QSettings("Hectronic", "Secretario")
        hf_token = settings.value("hf_token", "")
        enable_diarization = self.diarization_check.isChecked()
        
        settings = QSettings("Hectronic", "Secretario")
        hf_token = settings.value("hf_token", "")
        enable_diarization = self.diarization_check.isChecked()
        force_cpu = settings.value("force_cpu", False, type=bool)
        compute_type = settings.value("compute_type", "int8")
        # If "auto", pass None to let TranscriberThread auto-detect
        if compute_type == "auto":
            compute_type = None
        
        # Get duration for progress calculation
        duration = 0
        try:
            f = sf.SoundFile(audio_path)
            duration = len(f) / f.samplerate
        except: pass
        
        self.transcriber_thread = TranscriberThread(audio_path, model_size=model_size, compute_type=compute_type, language=language_code, hf_token=hf_token, enable_diarization=enable_diarization, total_duration=duration, force_cpu=force_cpu)
        self.transcriber_thread.finished.connect(self.on_transcription_finished)
        self.transcriber_thread.progress.connect(self.progress_bar.setValue)
        self.transcriber_thread.status_update.connect(self.status_label.setText)
        self.transcriber_thread.error.connect(self.on_transcription_error)
        self.transcriber_thread.start()

    def on_transcription_finished(self, result):
        self.status_label.setText("Saved.")
        self.progress_bar.setVisible(False)
        self.retranscribe_btn.setEnabled(True)
        
        text = result["text"]
        self.text_display.setText(text)
        
        # Log transcription
        if self.current_record_id:
             # If we are retranscribing, we should probably log it too.
             self.db.log_transcription(
                model_name=result["model_name"],
                audio_duration=result["audio_duration"],
                audio_size_bytes=result["audio_size_bytes"],
                transcription_time_seconds=result["transcription_time"],
                record_id=self.current_record_id
            )
        
        duration = result["audio_duration"]
            
        filename = os.path.basename(self.current_recording_path)
        
        if self.current_record_id:
            # Update transcription and duration for existing record
            self.db.update_transcription(self.current_record_id, text, is_diarized=result.get("is_diarized", False), transcription_model=result.get("model_name"))
            self.db.update_duration(self.current_record_id, duration)
        else:
            self.db.save(filename, text, duration, is_diarized=result.get("is_diarized", False), transcription_model=result.get("model_name"))
            # Find new ID
            records = self.db.fetch_all()
            if records:
                self.current_record_id = records[0]['id']
                
            # Log transcription for new record
            self.db.log_transcription(
                model_name=result["model_name"],
                audio_duration=result["audio_duration"],
                audio_size_bytes=result["audio_size_bytes"],
                transcription_time_seconds=result["transcription_time"],
                record_id=self.current_record_id
            )
        
        self.load_record(self.current_record_id)
        self.recording_saved.emit()
        
        if self.rag:
            self.rag.add_document(self.current_record_id, text, {"title": filename, "date": self.date_label.text()})

    def on_transcription_error(self, err):
        self.status_label.setText("Failed.")
        self.progress_bar.setVisible(False)
        self.retranscribe_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", err)

    def save_all_changes(self):
        if self.current_record_id:
            new_title = self.title_input.text().strip()
            new_text = self.text_display.toPlainText()
            new_tags = self.tags_input.text().strip()
            
            self.db.update_title(self.current_record_id, new_title)
            self.db.update_transcription(self.current_record_id, new_text)
            new_tags = self.tags_input.text().strip()
            is_diarized = self.is_diarized_check_meta.isChecked()
            
            self.db.update_transcription(self.current_record_id, new_text, is_diarized=is_diarized)
            self.db.update_tags(self.current_record_id, new_tags)
            
            if self.rag:
                self.rag.add_document(self.current_record_id, new_text, {"title": new_title, "date": self.date_label.text(), "tags": new_tags})
            
            self.recording_saved.emit()
            self.status_label.setText("Saved.")

    def run_ai_task(self, task_type):
        text = self.text_display.toPlainText()
        if not text: return
        
        settings = QSettings("Hectronic", "Secretario")
        
        # Validate AI provider configuration
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        if not is_valid:
            QMessageBox.warning(self, "Error", error_msg)
            return
            
        self.status_label.setText(f"Running {task_type}...")
        # api_key parameter kept for backward compatibility
        self.ai_thread = AIAssistant("", task_type, text)
        self.ai_thread.finished.connect(self.on_ai_finished)
        self.ai_thread.error.connect(self.on_ai_error)
        self.ai_thread.start()

    def on_ai_finished(self, task_type, result):
        self.status_label.setText("AI Task Done.")
        if task_type == "summary":
            self.summary_display.setText(result)
            self.db.update_ai_content(self.current_record_id, summary=result)
            self.tabs.setCurrentIndex(2)
        else:
            self.cleaned_display.setText(result)
            self.db.update_ai_content(self.current_record_id, cleaned_text=result)
            self.tabs.setCurrentIndex(1)

    def on_ai_error(self, err):
        self.status_label.setText("AI Task Failed.")
        QMessageBox.critical(self, "Error", err)

    def open_speaker_manager(self):
        text = self.text_display.toPlainText()
        # Find all unique speaker tags like SPEAKER_00, SPEAKER_01
        speakers = sorted(list(set(re.findall(r"SPEAKER_\d+", text))))
        
        if not speakers:
            QMessageBox.information(self, "Info", "No speakers found in the text.")
            return

        known_speakers = self.db.get_all_speakers()
        dialog = SpeakerDialog(speakers, self, known_speakers=known_speakers)
        if dialog.exec():
            mapping = dialog.get_mapping()
            # Apply mapping to text
            for spk, new_name in mapping.items():
                # Use regex to replace whole words only to avoid partial matches if any
                # But SPEAKER_00 is quite specific, simple replace might suffice.
                # Let's use simple replace for now as these tags are distinct.
                text = text.replace(spk, new_name)
            
            self.text_display.setText(text)
            self.save_all_changes()

    def retranscribe_recording(self):
        print(f"DEBUG: retranscribe_recording called. Path: {self.current_recording_path}")
        if self.current_recording_path:
            self.start_transcription(self.current_recording_path)
        else:
            print("DEBUG: No current recording path")

    def delete_recording(self):
        if self.current_record_id:
            if QMessageBox.question(self, "Delete", "Are you sure?") == QMessageBox.StandardButton.Yes:
                filename = self.db.delete(self.current_record_id)
                
                # Delete file
                if filename:
                    try:
                        file_path = os.path.join(os.getcwd(), "recordings", filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        print(f"Error deleting file {filename}: {e}")
                
                # Delete from RAG
                if self.rag:
                    try:
                        self.rag.delete_document(str(self.current_record_id))
                    except Exception as e:
                        print(f"Error deleting from RAG: {e}")
                
                self.recording_saved.emit()
                self.close_requested.emit()

    # Audio Player Methods
    def play_audio(self): self.player.play()
    def pause_audio(self): self.player.pause()
    def stop_audio(self): self.player.stop()
    def position_changed(self, p): self.slider.setValue(p)
    def duration_changed(self, d): self.slider.setRange(0, d)
    def set_position(self, p): self.player.setPosition(p)
    def media_state_changed(self, s):
        if self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia: self.stop_audio()
    def enable_playback_controls(self):
        self.play_btn.setEnabled(True); self.pause_btn.setEnabled(True); self.stop_btn.setEnabled(True)
        self.retranscribe_btn.setEnabled(True); self.delete_btn.setEnabled(True)
    def disable_playback_controls(self):
        self.play_btn.setEnabled(False); self.pause_btn.setEnabled(False); self.stop_btn.setEnabled(False)
        self.retranscribe_btn.setEnabled(False); self.delete_btn.setEnabled(False)


