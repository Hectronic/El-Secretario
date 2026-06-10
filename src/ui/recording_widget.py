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
import logging
import soundfile as sf
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QGroupBox, QFrame, QDoubleSpinBox,
                             QMessageBox, QProgressBar, QApplication,
                             QListWidget, QListWidgetItem)
from PyQt6.QtCore import QSettings, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.database import DBManager
from src.audio import trim_audio_segment
from src.worker_components.transcriber_thread import TranscriberThread
from src.stt_providers.sherpa_onnx.model_manager import get_transcription_preflight_error
from src.ai_assistant import AIAssistant
from src.ai_provider import validate_ai_provider_config
from src.ui.speaker_dialog import SpeakerDialog
from src.ui.recording.actions_bar import build_actions_bar
from src.ui.recording.ai_actions import (
    AUTO_SUMMARY_QUEUE_REQUIRED_MESSAGE,
    QUEUE_REQUIRED_MESSAGE,
    apply_ai_result,
    compose_record_ai_text,
    configure_legacy_ai_thread,
    enqueue_post_transcription_summary,
    enqueue_recording_summary,
    enqueue_task_extraction,
    extract_tasks_button_text,
)
from src.ui.recording.audio_trim import (
    mark_trim_end,
    mark_trim_start,
    playhead_seconds,
    trim_recording_audio,
    validate_trim_request,
)
from src.ui.recording.content_tabs import build_content_tabs
from src.ui.recording.controls import create_action_button, create_playback_controls, create_primary_action
from src.ui.recording.metadata_panel import build_metadata_panel
from src.ui.recording.rag_indexing import (
    index_saved_record_changes,
    index_transcription_result_after_refresh,
)
from src.ui.recording.state import (
    fallback_record_title,
    record_has_ai_text,
    recording_audio_path,
    to_bool,
)
from src.ui.recording.speaker_actions import apply_speaker_mapping, find_speaker_labels
from src.ui.recording.transcription_flow import (
    emit_error_trace,
    emit_finished_trace,
    emit_status_trace,
    persist_direct_transcription_result,
    start_direct_transcription,
)
from src.ui.recording.transcription_panel import build_transcription_panel

Recorder = None

