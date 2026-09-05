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
from src.ui.speaker_dialog import SpeakerDialog
from src.ui.recording.actions_bar import build_actions_bar
from src.ui.recording import layout as recording_layout
from src.ui.recording.ai_orchestration import RecordingAiCoordinator
from src.ui.recording.audio_trim import (
    mark_trim_end,
    mark_trim_start,
    playhead_seconds,
    trim_recording_audio,
    validate_trim_request,
)
from src.ui.recording.content_tabs import build_content_tabs
from src.ui.recording.controls import create_action_button, create_playback_controls, create_primary_action
from src.ui.recording.record_details import RecordingDetailsCoordinator
from src.ui.recording.metadata_panel import build_metadata_panel
from src.ui.recording.record_actions import RecordingActionsCoordinator
from src.ui.recording.state import recording_audio_path
from src.ui.recording.speaker_actions import apply_speaker_mapping, find_speaker_labels
from src.ui.recording.transcription_actions import RecordingTranscriptionCoordinator
from src.ui.recording.widget_support import RecordingWidgetSupport
from src.ai_assistant import AIAssistant
from src.ai_provider import validate_ai_provider_config
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
        self.record_actions = RecordingActionsCoordinator(self)
        self.record_details = RecordingDetailsCoordinator(self)
        self.transcription_actions = RecordingTranscriptionCoordinator(self)
        self.ai_actions = RecordingAiCoordinator(self)
        self.widget_support = RecordingWidgetSupport(self)

        self.init_ui()
        self._connect_dirty_tracking()
        
        if self.current_record_id:
            self.load_record(self.current_record_id)
        else:
            self.status_changed.emit("Ready to record")
            self._set_audio_edit_enabled(False)

    def init_ui(self):
        recording_layout.init_ui(self)

    def _build_transcription_controls(self, layout):
        recording_layout._build_transcription_controls(self, layout)

    def _build_playback_controls(self, layout):
        recording_layout._build_playback_controls(self, layout)

    def _build_separator(self, layout):
        recording_layout._build_separator(self, layout)

    def _build_metadata_panel(self, layout):
        recording_layout._build_metadata_panel(self, layout)

    def _build_content_tabs(self, layout):
        recording_layout._build_content_tabs(self, layout)

    def _build_bottom_actions(self, layout):
        recording_layout._build_bottom_actions(self, layout)

    def _build_audio_editor_ui(self, layout):
        recording_layout._build_audio_editor_ui(self, layout)

    def _connect_dirty_tracking(self):
        self.widget_support.connect_dirty_tracking()

    def _mark_dirty(self, *_args):
        self.widget_support.mark_dirty(*_args)

    def _set_dirty(self, is_dirty: bool):
        self.widget_support.set_dirty(is_dirty)

    def has_unsaved_changes(self):
        return self.widget_support.has_unsaved_changes()

    def _set_audio_edit_enabled(self, enabled: bool):
        self.widget_support.set_audio_edit_enabled(enabled)

    def _configure_audio_edit_bounds(self, duration_seconds: float):
        self.widget_support.configure_audio_edit_bounds(duration_seconds)

    def _current_playhead_seconds(self):
        return playhead_seconds(self.player.position())

    def _recording_audio_path(self, record):
        return self.widget_support.recording_audio_path(record)

    def _set_record_audio_source(self, record):
        return self.widget_support.set_record_audio_source(record, qurl=QUrl)

    def load_record(self, record_id):
        self.record_details.load_record(record_id)

    def set_transcription_config(self, config):
        self.transcription_actions.set_transcription_config(config)

    def start_transcription_with_config(self, audio_path, config):
        self.set_transcription_config(config)
        self.start_transcription(audio_path)

    def start_transcription(self, audio_path):
        self.transcription_actions.start_transcription(
            audio_path,
            settings_cls=QSettings,
            thread_cls=TranscriberThread,
            preflight_check=get_transcription_preflight_error,
            sound_file_cls=sf.SoundFile,
            message_box=QMessageBox,
        )

    def on_transcription_finished(self, result):
        self.transcription_actions.on_transcription_finished(result, settings_cls=QSettings)

    def on_transcription_error(self, err):
        self.transcription_actions.on_transcription_error(err, message_box=QMessageBox)

    def _on_transcriber_status_update(self, message):
        self.transcription_actions.on_status_update(message)

    def save_all_changes(self):
        return self.record_details.save_all_changes()

    def run_ai_task(self, task_type):
        self.ai_actions.run_ai_task(
            task_type,
            settings_cls=QSettings,
            assistant_cls=AIAssistant,
            validate_provider=validate_ai_provider_config,
            message_box=QMessageBox,
        )

    def _enqueue_post_transcription_ai_tasks(self):
        self.ai_actions.enqueue_post_transcription_ai_tasks(message_box=QMessageBox)

    def on_ai_finished(self, task_type, result):
        self.ai_actions.on_ai_finished(task_type, result)

    def application_top_level_widgets(self):
        return QApplication.topLevelWidgets()


    def _update_extract_tasks_button(self):
        self.ai_actions.update_extract_tasks_button()

    def refresh_from_background_queue(self, include_summary=False, include_tasks=False):
        self.ai_actions.refresh_from_background_queue(include_summary, include_tasks)

    def on_ai_error(self, err):
        self.ai_actions.on_ai_error(err, message_box=QMessageBox)

    def _update_transcription_actions(self):
        self.widget_support.update_transcription_actions()

    def copy_transcription_to_clipboard(self):
        self.widget_support.copy_transcription_to_clipboard(application=QApplication)

    def open_speaker_manager(self):
        self.widget_support.open_speaker_manager(dialog_cls=SpeakerDialog, message_box=QMessageBox)

    def retranscribe_recording(self):
        self.widget_support.retranscribe_recording()

    def delete_recording(self):
        self.record_actions.delete_recording()

    def open_audio_editor(self):
        self.record_actions.open_audio_editor()

    def mark_trim_start_from_playhead(self):
        self.widget_support.mark_trim_start()

    def mark_trim_end_from_playhead(self):
        self.widget_support.mark_trim_end()

    def trim_audio_selection(self):
        self.widget_support.trim_audio_selection(
            trim_func=trim_audio_segment, qurl=QUrl, message_box=QMessageBox
        )

    def open_chat_for_recording(self):
        self.record_actions.open_chat_for_recording()

    def play_audio(self): self.record_actions.play_audio()
    def pause_audio(self): self.record_actions.pause_audio()
    def stop_audio(self): self.record_actions.stop_audio()
    def position_changed(self, p): self.record_actions.position_changed(p)
    def duration_changed(self, d): self.record_actions.duration_changed(d)
    def set_position(self, p): self.record_actions.set_position(p)
    def media_state_changed(self, s): self.record_actions.media_state_changed(s)
    def enable_playback_controls(self):
        self.record_actions.enable_playback_controls()
        
    def disable_playback_controls(self):
        self.record_actions.disable_playback_controls()

    def _clear_transcriber_thread_ref(self, *args):
        self.widget_support.clear_thread_ref("transcriber_thread")

    def _clear_ai_thread_ref(self, *args):
        self.widget_support.clear_thread_ref("ai_thread")

    def _cleanup_thread(self, attr_name):
        self.widget_support.cleanup_thread(attr_name)

    def cleanup(self):
        self.widget_support.cleanup(qurl=QUrl)

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
