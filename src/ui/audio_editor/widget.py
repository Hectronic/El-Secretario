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
import shutil
import tempfile
from dataclasses import dataclass

import soundfile as sf
import numpy as np
from PyQt6.QtCore import Qt, QSettings, QUrl, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtWidgets import QStyle

from src.audio import Recorder
from src.database import DBManager
from src.transcription_options import get_saved_transcription_model
from src.ui.audio_editor.waveform import AudioWaveformWidget
from src.worker_components.transcriber_thread import TranscriberThread
from src.stt_providers.sherpa_onnx.model_manager import get_transcription_preflight_error


@dataclass
class AudioChunk:
    source_start: float
    source_end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)


class AudioEditorWidget(QWidget):
    recording_saved = pyqtSignal()
    recording_deleted = pyqtSignal(int)
    close_requested = pyqtSignal()
    status_changed = pyqtSignal(str)
    progress_changed = pyqtSignal(int)

    def __init__(self, rag_engine, recorder=None, record_id=None, task_queue=None, parent=None):
        super().__init__(parent)
        self.rag = rag_engine
        self.db = DBManager()
        self.recorder = recorder if recorder is not None else Recorder()
        self.summary_task_queue = task_queue
        self.current_record_id = record_id
        self.current_recording_path = None
        self.current_audio = None
        self.current_sample_rate = 16000
        self.current_duration = 0.0
        self.preview_audio = None
        self.preview_temp_path = None
        self.preview_ranges = []
        self.chunks: list[AudioChunk] = []
        self.active_chunk_index = -1
        self.selection_start = 0.0
        self.selection_end = 0.0
        self._suppress_signals = False
        self._has_unsaved_changes = False
        self._undo_stack = []
        self._redo_stack = []
        self._history_limit = 200
        self._boundary_drag_history_pending = False
        self.transcriber_thread = None
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.player.playbackStateChanged.connect(self.media_state_changed)
        self.audio_output.setVolume(0.7)
        self._init_ui()
        if self.current_record_id:
            self.load_record(self.current_record_id)
        else:
            self.status_changed.emit("Ready.")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.setStyleSheet("QLabel#editorMeta { font-size: 12px; }")

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.title_label = QLabel("Audio Editor")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        header.addWidget(self.title_label)
        self.file_info_label = QLabel("No audio loaded")
        self.file_info_label.setObjectName("editorMeta")
        header.addWidget(self.file_info_label)
        header.addStretch()
        self.hint_label = QLabel("Drag segment edges on the waveform to retime cuts")
        self.hint_label.setObjectName("editorMeta")
        header.addWidget(self.hint_label)
        layout.addLayout(header)

        playback_frame = QFrame()
        playback_frame.setFrameShape(QFrame.Shape.StyledPanel)
        playback = QHBoxLayout(playback_frame)
        playback.setContentsMargins(8, 6, 8, 6)
        playback.setSpacing(8)
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.clicked.connect(self.play_audio)
        self.play_btn.setEnabled(False)
        self.play_btn.setToolTip("Play")
        playback.addWidget(self.play_btn)

        self.pause_btn = QPushButton()
        self.pause_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.pause_btn.clicked.connect(self.pause_audio)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setToolTip("Pause")
        playback.addWidget(self.pause_btn)

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.clicked.connect(self.stop_audio)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setToolTip("Stop")
        playback.addWidget(self.stop_btn)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self.set_position)
        playback.addWidget(self.slider)

        self.time_label = QLabel("00:00 / 00:00")
        playback.addWidget(self.time_label)

        vol_lbl = QLabel("Vol")
        vol_lbl.setObjectName("editorMeta")
        playback.addWidget(vol_lbl)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.audio_output.setVolume)
        playback.addWidget(self.volume_slider)
        layout.addWidget(playback_frame)

        self.waveform = AudioWaveformWidget()
        self.waveform.selection_changed.connect(self._on_waveform_selection_changed)
        self.waveform.chunk_clicked.connect(self._on_waveform_chunk_clicked)
        self.waveform.seek_requested.connect(self._seek_to_time)
        self.waveform.boundary_dragged.connect(self._on_waveform_boundary_dragged)
        self.waveform.boundary_drag_started.connect(self._on_boundary_drag_started)
        self.waveform.boundary_drag_finished.connect(self._on_boundary_drag_finished)
        self.waveform.setMinimumHeight(320)
        layout.addWidget(self.waveform, 1)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(8)

        selection_group = QGroupBox("Selection")
        selection_layout = QVBoxLayout(selection_group)
        row = QHBoxLayout()
        self.selection_start_spin = QDoubleSpinBox()
        self.selection_start_spin.setDecimals(3)
        self.selection_start_spin.setSingleStep(0.1)
        self.selection_start_spin.setMinimum(0.0)
        self.selection_start_spin.valueChanged.connect(self._on_spin_selection_changed)
        row.addWidget(QLabel("Start:"))
        row.addWidget(self.selection_start_spin)
        self.selection_end_spin = QDoubleSpinBox()
        self.selection_end_spin.setDecimals(3)
        self.selection_end_spin.setSingleStep(0.1)
        self.selection_end_spin.setMinimum(0.0)
        self.selection_end_spin.valueChanged.connect(self._on_spin_selection_changed)
        row.addWidget(QLabel("End:"))
        row.addWidget(self.selection_end_spin)
        selection_layout.addLayout(row)

        selection_btns = QHBoxLayout()
        self.mark_start_btn = QPushButton("Mark Start")
        self.mark_start_btn.clicked.connect(self.mark_start_from_playhead)
        selection_btns.addWidget(self.mark_start_btn)
        self.mark_end_btn = QPushButton("Mark End")
        self.mark_end_btn.clicked.connect(self.mark_end_from_playhead)
        selection_btns.addWidget(self.mark_end_btn)
        self.split_btn = QPushButton("Split")
        self.split_btn.clicked.connect(self.split_selection)
        selection_btns.addWidget(self.split_btn)
        self.cut_btn = QPushButton("Cut")
        self.cut_btn.clicked.connect(self.cut_selection)
        selection_btns.addWidget(self.cut_btn)
        selection_layout.addLayout(selection_btns)
        chunk_group = QGroupBox("Chunks")
        chunk_layout = QVBoxLayout(chunk_group)
        chunk_layout.setContentsMargins(8, 8, 8, 8)
        self.chunk_list = QListWidget()
        self.chunk_list.setMaximumHeight(160)
        self.chunk_list.currentRowChanged.connect(self._on_chunk_row_changed)
        chunk_layout.addWidget(self.chunk_list)
        chunk_btns = QHBoxLayout()
        self.up_btn = QPushButton("Up")
        self.up_btn.clicked.connect(lambda: self.move_chunk(-1))
        chunk_btns.addWidget(self.up_btn)
        self.down_btn = QPushButton("Down")
        self.down_btn.clicked.connect(lambda: self.move_chunk(1))
        chunk_btns.addWidget(self.down_btn)
        self.delete_chunk_btn = QPushButton("Delete")
        self.delete_chunk_btn.clicked.connect(self.delete_chunk)
        chunk_btns.addWidget(self.delete_chunk_btn)
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_edits)
        chunk_btns.addWidget(self.reset_btn)
        chunk_layout.addLayout(chunk_btns)

        tools_row = QHBoxLayout()
        tools_row.setSpacing(8)
        tools_row.addWidget(selection_group, 2)
        tools_row.addWidget(chunk_group, 3)
        side_layout.addLayout(tools_row)

        action_row = QHBoxLayout()
        self.apply_btn = QPushButton("Apply Edits")
        self.apply_btn.setProperty("class", "calendar-primary-btn")
        self.apply_btn.setMinimumHeight(34)
        self.apply_btn.clicked.connect(self.apply_edits)
        action_row.addWidget(self.apply_btn)
        action_row.addStretch()
        side_layout.addLayout(action_row)

        layout.addWidget(side, 0)

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo)
        self.redo_alt_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        self.redo_alt_shortcut.activated.connect(self.redo)

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
        self.current_audio = audio
        self.current_sample_rate = int(sample_rate)
        self.current_duration = float(audio.shape[0] / sample_rate) if len(audio) else 0.0
        self.chunks = [AudioChunk(0.0, self.current_duration)] if self.current_duration > 0 else []
        self.active_chunk_index = 0 if self.chunks else -1
        self._rebuild_preview()

    def _rebuild_preview(self):
        if not self.chunks or self.current_audio is None:
            self.preview_audio = None
            self.preview_ranges = []
            self.waveform.set_audio(None, self.current_sample_rate)
            self.waveform.set_chunk_ranges([], -1)
            self._refresh_chunk_list()
            self._update_time_label()
            return

        parts = []
        preview_ranges = []
        cursor = 0.0
        for idx, chunk in enumerate(self.chunks):
            start_frame = int(round(chunk.source_start * self.current_sample_rate))
            end_frame = int(round(chunk.source_end * self.current_sample_rate))
            start_frame = max(0, min(start_frame, len(self.current_audio)))
            end_frame = max(start_frame, min(end_frame, len(self.current_audio)))
            part = self.current_audio[start_frame:end_frame]
            if len(part):
                parts.append(part)
            output_start = cursor
            cursor += chunk.duration
            preview_ranges.append(
                {
                    "output_start": output_start,
                    "output_end": cursor,
                    "source_start": chunk.source_start,
                    "source_end": chunk.source_end,
                    "chunk_index": idx,
                }
            )

        if parts:
            self.preview_audio = np.concatenate(parts, axis=0)
        else:
            self.preview_audio = np.zeros((0, self.current_audio.shape[1]), dtype=np.float32)
        self.preview_ranges = preview_ranges
        self.waveform.set_audio(self.preview_audio, self.current_sample_rate)
        self.waveform.set_chunk_ranges(self.preview_ranges, self.active_chunk_index)
        self._refresh_chunk_list()
        self._update_active_selection_from_chunk()
        self._update_time_label()
        self._refresh_preview_player()

    def _refresh_preview_player(self):
        if self.preview_temp_path and os.path.exists(self.preview_temp_path):
            try:
                os.remove(self.preview_temp_path)
            except Exception:
                pass
        self.preview_temp_path = None
        if self.preview_audio is None:
            self.player.setSource(QUrl())
            return
        fd, path = tempfile.mkstemp(prefix="secretario_audio_preview_", suffix=".wav")
        os.close(fd)
        sf.write(path, self.preview_audio, self.current_sample_rate)
        self.preview_temp_path = path
        self.player.setSource(QUrl.fromLocalFile(path))

    def _refresh_chunk_list(self):
        self._suppress_signals = True
        self.chunk_list.clear()
        for idx, chunk in enumerate(self.preview_ranges):
            item = QListWidgetItem(
                f"{idx + 1}. {self._fmt_seconds(chunk['output_start'])} - {self._fmt_seconds(chunk['output_end'])}"
            )
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.chunk_list.addItem(item)
        if 0 <= self.active_chunk_index < self.chunk_list.count():
            self.chunk_list.setCurrentRow(self.active_chunk_index)
        self._suppress_signals = False

    def _update_active_selection_from_chunk(self):
        if not (0 <= self.active_chunk_index < len(self.preview_ranges)):
            self.selection_start_spin.setValue(0.0)
            self.selection_end_spin.setValue(0.0)
            self.waveform.set_selection(0.0, 0.0)
            return
        active = self.preview_ranges[self.active_chunk_index]
        self.selection_start_spin.blockSignals(True)
        self.selection_end_spin.blockSignals(True)
        self.selection_start_spin.setRange(active["output_start"], active["output_end"])
        self.selection_end_spin.setRange(active["output_start"], active["output_end"])
        self.selection_start_spin.setValue(active["output_start"])
        self.selection_end_spin.setValue(active["output_end"])
        self.selection_start_spin.blockSignals(False)
        self.selection_end_spin.blockSignals(False)
        self.waveform.set_selection(active["output_start"], active["output_end"])

    def _on_waveform_selection_changed(self, start: float, end: float):
        if self._suppress_signals:
            return
        self.selection_start = start
        self.selection_end = end
        self.selection_start_spin.blockSignals(True)
        self.selection_end_spin.blockSignals(True)
        self.selection_start_spin.setValue(start)
        self.selection_end_spin.setValue(end)
        self.selection_start_spin.blockSignals(False)
        self.selection_end_spin.blockSignals(False)
        self._mark_dirty()

    def _on_spin_selection_changed(self, *_args):
        if self._suppress_signals:
            return
        start = self.selection_start_spin.value()
        end = self.selection_end_spin.value()
        if end < start:
            start, end = end, start
        self.selection_start = start
        self.selection_end = end
        self.waveform.set_selection(start, end)
        self._mark_dirty()

    def _on_chunk_row_changed(self, row: int):
        if self._suppress_signals:
            return
        if row < 0:
            return
        self.active_chunk_index = row
        self.waveform.set_chunk_ranges(self.preview_ranges, self.active_chunk_index)
        self._update_active_selection_from_chunk()

    def _on_waveform_chunk_clicked(self, index: int):
        if not (0 <= index < len(self.preview_ranges)):
            return
        if self.chunk_list.currentRow() != index:
            self.chunk_list.setCurrentRow(index)
        else:
            self._on_chunk_row_changed(index)

    def _on_waveform_boundary_dragged(self, side: str, boundary_time: float):
        if self._suppress_signals:
            return
        if not (0 <= self.active_chunk_index < len(self.chunks)):
            return
        self.adjust_active_chunk_boundary(side, boundary_time)

    def _on_boundary_drag_started(self):
        self._boundary_drag_history_pending = True

    def _on_boundary_drag_finished(self):
        self._boundary_drag_history_pending = False

    def _chunk_for_selection(self):
        if not (0 <= self.active_chunk_index < len(self.preview_ranges)):
            return None, None
        active = self.preview_ranges[self.active_chunk_index]
        if self.selection_end <= self.selection_start:
            return None, "Select a range first."
        if self.selection_start < active["output_start"] or self.selection_end > active["output_end"]:
            return None, "The selection must stay inside the active chunk."
        return active, None

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

        self._push_undo_state()
        chunk = self.chunks[self.active_chunk_index]
        left, middle, right = self._split_chunk(chunk, active, keep_middle=True)
        new_chunks = []
        if left:
            new_chunks.append(left)
        if middle:
            new_chunks.append(middle)
        if right:
            new_chunks.append(right)
        self.chunks[self.active_chunk_index:self.active_chunk_index + 1] = new_chunks
        self.active_chunk_index = min(self.active_chunk_index + (1 if left else 0), len(self.chunks) - 1)
        self._rebuild_preview()
        self._mark_dirty()

    def cut_selection(self):
        try:
            active = self._selection_to_chunk()
        except ValueError as exc:
            QMessageBox.warning(self, "Cut", str(exc))
            return

        self._push_undo_state()
        chunk = self.chunks[self.active_chunk_index]
        left, _, right = self._split_chunk(chunk, active, keep_middle=False)
        new_chunks = []
        if left:
            new_chunks.append(left)
        if right:
            new_chunks.append(right)
        self.chunks[self.active_chunk_index:self.active_chunk_index + 1] = new_chunks
        self.active_chunk_index = min(self.active_chunk_index, max(0, len(self.chunks) - 1))
        self._rebuild_preview()
        self._mark_dirty()

    def delete_chunk(self):
        if not (0 <= self.active_chunk_index < len(self.chunks)):
            return
        if len(self.chunks) == 1:
            QMessageBox.warning(self, "Delete Chunk", "You need at least one chunk.")
            return
        self._push_undo_state()
        del self.chunks[self.active_chunk_index]
        self.active_chunk_index = min(self.active_chunk_index, len(self.chunks) - 1)
        self._rebuild_preview()
        self._mark_dirty()

    def move_chunk(self, offset: int):
        if not (0 <= self.active_chunk_index < len(self.chunks)):
            return
        target = self.active_chunk_index + offset
        if target < 0 or target >= len(self.chunks):
            return
        self._push_undo_state()
        self.chunks[self.active_chunk_index], self.chunks[target] = self.chunks[target], self.chunks[self.active_chunk_index]
        self.active_chunk_index = target
        self._rebuild_preview()
        self._mark_dirty()

    def adjust_active_chunk_boundary(self, side: str, boundary_time: float):
        if not (0 <= self.active_chunk_index < len(self.chunks)):
            return False
        if not self.preview_ranges:
            return False
        if self._boundary_drag_history_pending:
            self._push_undo_state()
            self._boundary_drag_history_pending = False

        active_range = self.preview_ranges[self.active_chunk_index]
        boundary_time = float(boundary_time)
        if side == "left":
            min_time = active_range["output_start"]
            max_time = active_range["output_end"] - 0.001
            if self.active_chunk_index > 0:
                prev_range = self.preview_ranges[self.active_chunk_index - 1]
                min_time = prev_range["output_start"] + 0.001
                max_time = active_range["output_end"] - 0.001
                if boundary_time < min_time:
                    boundary_time = min_time
                if boundary_time > max_time:
                    boundary_time = max_time
                prev_chunk = self.chunks[self.active_chunk_index - 1]
                current_chunk = self.chunks[self.active_chunk_index]
                total = prev_chunk.duration + current_chunk.duration
                left_duration = max(0.001, boundary_time - prev_range["output_start"])
                right_duration = max(0.001, total - left_duration)
                prev_chunk.source_end = prev_chunk.source_start + left_duration
                current_chunk.source_start = current_chunk.source_end - right_duration
            else:
                current_chunk = self.chunks[self.active_chunk_index]
                max_start = current_chunk.source_end - 0.001
                new_start = max(0.0, min(boundary_time, max_start))
                current_chunk.source_start = new_start
        elif side == "right":
            min_time = active_range["output_start"] + 0.001
            max_time = active_range["output_end"]
            if self.active_chunk_index < len(self.chunks) - 1:
                next_range = self.preview_ranges[self.active_chunk_index + 1]
                min_time = active_range["output_start"] + 0.001
                max_time = next_range["output_end"] - 0.001
                if boundary_time < min_time:
                    boundary_time = min_time
                if boundary_time > max_time:
                    boundary_time = max_time
                current_chunk = self.chunks[self.active_chunk_index]
                next_chunk = self.chunks[self.active_chunk_index + 1]
                total = current_chunk.duration + next_chunk.duration
                left_duration = max(0.001, boundary_time - active_range["output_start"])
                right_duration = max(0.001, total - left_duration)
                current_chunk.source_end = current_chunk.source_start + left_duration
                next_chunk.source_start = next_chunk.source_end - right_duration
            else:
                current_chunk = self.chunks[self.active_chunk_index]
                min_end = current_chunk.source_start + 0.001
                new_end = max(min_end, min(boundary_time, self.current_duration))
                current_chunk.source_end = new_end
        else:
            return False

        self._rebuild_preview()
        self._mark_dirty()
        return True

    def reset_edits(self):
        if self.current_duration <= 0:
            return
        self._push_undo_state()
        self.chunks = [AudioChunk(0.0, self.current_duration)]
        self.active_chunk_index = 0
        self._rebuild_preview()
        self._mark_dirty()

    def _split_chunk(self, chunk: AudioChunk, active_range: dict, keep_middle: bool):
        # Split the currently selected chunk by mapping the output selection back to source coordinates.
        chunk_duration = chunk.duration
        output_start = active_range["output_start"]
        sel_start = max(output_start, self.selection_start)
        sel_end = min(active_range["output_end"], self.selection_end)
        if sel_end <= sel_start:
            raise ValueError("The selection must have a positive duration.")

        left_duration = sel_start - output_start
        middle_duration = sel_end - sel_start
        right_duration = active_range["output_end"] - sel_end

        left = AudioChunk(chunk.source_start, chunk.source_start + left_duration) if left_duration > 0.001 else None
        middle = AudioChunk(chunk.source_start + left_duration, chunk.source_start + left_duration + middle_duration) if middle_duration > 0.001 else None
        right = AudioChunk(chunk.source_end - right_duration, chunk.source_end) if right_duration > 0.001 else None

        if keep_middle:
            return left, middle, right
        return left, None, right

    def _mark_dirty(self):
        self._has_unsaved_changes = True

    def _mark_clean(self):
        self._has_unsaved_changes = False

    def has_unsaved_changes(self):
        return self._has_unsaved_changes

    def _chunk_snapshot(self):
        return ([(c.source_start, c.source_end) for c in self.chunks], int(self.active_chunk_index))

    def _restore_snapshot(self, snapshot):
        chunk_pairs, active_idx = snapshot
        self.chunks = [AudioChunk(float(start), float(end)) for start, end in chunk_pairs]
        self.active_chunk_index = max(-1, min(int(active_idx), len(self.chunks) - 1))
        self._rebuild_preview()

    def _clear_history(self):
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._boundary_drag_history_pending = False

    def _push_undo_state(self):
        snapshot = self._chunk_snapshot()
        if self._undo_stack and self._undo_stack[-1] == snapshot:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return False
        current = self._chunk_snapshot()
        previous = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore_snapshot(previous)
        self._mark_dirty()
        self.status_changed.emit("Undo")
        return True

    def redo(self):
        if not self._redo_stack:
            return False
        current = self._chunk_snapshot()
        next_snapshot = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._restore_snapshot(next_snapshot)
        self._mark_dirty()
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
            backup_path = f"{self.current_recording_path}.orig"
            if not os.path.exists(backup_path):
                shutil.copy2(self.current_recording_path, backup_path)
            sf.write(self.current_recording_path, self.preview_audio, self.current_sample_rate)
            self.current_audio = self.preview_audio
            self.current_duration = float(len(self.preview_audio) / self.current_sample_rate)
            self.db.update_duration(self.current_record_id, self.current_duration)
            self.status_changed.emit("Audio updated.")
            self.recording_saved.emit()
            self._mark_clean()
            self._clear_history()
            self.chunks = [AudioChunk(0.0, self.current_duration)]
            self.active_chunk_index = 0
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
        settings = QSettings("Hectronic", "Secretario")
        model_size = get_saved_transcription_model(settings)
        language = settings.value("rec_config/language", "Auto")
        lang_map = {"Auto": None, "Spanish": "es", "English": "en"}
        language_code = lang_map.get(language, None)
        hf_token = settings.value("hf_token", "")
        force_cpu = settings.value("force_cpu", False, type=bool)
        compute_type = settings.value("compute_type", "auto")
        transcription_backend = settings.value("transcription_backend", "auto")
        enable_diarization = settings.value("rec_config/diarization", False, type=bool)
        preflight_error = get_transcription_preflight_error(model_size, settings)
        if preflight_error:
            QMessageBox.critical(self, "Transcription Error", preflight_error)
            return
        if compute_type == "auto":
            compute_type = None
        duration = self.current_duration
        self.transcriber_thread = TranscriberThread(
            self.current_recording_path,
            model_size=model_size,
            compute_type=compute_type,
            language=language_code,
            hf_token=hf_token,
            enable_diarization=enable_diarization,
            total_duration=duration,
            force_cpu=force_cpu,
            backend_preference=transcription_backend,
        )
        self.transcriber_thread.finished.connect(self._on_transcription_finished)
        self.transcriber_thread.error.connect(self._on_transcription_error)
        self.transcriber_thread.finished.connect(self._clear_transcriber_thread_ref)
        self.transcriber_thread.error.connect(self._clear_transcriber_thread_ref)
        self.transcriber_thread.start()
        self.progress_changed.emit(0)

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

    def _clear_transcriber_thread_ref(self, *args):
        thread = self.transcriber_thread
        self.transcriber_thread = None
        if thread:
            thread.deleteLater()

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
        self.stop_audio()
        self.player.setSource(QUrl())
        if self.preview_temp_path and os.path.exists(self.preview_temp_path):
            try:
                os.remove(self.preview_temp_path)
            except Exception:
                pass
            self.preview_temp_path = None
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

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