class RecordingWidget(QWidget):
    recording_saved = pyqtSignal() # To refresh history list in MainWindow
    recording_deleted = pyqtSignal(int) # Notify MainWindow so duplicate tabs can close
    close_requested = pyqtSignal() # To request closing the tab
    start_chat_requested = pyqtSignal(list) # Emits initial chat contexts
    open_audio_editor_requested = pyqtSignal(int) # Request opening the audio editor tab
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    def __init__(self, rag_engine, recorder=None, record_id=None, task_queue=None, parent=None, audio_edit_mode=False):
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
        self.audio_edit_mode = audio_edit_mode
        self.transcriber_thread = None
        self.ai_thread = None
        self._suppress_dirty_tracking = False
        self._has_unsaved_changes = False
        self._audio_edit_start = 0.0
        self._audio_edit_end = 0.0
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
        self._connect_dirty_tracking()
        
        if self.current_record_id:
            self.load_record(self.current_record_id)
        else:
            self.status_changed.emit("Ready to record")
            self._set_audio_edit_enabled(False)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        if self.audio_edit_mode:
            self._build_audio_editor_ui(layout)
            return

        self._build_transcription_controls(layout)
        self._build_playback_controls(layout)
        self._build_separator(layout)
        self._build_metadata_panel(layout)
        self._build_content_tabs(layout)
        self._build_bottom_actions(layout)

    def _build_transcription_controls(self, layout):
        panel = build_transcription_panel(self, self.retranscribe_recording)
        self.model_combo = panel.model_combo
        self.lang_combo = panel.lang_combo
        self.diarization_check = panel.diarization_check
        self.retranscribe_btn = panel.retranscribe_btn
        layout.addLayout(panel.layout)

    def _build_playback_controls(self, layout):
        playback_controls = create_playback_controls(
            self,
            on_play=self.play_audio,
            on_pause=self.pause_audio,
            on_stop=self.stop_audio,
            on_slider_moved=self.set_position,
            on_volume_changed=self.audio_output.setVolume,
        )
        playback_layout = playback_controls.layout
        self.play_btn = playback_controls.play_btn
        self.pause_btn = playback_controls.pause_btn
        self.stop_btn = playback_controls.stop_btn
        self.slider = playback_controls.slider
        self.time_label = playback_controls.time_label
        self.volume_slider = playback_controls.volume_slider

        self.edit_audio_btn = create_primary_action(
            "Edit Audio in New Tab",
            self.open_audio_editor,
            min_height=38,
            enabled=False,
            parent=self,
        )
        playback_layout.insertWidget(3, self.edit_audio_btn)
        layout.addLayout(playback_layout)

        self.audio_edit_group = None
        self.trim_start_spin = None
        self.trim_end_spin = None
        self.mark_start_btn = None
        self.mark_end_btn = None
        self.trim_btn = None

    def _build_separator(self, layout):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

    def _build_metadata_panel(self, layout):
        panel = build_metadata_panel(self.db.get_all_tags())
        self.title_input = panel.title_input
        self.date_label = panel.date_label
        self.duration_label = panel.duration_label
        self.tags_input = panel.tags_input
        self.is_diarized_check_meta = panel.is_diarized_check
        layout.addWidget(panel.group)

    def _build_content_tabs(self, layout):
        panel = build_content_tabs(
            self,
            self.db,
            self.current_record_id,
            open_speaker_manager=self.open_speaker_manager,
            copy_transcription=self.copy_transcription_to_clipboard,
            on_transcription_text_changed=self._update_transcription_actions,
        )
        self.tabs = panel.tabs
        self.text_display = panel.text_display
        self.notes_display = panel.notes_display
        self.summary_display = panel.summary_display
        self.tasks_widget = panel.tasks_widget
        self.rename_speakers_btn = panel.rename_speakers_btn
        self.copy_transcription_btn = panel.copy_transcription_btn
        layout.addWidget(panel.tabs)

    def _build_bottom_actions(self, layout):
        actions = build_actions_bar(
            self,
            summarize_slot=lambda: self.run_ai_task("summary"),
            extract_tasks_slot=lambda: self.run_ai_task("task_extraction"),
            save_slot=self.save_all_changes,
            ask_slot=self.open_chat_for_recording,
            delete_slot=self.delete_recording,
        )
        self.summarize_btn = actions.summarize_btn
        self.extract_tasks_btn = actions.extract_tasks_btn
        self.save_all_btn = actions.save_all_btn
        self.ask_meeting_btn = actions.ask_meeting_btn
        self.delete_btn = actions.delete_btn
        layout.addLayout(actions.layout)

    def _build_audio_editor_ui(self, layout):
        playback_controls = create_playback_controls(
            self,
            on_play=self.play_audio,
            on_pause=self.pause_audio,
            on_stop=self.stop_audio,
            on_slider_moved=self.set_position,
            on_volume_changed=self.audio_output.setVolume,
        )
        self.play_btn = playback_controls.play_btn
        self.pause_btn = playback_controls.pause_btn
        self.stop_btn = playback_controls.stop_btn
        self.slider = playback_controls.slider
        self.time_label = playback_controls.time_label
        self.volume_slider = playback_controls.volume_slider
        layout.addLayout(playback_controls.layout)

        edit_group = QGroupBox("Audio Edit")
        edit_layout = QVBoxLayout(edit_group)
        edit_layout.setSpacing(8)

        edit_row = QHBoxLayout()
        self.trim_start_spin = QDoubleSpinBox()
        self.trim_start_spin.setDecimals(2)
        self.trim_start_spin.setSingleStep(0.5)
        self.trim_start_spin.setMinimum(0.0)
        self.trim_start_spin.setMaximum(0.0)
        self.trim_start_spin.setSuffix(" s")
        edit_row.addWidget(QLabel("Start:"))
        edit_row.addWidget(self.trim_start_spin)

        self.trim_end_spin = QDoubleSpinBox()
        self.trim_end_spin.setDecimals(2)
        self.trim_end_spin.setSingleStep(0.5)
        self.trim_end_spin.setMinimum(0.0)
        self.trim_end_spin.setMaximum(0.0)
        self.trim_end_spin.setSuffix(" s")
        edit_row.addWidget(QLabel("End:"))
        edit_row.addWidget(self.trim_end_spin)

        self.mark_start_btn = create_action_button(
            "Mark Start",
            self.mark_trim_start_from_playhead,
            parent=self,
        )
        edit_row.addWidget(self.mark_start_btn)

        self.mark_end_btn = create_action_button(
            "Mark End",
            self.mark_trim_end_from_playhead,
            parent=self,
        )
        edit_row.addWidget(self.mark_end_btn)
        edit_row.addStretch()
        edit_layout.addLayout(edit_row)

        trim_row = QHBoxLayout()
        self.trim_btn = create_primary_action(
            "Trim and Retranscribe",
            self.trim_audio_selection,
            parent=self,
        )
        trim_row.addWidget(self.trim_btn)
        trim_row.addStretch()
        edit_layout.addLayout(trim_row)

        layout.addWidget(edit_group)
        self.audio_edit_group = edit_group

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self.duration_label = None
        self.model_combo = None
        self.lang_combo = None
        self.diarization_check = None
        self.title_input = None
        self.save_all_btn = None
        self.date_label = None
        self.duration_label = None
        self.tags_input = None
        self.is_diarized_check_meta = None
        self.tabs = None
        self.text_display = None
        self.notes_display = None
        self.summary_display = None
        self.tasks_widget = None
        self.summarize_btn = None
        self.extract_tasks_btn = None
        self.retranscribe_btn = None
        self.ask_meeting_btn = None
        self.delete_btn = None
        self.rename_speakers_btn = None
        self.copy_transcription_btn = None
        return

    def _connect_dirty_tracking(self):
        for widget_name, signal_name in (
            ("title_input", "textChanged"),
            ("text_display", "textChanged"),
            ("notes_display", "textChanged"),
            ("tags_input", "textChanged"),
            ("is_diarized_check_meta", "stateChanged"),
            ("trim_start_spin", "valueChanged"),
            ("trim_end_spin", "valueChanged"),
        ):
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue
            signal = getattr(widget, signal_name, None)
            if signal is not None:
                signal.connect(self._mark_dirty)

    def _mark_dirty(self, *_args):
        if self._suppress_dirty_tracking:
            return
        self._set_dirty(True)

    def _set_dirty(self, is_dirty: bool):
        self._has_unsaved_changes = bool(is_dirty)
        if getattr(self, "save_all_btn", None):
            self.save_all_btn.setEnabled(self._has_unsaved_changes)

    def has_unsaved_changes(self):
        return self._has_unsaved_changes

    def _set_audio_edit_enabled(self, enabled: bool):
        if not self.audio_edit_group:
            return
        for widget in (
            self.audio_edit_group,
            self.trim_start_spin,
            self.trim_end_spin,
            self.mark_start_btn,
            self.mark_end_btn,
            self.trim_btn,
        ):
            widget.setEnabled(enabled)

    def _configure_audio_edit_bounds(self, duration_seconds: float):
        duration_seconds = max(0.0, float(duration_seconds or 0.0))
        self._audio_edit_start = 0.0
        self._audio_edit_end = duration_seconds
        if not self.audio_edit_group:
            return
        self.trim_start_spin.blockSignals(True)
        self.trim_end_spin.blockSignals(True)
        self.trim_start_spin.setRange(0.0, duration_seconds)
        self.trim_end_spin.setRange(0.0, duration_seconds)
        self.trim_start_spin.setValue(0.0)
        self.trim_end_spin.setValue(duration_seconds)
        self.trim_start_spin.blockSignals(False)
        self.trim_end_spin.blockSignals(False)
        self._set_audio_edit_enabled(duration_seconds > 0.0)

    def _current_playhead_seconds(self):
        return playhead_seconds(self.player.position())

    def _recording_audio_path(self, record):
        return recording_audio_path(record, os.getcwd())

    def _set_record_audio_source(self, record):
        audio_exists = os.path.exists(self.current_recording_path)
        if audio_exists:
            self.enable_playback_controls()
            self.player.setSource(QUrl.fromLocalFile(self.current_recording_path))
        else:
            self.disable_playback_controls()
            self.status_changed.emit("Audio file not found.")
        return audio_exists and record["duration"] > 0.0

    def load_record(self, record_id):
        record = self.db.fetch_record(record_id)
        if not record:
            return
        if self.audio_edit_mode:
            self._load_audio_editor_record(record)
            return
        self._load_record_detail(record)

    def _load_audio_editor_record(self, record):
        self.current_record_id = record["id"]
        self.current_recording_path = self._recording_audio_path(record)
        self._configure_audio_edit_bounds(record["duration"])
        can_edit_audio = self._set_record_audio_source(record)
        self._set_audio_edit_enabled(can_edit_audio)
        self._set_dirty(False)

    def _load_record_detail(self, record):
        self._suppress_dirty_tracking = True
        try:
            self.current_record_id = record["id"]
            self.text_display.setText(record["transcription"])
            self.notes_display.setText(record.get("recording_notes") or "")
            self.summary_display.setText(record["summary"] if record["summary"] else "")
            self.title_input.setText(record["title"] if record["title"] else "")
            self.title_input.setEnabled(True)
            self.tags_input.setText(record["tags"] if record["tags"] else "")
            self.tags_input.setEnabled(True)
            self.is_diarized_check_meta.setChecked(bool(record["is_diarized"]))
            self.is_diarized_check_meta.setEnabled(True)
            self.date_label.setText(record["created_at"])
            self.duration_label.setText(f"{record['duration']:.1f}s")
            self._configure_audio_edit_bounds(record["duration"])

            has_text = record_has_ai_text(record)
            self.summarize_btn.setEnabled(has_text)
            self.extract_tasks_btn.setEnabled(has_text)
            self._update_extract_tasks_button()
            self.rename_speakers_btn.setEnabled(has_text)
            self._update_transcription_actions()

            self.current_recording_path = self._recording_audio_path(record)
            can_edit_audio = self._set_record_audio_source(record)

            self.tasks_widget.record_id = self.current_record_id
            self.tasks_widget.refresh()
            self.ask_meeting_btn.setEnabled(True)
            self.edit_audio_btn.setEnabled(can_edit_audio)
            self._set_audio_edit_enabled(can_edit_audio)
            self._set_dirty(False)
        finally:
            self._suppress_dirty_tracking = False

    def set_transcription_config(self, config):
        if not getattr(self, "model_combo", None):
            return
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
            self.auto_summarize_after_transcription = to_bool(
                config.get("auto_summarize_after_transcription")
            )

    def start_transcription_with_config(self, audio_path, config):
        self.set_transcription_config(config)
        self.start_transcription(audio_path)

    def start_transcription(self, audio_path):
        settings = QSettings("Hectronic", "Secretario")
        self.transcriber_thread = start_direct_transcription(
            self,
            audio_path,
            settings=settings,
            model_size=self.model_combo.currentText(),
            language_label=self.lang_combo.currentText(),
            enable_diarization=self.diarization_check.isChecked(),
            thread_cls=TranscriberThread,
            preflight_check=get_transcription_preflight_error,
            sound_file_cls=sf.SoundFile,
            message_box=QMessageBox,
        )

    def on_transcription_finished(self, result):
        logging.info("Post-transcription checkpoint P1: entered on_transcription_finished record_id=%s", self.current_record_id)
        emit_finished_trace(self.summary_task_queue, self.current_record_id, result)
        logging.info("Post-transcription checkpoint P2: queue trace emitted")
        self.status_changed.emit("Saved.")
        self.progress_changed.emit(-2)
        self.retranscribe_btn.setEnabled(True)
        logging.info("Post-transcription checkpoint P3: UI status/progress updated")
        text = result["text"]
        self.text_display.setText(text)
        self._update_transcription_actions()
        logging.info("Post-transcription checkpoint P4: text set in editor (len=%s)", len(text))
        filename = os.path.basename(self.current_recording_path)
        self.current_record_id = persist_direct_transcription_result(
            self.db,
            self.current_record_id,
            filename,
            result,
        )
        logging.info("Post-transcription checkpoint P5: transcription result persisted")
        logging.info("Post-transcription checkpoint P6: DB updated and record_id=%s", self.current_record_id)
        self.load_record(self.current_record_id)
        logging.info("Post-transcription checkpoint P7: load_record completed")
        self.recording_saved.emit()
        logging.info("Post-transcription checkpoint P8: recording_saved emitted")
        if self.auto_summarize_after_transcription and text.strip():
            self._enqueue_post_transcription_ai_tasks()
            logging.info("Post-transcription checkpoint P9: post-transcription AI tasks enqueued")
        settings = QSettings("Hectronic", "Secretario")
        index_transcription_result_after_refresh(
            rag=self.rag,
            db=self.db,
            settings=settings,
            record_id=self.current_record_id,
            title=filename,
            date_label=self.date_label.text(),
            emit_status=self.status_changed.emit,
        )

    def on_transcription_error(self, err):
        emit_error_trace(self.summary_task_queue, self.current_record_id, err)
        self.status_changed.emit("Failed.")
        self.progress_changed.emit(-2)
        self.retranscribe_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", err)

    def _on_transcriber_status_update(self, message):
        self.status_changed.emit(message)
        emit_status_trace(self.summary_task_queue, self.current_record_id, message)

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
            settings = QSettings("Hectronic", "Secretario")
            index_saved_record_changes(
                rag=self.rag,
                db=self.db,
                settings=settings,
                record_id=self.current_record_id,
                transcription=new_text,
                notes=new_notes,
                title=new_title,
                date_label=self.date_label.text(),
                tags=new_tags,
            )
            self._set_dirty(False)
            self.recording_saved.emit()
            self.status_changed.emit("Saved.")
            return True
        return False

    def run_ai_task(self, task_type):
        text = compose_record_ai_text(
            self.db,
            self.text_display.toPlainText(),
            self.notes_display.toPlainText(),
        )
        if not text:
            return

        title = fallback_record_title(self.current_record_id, self.title_input.text())
        if self.summary_task_queue:
            if task_type == "summary":
                enqueue_recording_summary(self.summary_task_queue, self.current_record_id, text, title)
                return
            if task_type == "task_extraction":
                force_reextract = enqueue_task_extraction(
                    self.summary_task_queue,
                    self.db,
                    self.current_record_id,
                    text,
                    self.tags_input.text(),
                    title,
                )
                if force_reextract:
                    self.tasks_widget.refresh()
                    self._update_extract_tasks_button()
                return
        elif task_type in {"summary", "task_extraction"}:
            QMessageBox.warning(self, "Error", QUEUE_REQUIRED_MESSAGE)
            return

        settings = QSettings("Hectronic", "Secretario")
        is_valid, error_msg = validate_ai_provider_config(settings)
        if not is_valid:
            QMessageBox.warning(self, "Error", error_msg)
            return
        if task_type == "clean":
            return
        self.ai_thread = configure_legacy_ai_thread(self, AIAssistant, task_type, text)

    def _enqueue_post_transcription_ai_tasks(self):
        text = compose_record_ai_text(
            self.db,
            self.text_display.toPlainText(),
            self.notes_display.toPlainText(),
        )
        title = fallback_record_title(self.current_record_id, self.title_input.text())
        if not enqueue_post_transcription_summary(
            self.summary_task_queue,
            self.current_record_id,
            text,
            title,
        ) and text.strip():
            QMessageBox.warning(self, "Error", AUTO_SUMMARY_QUEUE_REQUIRED_MESSAGE)

    def on_ai_finished(self, task_type, result):
        apply_ai_result(self, task_type, result)

    def application_top_level_widgets(self):
        return QApplication.topLevelWidgets()


    def _update_extract_tasks_button(self):
        self.extract_tasks_btn.setText(extract_tasks_button_text(self.db, self.current_record_id))

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

    def _update_transcription_actions(self):
        text = self.text_display.toPlainText() if self.text_display else ""
        has_transcription = bool(text.strip())
        if self.copy_transcription_btn:
            self.copy_transcription_btn.setEnabled(has_transcription)

    def copy_transcription_to_clipboard(self):
        text = self.text_display.toPlainText() if self.text_display else ""
        if not text.strip():
            return
        QApplication.clipboard().setText(text)
        self.status_changed.emit("Transcription copied.")

    def open_speaker_manager(self):
        text = self.text_display.toPlainText()
        speakers = find_speaker_labels(text)
        if not speakers:
            QMessageBox.information(self, "Info", "No speakers found in the text.")
            return
        known_speakers = self.db.get_all_speakers()
        dialog = SpeakerDialog(speakers, self, known_speakers=known_speakers)
        if dialog.exec():
            self.text_display.setText(apply_speaker_mapping(text, dialog.get_mapping()))
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
                self.recording_deleted.emit(self.current_record_id)

    def open_audio_editor(self):
        if self.current_record_id is None:
            return
        self.open_audio_editor_requested.emit(int(self.current_record_id))

    def mark_trim_start_from_playhead(self):
        if not self.trim_start_spin:
            return
        start, end = mark_trim_start(
            self.trim_start_spin.value(),
            self.trim_end_spin.value(),
            self._current_playhead_seconds(),
        )
        self.trim_start_spin.setValue(start)
        self.trim_end_spin.setValue(end)

    def mark_trim_end_from_playhead(self):
        if not self.trim_end_spin:
            return
        start, end = mark_trim_end(
            self.trim_start_spin.value(),
            self.trim_end_spin.value(),
            self._current_playhead_seconds(),
        )
        self.trim_start_spin.setValue(start)
        self.trim_end_spin.setValue(end)

    def trim_audio_selection(self):
        if not self.audio_edit_group:
            return

        start_seconds = float(self.trim_start_spin.value())
        end_seconds = float(self.trim_end_spin.value())
        validation_message = validate_trim_request(self.current_recording_path, start_seconds, end_seconds)
        if validation_message:
            QMessageBox.warning(self, "Error", validation_message)
            return

        try:
            duration = trim_recording_audio(
                self.current_recording_path,
                start_seconds,
                end_seconds,
                trim_audio_segment,
            )
            self.db.update_duration(self.current_record_id, duration)
            if getattr(self, "duration_label", None):
                self.duration_label.setText(f"{duration:.1f}s")
            self._configure_audio_edit_bounds(duration)
            self.player.setSource(QUrl.fromLocalFile(self.current_recording_path))
            self._set_dirty(False)
            self.recording_saved.emit()
            self.status_changed.emit("Audio trimmed. Retranscribing...")
            self.start_transcription(self.current_recording_path)
        except Exception as exc:
            logging.exception("Failed to trim audio for record_id=%s", self.current_record_id)
            QMessageBox.critical(self, "Trim Error", str(exc))

    def open_chat_for_recording(self):
        if not self.current_record_id:
            return
        record = self.db.fetch_record(self.current_record_id)
        if not isinstance(record, dict):
            return
        title = fallback_record_title(self.current_record_id, record.get("title"))
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
        if getattr(self, "ask_meeting_btn", None):
            self.ask_meeting_btn.setEnabled(True)
        if getattr(self, "retranscribe_btn", None):
            self.retranscribe_btn.setEnabled(True)
        if getattr(self, "delete_btn", None):
            self.delete_btn.setEnabled(True)
        if getattr(self, "edit_audio_btn", None):
            self.edit_audio_btn.setEnabled(True)
        
    def disable_playback_controls(self):
        self.play_btn.setEnabled(False); self.pause_btn.setEnabled(False); self.stop_btn.setEnabled(False)
        if getattr(self, "ask_meeting_btn", None):
            self.ask_meeting_btn.setEnabled(False)
        if getattr(self, "retranscribe_btn", None):
            self.retranscribe_btn.setEnabled(False)
        if getattr(self, "delete_btn", None):
            self.delete_btn.setEnabled(False)
        if getattr(self, "edit_audio_btn", None):
            self.edit_audio_btn.setEnabled(False)

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
