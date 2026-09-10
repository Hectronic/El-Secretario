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

from __future__ import annotations

import logging
import os

import soundfile as sf
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import QMessageBox, QWidget

from src.audio import Recorder
from src.database import DBManager
from src.ui.audio_editor.editing_state import AudioChunk
from src.ui.audio_editor.layout import build_audio_editor_layout
from src.ui.audio_editor.persistence import apply_edited_audio
from src.ui.audio_editor.playback import AudioEditorPlaybackController
from src.ui.audio_editor.selection import AudioEditorSelectionController
from src.ui.audio_editor.session import AudioEditorSession
from src.ui.audio_editor.transcription_runtime import AudioEditorTranscriptionRuntime


class AudioEditorWidget(QWidget):
    recording_saved = pyqtSignal()
    recording_deleted = pyqtSignal(int)
    close_requested = pyqtSignal()
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    # Compatibility proxies keep the established widget state observable while the
    # non-Qt session owns it. Existing integrations may inspect these attributes.
    current_audio = property(lambda self: self.session.current_audio, lambda self, value: setattr(self.session, "current_audio", value))
    current_sample_rate = property(lambda self: self.session.sample_rate, lambda self, value: setattr(self.session, "sample_rate", value))
    current_duration = property(lambda self: self.session.duration, lambda self, value: setattr(self.session, "duration", value))
    preview_audio = property(lambda self: self.session.preview_audio, lambda self, value: setattr(self.session, "preview_audio", value))
    preview_ranges = property(lambda self: self.session.preview_ranges, lambda self, value: setattr(self.session, "preview_ranges", value))
    chunks = property(lambda self: self.session.chunks, lambda self, value: setattr(self.session, "chunks", value))
    active_chunk_index = property(lambda self: self.session.active_chunk_index, lambda self, value: setattr(self.session, "active_chunk_index", value))
    selection_start = property(lambda self: self.session.selection_start, lambda self, value: setattr(self.session, "selection_start", value))
    selection_end = property(lambda self: self.session.selection_end, lambda self, value: setattr(self.session, "selection_end", value))
    _has_unsaved_changes = property(lambda self: self.session.has_unsaved_changes, lambda self, value: setattr(self.session, "has_unsaved_changes", value))
    _boundary_drag_history_pending = property(lambda self: self.session.boundary_drag_history_pending, lambda self, value: setattr(self.session, "boundary_drag_history_pending", value))
    preview_temp_path = property(
        lambda self: self.playback.preview_temp_path,
        lambda self, value: setattr(self.playback, "preview_temp_path", value),
    )
    _suppress_signals = property(
        lambda self: self.selection.suppress_signals,
        lambda self, value: setattr(self.selection, "suppress_signals", value),
    )

    def __init__(
        self,
        rag_engine,
        recorder=None,
        record_id=None,
        task_queue=None,
        parent=None,
        persistence=None,
        transcription_runtime=None,
    ):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = persistence if persistence is not None else DBManager()
        self.recorder = recorder if recorder is not None else Recorder()
        self.summary_task_queue = task_queue
        self.session = AudioEditorSession()
        self.current_record_id = record_id
        self.current_recording_path = None
        self.current_audio = None
        self.current_sample_rate = 16000
        self.current_duration = 0.0
        self.preview_audio = None
        self.preview_ranges = []
        self.chunks = []
        self.active_chunk_index = -1
        self.selection_start = 0.0
        self.selection_end = 0.0
        self._has_unsaved_changes = False
        self.transcription_runtime = transcription_runtime or AudioEditorTranscriptionRuntime()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.media_state_changed)
        self.audio_output.setVolume(0.7)
        self.playback = AudioEditorPlaybackController(self.player, self.audio_output)
        self._init_ui()
        if self.current_record_id:
            self.load_record(self.current_record_id)
        else:
            self.status_changed.emit("Ready.")

    def _init_ui(self):
        build_audio_editor_layout(self)
        self.selection = AudioEditorSelectionController(
            self.session,
            self.waveform,
            self.chunk_list,
            self.selection_start_spin,
            self.selection_end_spin,
            self._fmt_seconds,
        )
        self._set_editor_enabled(False)

    def _set_editor_enabled(self, enabled: bool):
        for widget in (
            self.play_btn,
            self.pause_btn,
            self.stop_btn,
            self.slider,
            self.time_label,
            self.volume_slider,
            self.selection_start_spin,
            self.selection_end_spin,
            self.mark_start_btn,
            self.mark_end_btn,
            self.split_btn,
            self.cut_btn,
            self.chunk_list,
            self.up_btn,
            self.down_btn,
            self.delete_chunk_btn,
            self.reset_btn,
            self.apply_btn,
        ):
            widget.setEnabled(enabled)

    def load_record(self, record_id):
        record = self.db.fetch_record(record_id)
        if not record:
            return
        self.current_record_id = record["id"]
        self.current_recording_path = os.path.join(os.getcwd(), "recordings", record["filename"])
        self.title_label.setText(record.get("title") or f"Recording {record_id}")
        self.file_info_label.setText(f"{record.get('duration', 0.0):.1f}s, loading...")

        if not os.path.exists(self.current_recording_path):
            self._set_editor_enabled(False)
            self.status_changed.emit("Audio file not found.")
            return

        self._load_audio_buffer(self.current_recording_path)
        self._set_editor_enabled(True)
        self._clear_history()
        self._mark_clean()

    def _load_audio_buffer(self, path: str):
        audio, sample_rate = sf.read(path, always_2d=True, dtype="float32")
        self.session.load_audio(audio, sample_rate)
        self._rebuild_preview()

    def _rebuild_preview(self):
        if not self.chunks or self.current_audio is None:
            self.preview_audio = None
            self.preview_ranges = []
            self.waveform.set_audio(None, self.current_sample_rate)
            self.waveform.set_chunk_ranges([], -1)
            self._refresh_chunk_list()
            self._update_time_label()
            self._refresh_preview_player()
            return

        self.session.rebuild_preview()
        self.waveform.set_audio(self.preview_audio, self.current_sample_rate)
        self.waveform.set_chunk_ranges(self.preview_ranges, self.active_chunk_index)
        self._refresh_chunk_list()
        self._update_active_selection_from_chunk()
        self._update_time_label()
        self._refresh_preview_player()

    def _refresh_preview_player(self):
        self.playback.refresh_preview(self.preview_audio, self.current_sample_rate)

    def _refresh_chunk_list(self):
        self.selection.refresh_chunks()

    def _update_active_selection_from_chunk(self):
        self.selection.sync_active_selection()

    def _on_waveform_selection_changed(self, start: float, end: float):
        self.selection.from_waveform(start, end)

    def _on_spin_selection_changed(self, *_args):
        self.selection.from_spins()

    def _on_chunk_row_changed(self, row: int):
        self.selection.select_chunk(row)

    def _on_waveform_chunk_clicked(self, index: int):
        self.selection.select_waveform_chunk(index)

    def _on_waveform_boundary_dragged(self, side: str, boundary_time: float):
        if self.selection.suppress_signals:
            return
        if not (0 <= self.active_chunk_index < len(self.chunks)):
            return
        self.adjust_active_chunk_boundary(side, boundary_time)

    def _on_boundary_drag_started(self):
        self._boundary_drag_history_pending = True

    def _on_boundary_drag_finished(self):
        self._boundary_drag_history_pending = False

    def _chunk_for_selection(self):
        try:
            return self.session.selection_range(), None
        except ValueError as exc:
            return None, str(exc)

    def _selection_to_chunk(self):
        active, error = self._chunk_for_selection()
        if error:
            raise ValueError(error)
        return active

    def split_selection(self):
        try:
            active = self._selection_to_chunk()
        except ValueError as exc:
            QMessageBox.warning(self, "Split", str(exc))
            return

        self.session.split_selection()
        self._rebuild_preview()

    def cut_selection(self):
        try:
            active = self._selection_to_chunk()
        except ValueError as exc:
            QMessageBox.warning(self, "Cut", str(exc))
            return

        self.session.cut_selection()
        self._rebuild_preview()

    def delete_chunk(self):
        try:
            changed = self.session.delete_active_chunk()
        except ValueError as exc:
            QMessageBox.warning(self, "Delete Chunk", str(exc))
            return
        if not changed:
            return
        self._rebuild_preview()

    def move_chunk(self, offset: int):
        if not self.session.move_active_chunk(offset):
            return
        self._rebuild_preview()

    def adjust_active_chunk_boundary(self, side: str, boundary_time: float):
        if not self.session.adjust_active_boundary(side, boundary_time):
            return False
        self._rebuild_preview()
        return True

    def reset_edits(self):
        if not self.session.reset():
            return
        self._rebuild_preview()

    def _mark_dirty(self):
        self.session.mark_dirty()

    def _mark_clean(self):
        self.session.mark_clean()

    def has_unsaved_changes(self):
        return self.session.has_unsaved_changes

    def _clear_history(self):
        self.session.clear_history()

    def _push_undo_state(self):
        self.session.history.push(self.chunks, self.active_chunk_index)

    def undo(self):
        if not self.session.undo():
            return False
        self._rebuild_preview()
        self.status_changed.emit("Undo")
        return True

    def redo(self):
        if not self.session.redo():
            return False
        self._rebuild_preview()
        self.status_changed.emit("Redo")
        return True

    def save_all_changes(self):
        return self.apply_edits()

    def apply_edits(self):
        if not self.preview_audio is None and len(self.preview_audio) == 0:
            QMessageBox.warning(self, "Apply Edits", "The edited audio would be empty.")
            return False
        if self.current_recording_path is None or not os.path.exists(self.current_recording_path):
            QMessageBox.warning(self, "Apply Edits", "Audio file not available.")
            return False
        if self.preview_audio is None or not len(self.preview_audio):
            QMessageBox.warning(self, "Apply Edits", "No audio loaded.")
            return False

        try:
            self.current_duration = apply_edited_audio(
                self.current_recording_path,
                self.preview_audio,
                self.current_sample_rate,
                self.db,
                self.current_record_id,
            )
            self.status_changed.emit("Audio updated.")
            self.recording_saved.emit()
            self.session.accept_saved_preview(self.current_duration)
            self._rebuild_preview()
            self._retranscribe_current_audio()
            return True
        except Exception as exc:
            logging.exception("Failed applying audio edits for record_id=%s", self.current_record_id)
            QMessageBox.critical(self, "Apply Edits", str(exc))
            return False

    def _retranscribe_current_audio(self):
        if not self.current_recording_path:
            return
        result = self.transcription_runtime.start(
            self.current_recording_path,
            self.current_duration,
            self._on_transcription_finished,
            self._on_transcription_error,
            lambda: self.progress_changed.emit(0),
        )
        if result.preflight_error:
            QMessageBox.critical(self, "Transcription Error", result.preflight_error)

    def _on_transcription_finished(self, result):
        self.progress_changed.emit(-2)
        text = result.get("text", "")
        if self.current_record_id:
            self.db.update_transcription(
                self.current_record_id,
                text,
                is_diarized=result.get("is_diarized", False),
                transcription_model=result.get("model_name"),
            )
            self.db.log_transcription(
                model_name=result.get("model_name", ""),
                audio_duration=result.get("audio_duration", 0.0),
                audio_size_bytes=result.get("audio_size_bytes", 0),
                transcription_time_seconds=result.get("transcription_time", 0.0),
                record_id=self.current_record_id,
            )
        self.status_changed.emit("Saved.")
        self.recording_saved.emit()

    def _on_transcription_error(self, err):
        self.progress_changed.emit(-2)
        QMessageBox.critical(self, "Error", err)

    def mark_start_from_playhead(self):
        self.selection_start_spin.setValue(self._current_playhead_seconds())

    def mark_end_from_playhead(self):
        self.selection_end_spin.setValue(self._current_playhead_seconds())

    def _current_playhead_seconds(self):
        return max(0.0, float(self.player.position()) / 1000.0)

    def play_audio(self):
        self.player.play()

    def pause_audio(self):
        self.player.pause()

    def stop_audio(self):
        self.player.stop()

    def position_changed(self, position):
        self.slider.setValue(position)
        self.waveform.set_playhead(float(position) / 1000.0)

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):
        self.player.setPosition(position)
        self.waveform.set_playhead(float(position) / 1000.0)

    def media_state_changed(self, state):
        if self.player.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop_audio()

    def _seek_to_time(self, seconds: float):
        self.set_position(int(seconds * 1000))

    def _update_time_label(self):
        if self.preview_audio is None:
            self.time_label.setText("00:00 / 00:00")
            return
        current = self.player.position() / 1000.0
        total = float(len(self.preview_audio) / self.current_sample_rate) if len(self.preview_audio) else 0.0
        self.time_label.setText(f"{self._fmt_seconds(current)} / {self._fmt_seconds(total)}")

    def _fmt_seconds(self, seconds: float) -> str:
        seconds = max(0.0, float(seconds))
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:05.2f}" if mins else f"{secs:05.2f}"

    def cleanup(self):
        self.playback.cleanup()
        self.transcription_runtime.cleanup()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
