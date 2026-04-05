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
# along with this program.  See <https://www.gnu.org/licenses/>.

import os
import re
import logging
import soundfile as sf
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QComboBox, QFormLayout, 
                             QLineEdit, QGroupBox, QTabWidget, QFrame, 
                             QMessageBox, QStyle, QSlider, QProgressBar, QApplication, QCheckBox,
                             QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QSettings, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QCursor

from src.database import DBManager
from src.worker import TranscriberThread, get_transcription_preflight_error
from src.ai_assistant import AIAssistant
from src.ui.dialogs import SpeakerDialog
from src.ui.components import TagsLineEdit
from src.ui.tasks_list_widget import TasksListWidget
from src.transcription_options import DEFAULT_TRANSCRIPTION_MODEL, get_transcription_model_options

Recorder = None

class RecordingWidget(QWidget):
    recording_saved = pyqtSignal() # To refresh history list in MainWindow
    close_requested = pyqtSignal() # To request closing the tab
    start_chat_requested = pyqtSignal(list) # Emits initial chat contexts
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    def __init__(self, rag_engine, recorder=None, record_id=None, task_queue=None, parent=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        if recorder is not None:
            self.recorder = recorder
        else:
            global Recorder
            if Recorder is None:
                from src.audio import Recorder as _Recorder
                Recorder = _Recorder
            self.recorder = Recorder()
        self.summary_task_queue = task_queue
        self.current_record_id = record_id
        self.current_recording_path = None
        self.transcriber_thread = None
        self.ai_thread = None
        settings = QSettings("Hectronic", "Secretario")
        self.auto_summarize_after_transcription = settings.value(
            "rec_config/auto_summarize_after_transcription",
            False,
            type=bool,
        )
        
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
            self.status_changed.emit("Ready to record")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Transcription Controls (for retranscription)
        transcription_layout = QHBoxLayout()
        transcription_layout.addWidget(QLabel("Retranscription Options:"))
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(get_transcription_model_options())
        self.model_combo.setCurrentText(DEFAULT_TRANSCRIPTION_MODEL)
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
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
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
        all_tags = self.db.get_all_tags()
        self.tags_input.set_tags(all_tags)
        meta_layout.addRow("Tags:", self.tags_input)

        self.is_diarized_check_meta = QCheckBox("Diarized")
        self.is_diarized_check_meta.setEnabled(False)
        meta_layout.addRow("", self.is_diarized_check_meta)
        meta_group.setLayout(meta_layout)
        layout.addWidget(meta_group)
        
        self.tabs = QTabWidget()
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

        self.notes_display = QTextEdit()
        self.notes_display.setPlaceholderText("Add notes for this recording...")
        self.tabs.addTab(self.notes_display, "Notes")
        
        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setPlaceholderText("Summary will appear here...")
        self.tabs.addTab(self.summary_display, "Summary")

        # Tasks Tab
        self.tasks_widget = TasksListWidget(self.db, record_id=self.current_record_id, parent=self)
        self.tabs.addTab(self.tasks_widget, "Tasks")
        layout.addWidget(self.tabs)
        
        bottom_actions_layout = QHBoxLayout()
        bottom_actions_layout.setSpacing(12)
        bottom_actions_layout.setContentsMargins(0, 6, 0, 2)

        ai_layout = QHBoxLayout()
        ai_layout.setSpacing(10)
        self.summarize_btn = QPushButton("Summarize (AI)")
        self.summarize_btn.setProperty("class", "calendar-nav-btn")
        self.summarize_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.summarize_btn.setMinimumHeight(36)
        self.summarize_btn.clicked.connect(lambda: self.run_ai_task("summary"))
        self.summarize_btn.setEnabled(False)
        ai_layout.addWidget(self.summarize_btn)

        self.extract_tasks_btn = QPushButton("Extract Tasks (AI)")
        self.extract_tasks_btn.setProperty("class", "calendar-nav-btn")
        self.extract_tasks_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.extract_tasks_btn.setMinimumHeight(36)
        self.extract_tasks_btn.clicked.connect(lambda: self.run_ai_task("task_extraction"))
        self.extract_tasks_btn.setEnabled(False)
        ai_layout.addWidget(self.extract_tasks_btn)

        self.retranscribe_btn = QPushButton("Retranscribe")
        self.retranscribe_btn.setProperty("class", "calendar-nav-btn")
        self.retranscribe_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.retranscribe_btn.setMinimumHeight(38)
        self.retranscribe_btn.clicked.connect(self.retranscribe_recording)
        self.retranscribe_btn.setEnabled(False)
        ai_layout.addWidget(self.retranscribe_btn)

        bottom_actions_layout.addLayout(ai_layout)
        bottom_actions_layout.addStretch()

        self.ask_meeting_btn = QPushButton("Ask About This Meeting")
        self.ask_meeting_btn.setProperty("class", "calendar-primary-btn")
        self.ask_meeting_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.ask_meeting_btn.setMinimumHeight(38)
        self.ask_meeting_btn.clicked.connect(self.open_chat_for_recording)
        self.ask_meeting_btn.setEnabled(False)
        bottom_actions_layout.addWidget(self.ask_meeting_btn)
        bottom_actions_layout.addSpacing(18)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "record-del-btn")
        self.delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.delete_btn.setMinimumHeight(38)
        self.delete_btn.setMinimumWidth(110)
        self.delete_btn.clicked.connect(self.delete_recording)
        self.delete_btn.setEnabled(False)
        bottom_actions_layout.addWidget(self.delete_btn)
        bottom_actions_layout.addSpacing(8)

        layout.addLayout(bottom_actions_layout)

    def load_record(self, record_id):
        record = self.db.fetch_record(record_id)
        if record:
            self.current_record_id = record['id']
            self.text_display.setText(record['transcription'])
            self.notes_display.setText(record.get('recording_notes') or "")
            self.summary_display.setText(record['summary'] if record['summary'] else "")
            self.title_input.setText(record['title'] if record['title'] else "")
            self.title_input.setEnabled(True)
            self.tags_input.setText(record['tags'] if record['tags'] else "")
            self.tags_input.setEnabled(True)
            self.is_diarized_check_meta.setChecked(bool(record['is_diarized']))
            self.is_diarized_check_meta.setEnabled(True)
            self.save_all_btn.setEnabled(True)
            self.date_label.setText(record['created_at'])
            self.duration_label.setText(f"{record['duration']:.1f}s")
            
            has_text = bool((record.get('transcription') or '').strip() or (record.get('recording_notes') or '').strip())
            self.summarize_btn.setEnabled(has_text)
            self.extract_tasks_btn.setEnabled(has_text)
            self._update_extract_tasks_button()
            self.rename_speakers_btn.setEnabled(has_text)
            
            filename = record['filename']
            self.current_recording_path = os.path.join(os.getcwd(), "recordings", filename)
            
            if os.path.exists(self.current_recording_path):
                self.enable_playback_controls()
                self.player.setSource(QUrl.fromLocalFile(self.current_recording_path))
            else:
                self.disable_playback_controls()
                self.status_changed.emit("Audio file not found.")
                
            self.tasks_widget.record_id = self.current_record_id
            self.tasks_widget.refresh()
            self.ask_meeting_btn.setEnabled(True)

    def set_transcription_config(self, config):
        if config.get("model"):
            index = self.model_combo.findText(config["model"])
            if index >= 0: self.model_combo.setCurrentIndex(index)
        if config.get("language") is not None:
            lang_reverse_map = {None: "Auto", "es": "Spanish", "en": "English"}
            lang_text = lang_reverse_map.get(config["language"], "Auto")
            index = self.lang_combo.findText(lang_text)
            if index >= 0: self.lang_combo.setCurrentIndex(index)
        if config.get("diarization") is not None:
            self.diarization_check.setChecked(config["diarization"])
        if config.get("auto_summarize_after_transcription") is not None:
            self.auto_summarize_after_transcription = self._to_bool(
                config.get("auto_summarize_after_transcription")
            )

    def start_transcription_with_config(self, audio_path, config):
        self.set_transcription_config(config)
        self.start_transcription(audio_path)

    def start_transcription(self, audio_path):
        self.status_changed.emit("Processing transcription...")
        self.progress_changed.emit(0)
        self.retranscribe_btn.setEnabled(False)
        lang_map = {"Auto": None, "Spanish": "es", "English": "en"}
        language_code = lang_map.get(self.lang_combo.currentText())
        model_size = self.model_combo.currentText()
        settings = QSettings("Hectronic", "Secretario")
        hf_token = settings.value("hf_token", "")
        enable_diarization = self.diarization_check.isChecked()
        force_cpu = settings.value("force_cpu", False, type=bool)
        compute_type = settings.value("compute_type", "auto")
        transcription_backend = settings.value("transcription_backend", "auto")
        preflight_error = get_transcription_preflight_error(model_size, settings)
        if preflight_error:
            self.status_changed.emit("Failed.")
            self.progress_changed.emit(-2)
            self.retranscribe_btn.setEnabled(True)
            QMessageBox.critical(self, "Transcription Error", preflight_error)
            return
        if compute_type == "auto": compute_type = None
        duration = 0
        try:
            f = sf.SoundFile(audio_path)
            duration = len(f) / f.samplerate
        except: pass
        self.transcriber_thread = TranscriberThread(
            audio_path,
            model_size=model_size,
            compute_type=compute_type,
            language=language_code,
            hf_token=hf_token,
            enable_diarization=enable_diarization,
            total_duration=duration,
            force_cpu=force_cpu,
            backend_preference=transcription_backend,
        )
        self.transcriber_thread.finished.connect(self.on_transcription_finished)
        self.transcriber_thread.progress.connect(self.progress_changed.emit)
        self.transcriber_thread.status_update.connect(self._on_transcriber_status_update)
        self.transcriber_thread.error.connect(self.on_transcription_error)
        self.transcriber_thread.finished.connect(self._clear_transcriber_thread_ref)
        self.transcriber_thread.start()

    def on_transcription_finished(self, result):
        logging.info("Post-transcription checkpoint P1: entered on_transcription_finished record_id=%s", self.current_record_id)
        if self.summary_task_queue and hasattr(self.summary_task_queue, "add_external_trace"):
            backend = result.get("backend", "unknown")
            model_name = result.get("model_name", "unknown")
            device = result.get("device", "unknown")
            compute_type = result.get("compute_type", "unknown")
            self.summary_task_queue.add_external_trace(
                f"Direct transcription finished: backend={backend}, model={model_name}, device={device}, compute={compute_type}",
                {"type": "transcription", "record_id": self.current_record_id or -1},
                event="finished",
            )
        logging.info("Post-transcription checkpoint P2: queue trace emitted")
        self.status_changed.emit("Saved.")
        self.progress_changed.emit(-2)
        self.retranscribe_btn.setEnabled(True)
        logging.info("Post-transcription checkpoint P3: UI status/progress updated")
        text = result["text"]
        self.text_display.setText(text)
        logging.info("Post-transcription checkpoint P4: text set in editor (len=%s)", len(text))
        if self.current_record_id:
             self.db.log_transcription(model_name=result["model_name"], audio_duration=result["audio_duration"], audio_size_bytes=result["audio_size_bytes"], transcription_time_seconds=result["transcription_time"], record_id=self.current_record_id)
        logging.info("Post-transcription checkpoint P5: transcription metrics logged")
        duration = result["audio_duration"]
        filename = os.path.basename(self.current_recording_path)
        if self.current_record_id:
            self.db.update_transcription(self.current_record_id, text, is_diarized=result.get("is_diarized", False), transcription_model=result.get("model_name"))
            self.db.update_duration(self.current_record_id, duration)
        else:
            self.current_record_id = self.db.save(filename, text, duration, is_diarized=result.get("is_diarized", False), transcription_model=result.get("model_name"))
            self.db.log_transcription(model_name=result["model_name"], audio_duration=result["audio_duration"], audio_size_bytes=result["audio_size_bytes"], transcription_time_seconds=result["transcription_time"], record_id=self.current_record_id)
        logging.info("Post-transcription checkpoint P6: DB updated and record_id=%s", self.current_record_id)
        self.load_record(self.current_record_id)
        logging.info("Post-transcription checkpoint P7: load_record completed")
        self.recording_saved.emit()
        logging.info("Post-transcription checkpoint P8: recording_saved emitted")
        if self.auto_summarize_after_transcription and text.strip():
            self._enqueue_post_transcription_ai_tasks()
            logging.info("Post-transcription checkpoint P9: post-transcription AI tasks enqueued")
        if self.rag:
            settings = QSettings("Hectronic", "Secretario")
            if self._should_auto_index_rag(settings):
                logging.info("Post-transcription checkpoint P10: RAG auto-index enabled")
                ai_text = self.db.get_record_ai_text(self.current_record_id)
                logging.info("Post-transcription checkpoint P11: fetched ai_text (len=%s)", len(ai_text or ""))
                self.rag.add_document(self.current_record_id, ai_text, {"title": filename, "date": self.date_label.text()})
                logging.info("Post-transcription checkpoint P12: rag.add_document completed")
            else:
                self.status_changed.emit("RAG auto-index skipped (auto_index_rag=false).")
                logging.info("Post-transcription checkpoint P10b: RAG auto-index skipped by settings")

    def on_transcription_error(self, err):
        if self.summary_task_queue and hasattr(self.summary_task_queue, "add_external_trace"):
            self.summary_task_queue.add_external_trace(
                f"Direct transcription failed: {err}",
                {"type": "transcription", "record_id": self.current_record_id or -1},
                event="failed",
            )
        self.status_changed.emit("Failed.")
        self.progress_changed.emit(-2)
        self.retranscribe_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", err)

    def _on_transcriber_status_update(self, message):
        self.status_changed.emit(message)
        if self.summary_task_queue and hasattr(self.summary_task_queue, "add_external_trace"):
            self.summary_task_queue.add_external_trace(
                message,
                {"type": "transcription", "record_id": self.current_record_id or -1},
                event="trace",
            )

    def save_all_changes(self):
        if self.current_record_id:
            new_title = self.title_input.text().strip()
            new_text = self.text_display.toPlainText()
            new_notes = self.notes_display.toPlainText().strip()
            new_tags = self.tags_input.text().strip()
            is_diarized = self.is_diarized_check_meta.isChecked()
            self.db.update_title(self.current_record_id, new_title)
            self.db.update_transcription(self.current_record_id, new_text, is_diarized=is_diarized)
            self.db.update_recording_notes(self.current_record_id, new_notes)
            self.db.update_tags(self.current_record_id, new_tags)
            if self.rag:
                settings = QSettings("Hectronic", "Secretario")
                if self._should_auto_index_rag(settings):
                    ai_text = self.db.compose_ai_text(new_text, new_notes)
                    self.rag.add_document(self.current_record_id, ai_text, {"title": new_title, "date": self.date_label.text(), "tags": new_tags})
            self.recording_saved.emit()
            self.status_changed.emit("Saved.")

    def run_ai_task(self, task_type):
        text = self.db.compose_ai_text(self.text_display.toPlainText(), self.notes_display.toPlainText())
        if not text: return
        
        if self.summary_task_queue:
            if task_type == "summary":
                self.summary_task_queue.enqueue_recording_summary(
                    self.current_record_id, 
                    text, 
                    self.title_input.text() or f"Recording {self.current_record_id}"
                )
                return
            elif task_type == "task_extraction":
                force_reextract = bool(self.current_record_id and self.db.has_ai_tasks_for_record(self.current_record_id))
                if force_reextract:
                    self.db.delete_ai_tasks_by_record(self.current_record_id)
                    self.tasks_widget.refresh()
                    self._update_extract_tasks_button()
                self.summary_task_queue.enqueue_task_extraction(
                    self.current_record_id, 
                    text, 
                    self.tags_input.text(),
                    self.title_input.text() or f"Recording {self.current_record_id}",
                    force=force_reextract,
                )
                return
        elif task_type in {"summary", "task_extraction"}:
            QMessageBox.warning(self, "Error", "Summary and task extraction must run through the central queue.")
            return

        settings = QSettings("Hectronic", "Secretario")
        from src.ai_provider import validate_ai_provider_config
        is_valid, error_msg = validate_ai_provider_config(settings)
        if not is_valid:
            QMessageBox.warning(self, "Error", error_msg)
            return
        if task_type == "clean": return
        self.status_changed.emit(f"Running {task_type}...")
        self.progress_changed.emit(-1)
        self.ai_thread = AIAssistant("", task_type, text)
        self.ai_thread.task_completed.connect(self.on_ai_finished)
        self.ai_thread.error.connect(self.on_ai_error)
        self.ai_thread.finished.connect(self._clear_ai_thread_ref)
        self.ai_thread.error.connect(self._clear_ai_thread_ref)
        self.ai_thread.start()

    def _enqueue_post_transcription_ai_tasks(self):
        """When auto mode is enabled, run both summary and task extraction."""
        text = self.db.compose_ai_text(self.text_display.toPlainText(), self.notes_display.toPlainText())
        if not text.strip():
            return
        title = self.title_input.text() or f"Recording {self.current_record_id}"
        tags = self.tags_input.text()

        if self.summary_task_queue:
            self.summary_task_queue.enqueue_recording_summary(
                self.current_record_id,
                text,
                title,
            )
        else:
            QMessageBox.warning(self, "Error", "Automatic summary requires the central queue to be available.")

    @staticmethod
    def _to_bool(value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    @staticmethod
    def _should_auto_index_rag(settings: QSettings) -> bool:
        return settings.value("auto_index_rag", True, type=bool)

    def on_ai_finished(self, task_type, result):
        self.status_changed.emit("AI Task Done.")
        self.progress_changed.emit(-2)
        if task_type == "summary":
            self.summary_display.setText(result)
            self.db.update_ai_content(self.current_record_id, summary=result)
            self.tabs.setCurrentWidget(self.summary_display)
        elif task_type == "task_extraction":
            self.tasks_widget.refresh()
            self._refresh_global_tasks_sidebar()

    def _refresh_global_tasks_sidebar(self):
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "refresh_tasks_sidebar"):
                widget.refresh_tasks_sidebar()

    def _update_extract_tasks_button(self):
        has_ai_tasks = False
        if self.current_record_id:
            try:
                has_ai_tasks = self.db.has_ai_tasks_for_record(self.current_record_id)
            except Exception:
                has_ai_tasks = False
        self.extract_tasks_btn.setText("Re-extract Tasks (AI)" if has_ai_tasks else "Extract Tasks (AI)")

    def refresh_from_background_queue(self, include_summary=False, include_tasks=False):
        """
        Refresh UI sections after queue-completed tasks while this tab is open.
        Keeps user context (doesn't force tab switches or overwrite editable fields).
        """
        if not self.current_record_id:
            return
        if include_summary:
            rec = self.db.fetch_record(self.current_record_id)
            if isinstance(rec, dict):
                self.summary_display.setText(rec.get("summary") or "")
        if include_tasks:
            self.tasks_widget.refresh()
        self._update_extract_tasks_button()

    def on_ai_error(self, err):
        self.status_changed.emit("AI Task Failed.")
        self.progress_changed.emit(-2)
        QMessageBox.critical(self, "Error", err)

    def open_speaker_manager(self):
        text = self.text_display.toPlainText()
        speakers = sorted(list(set(re.findall(r"SPEAKER_\d+", text))))
        if not speakers:
            QMessageBox.information(self, "Info", "No speakers found in the text.")
            return
        known_speakers = self.db.get_all_speakers()
        dialog = SpeakerDialog(speakers, self, known_speakers=known_speakers)
        if dialog.exec():
            mapping = dialog.get_mapping()
            for spk, new_name in mapping.items():
                text = text.replace(spk, new_name)
            self.text_display.setText(text)
            self.save_all_changes()

    def retranscribe_recording(self):
        if self.current_recording_path:
            self.start_transcription(self.current_recording_path)

    def delete_recording(self):
        if self.current_record_id:
            if QMessageBox.question(self, "Delete", "Are you sure?") == QMessageBox.StandardButton.Yes:
                filename = self.db.delete(self.current_record_id)
                if filename:
                    try:
                        file_path = os.path.join(os.getcwd(), "recordings", filename)
                        if os.path.exists(file_path): os.remove(file_path)
                    except Exception as e: print(f"Error deleting file {filename}: {e}")
                if self.rag:
                    try: self.rag.delete_document(str(self.current_record_id))
                    except Exception: pass
                self.recording_saved.emit()
                self.close_requested.emit()

    def open_chat_for_recording(self):
        if not self.current_record_id:
            return
        record = self.db.fetch_record(self.current_record_id)
        if not isinstance(record, dict):
            return
        title = (record.get("title") or f"Recording {self.current_record_id}").strip()
        contexts = [
            {
                "type": "recording",
                "value": int(self.current_record_id),
                "label": title,
            }
        ]
        self.start_chat_requested.emit(contexts)

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
        self.ask_meeting_btn.setEnabled(True); self.retranscribe_btn.setEnabled(True); self.delete_btn.setEnabled(True)
        
    def disable_playback_controls(self):
        self.play_btn.setEnabled(False); self.pause_btn.setEnabled(False); self.stop_btn.setEnabled(False)
        self.ask_meeting_btn.setEnabled(False); self.retranscribe_btn.setEnabled(False); self.delete_btn.setEnabled(False)

    def _clear_transcriber_thread_ref(self, *args):
        thread = self.transcriber_thread
        self.transcriber_thread = None
        if thread: thread.deleteLater()

    def _clear_ai_thread_ref(self, *args):
        thread = self.ai_thread
        self.ai_thread = None
        if thread: thread.deleteLater()

    def _cleanup_thread(self, attr_name):
        thread = getattr(self, attr_name, None)
        if not thread: return
        try:
            if thread.isRunning():
                thread.requestInterruption()
                thread.quit()
                thread.wait(3000)
        except Exception: pass
        try: thread.deleteLater()
        except Exception: pass
        setattr(self, attr_name, None)

    def cleanup(self):
        self.stop_audio()
        self.player.setSource(QUrl())
        self._cleanup_thread("transcriber_thread")
        self._cleanup_thread("ai_thread")

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
