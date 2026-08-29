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

import numpy as np
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QWidget


class AudioWaveformWidget(QWidget):
    """Interactive waveform view used by audio editing tools."""

    selection_changed = pyqtSignal(float, float)
    chunk_clicked = pyqtSignal(int)
    seek_requested = pyqtSignal(float)
    boundary_dragged = pyqtSignal(str, float)
    boundary_drag_started = pyqtSignal()
    boundary_drag_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setMouseTracking(True)
        self._audio = None
        self._sample_rate = 16000
        self._duration = 0.0
        self._selection = (0.0, 0.0)
        self._playhead = 0.0
        self._preview_ranges = []
        self._active_chunk_index = -1
        self._dragging = False
        self._drag_origin = 0.0
        self._drag_mode = None
        self._drag_side = None
        self._handle_hit_px = 8.0

    def set_audio(self, audio: np.ndarray | None, sample_rate: int):
        self._audio = audio
        self._sample_rate = int(sample_rate or 16000)
        self._duration = float(audio.shape[0] / self._sample_rate) if audio is not None and len(audio) else 0.0
        self.update()

    def set_chunk_ranges(self, preview_ranges: list[dict], active_index: int):
        self._preview_ranges = list(preview_ranges or [])
        self._active_chunk_index = int(active_index) if active_index is not None else -1
        self.update()

    def set_selection(self, start: float, end: float):
        start = max(0.0, float(start))
        end = max(0.0, float(end))
        if end < start:
            start, end = end, start
        self._selection = (start, end)
        self.update()

    def set_playhead(self, seconds: float):
        self._playhead = max(0.0, float(seconds))
        self.update()

    def _time_to_x(self, seconds: float) -> float:
        if self._duration <= 0:
            return 0.0
        margin = 12.0
        width = max(1.0, float(self.width()) - (margin * 2.0))
        return margin + (max(0.0, min(seconds, self._duration)) / self._duration) * width

    def _x_to_time(self, x: float) -> float:
        if self._duration <= 0:
            return 0.0
        margin = 12.0
        width = max(1.0, float(self.width()) - (margin * 2.0))
        relative = max(0.0, min(x - margin, width))
        return (relative / width) * self._duration

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            active = self._active_range()
            x = event.position().x()
            if active:
                left_x = self._time_to_x(active["output_start"])
                right_x = self._time_to_x(active["output_end"])
                if abs(x - left_x) <= self._handle_hit_px:
                    self._dragging = True
                    self._drag_mode = "boundary"
                    self._drag_side = "left"
                    self.boundary_drag_started.emit()
                    self.boundary_dragged.emit(self._drag_side, self._x_to_time(x))
                    return
                if abs(x - right_x) <= self._handle_hit_px:
                    self._dragging = True
                    self._drag_mode = "boundary"
                    self._drag_side = "right"
                    self.boundary_drag_started.emit()
                    self.boundary_dragged.emit(self._drag_side, self._x_to_time(x))
                    return
            chunk_index = self._chunk_index_at_time(self._x_to_time(x))
            if chunk_index is not None:
                self.chunk_clicked.emit(chunk_index)
            self._dragging = True
            self._drag_mode = "selection"
            self._drag_origin = self._x_to_time(event.position().x())
            self.set_selection(self._drag_origin, self._drag_origin)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_mode == "selection":
            current = self._x_to_time(event.position().x())
            start = min(self._drag_origin, current)
            end = max(self._drag_origin, current)
            self._selection = (start, end)
            self.selection_changed.emit(start, end)
            self.update()
        elif self._dragging and self._drag_mode == "boundary" and self._drag_side:
            self.boundary_dragged.emit(self._drag_side, self._x_to_time(event.position().x()))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        drag_mode = self._drag_mode
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            current = self._x_to_time(event.position().x())
            start = min(self._drag_origin, current)
            end = max(self._drag_origin, current)
            if drag_mode != "boundary":
                self._selection = (start, end)
                self.selection_changed.emit(start, end)
                self.update()
            else:
                self.boundary_drag_finished.emit()
            self._drag_mode = None
            self._drag_side = None
        elif event.button() == Qt.MouseButton.RightButton:
            self.seek_requested.emit(self._x_to_time(event.position().x()))
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.seek_requested.emit(self._x_to_time(event.position().x()))
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        palette = self.palette()
        bg = palette.color(QPalette.ColorRole.Base)
        border = palette.color(QPalette.ColorRole.Mid)
        text_color = palette.color(QPalette.ColorRole.Text)
        lane_color = palette.color(QPalette.ColorRole.Midlight)
        painter.fillRect(self.rect(), bg)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(rect, 10, 10)

        if self._duration <= 0 or self._audio is None or not len(self._audio):
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Load an audio file to see the waveform")
            return

        channel_count = 1 if self._audio.ndim == 1 else self._audio.shape[1]
        lane_height = max(20.0, rect.height() / max(1, channel_count))
        palette = [
            QColor("#63b3ed"),
            QColor("#f6ad55"),
            QColor("#68d391"),
            QColor("#f687b3"),
        ]

        for idx, chunk in enumerate(self._preview_ranges):
            start_x = self._time_to_x(chunk["output_start"])
            end_x = self._time_to_x(chunk["output_end"])
            if idx == self._active_chunk_index:
                painter.fillRect(
                    QRectF(start_x, rect.top(), max(1.0, end_x - start_x), rect.height()),
                    QColor(100, 181, 246, 38),
                )
            painter.setPen(QPen(border, 1))
            painter.drawLine(int(start_x), rect.top(), int(start_x), rect.bottom())
            painter.drawLine(int(end_x), rect.top(), int(end_x), rect.bottom())

        sel_start, sel_end = self._selection
        if sel_end > sel_start:
            painter.fillRect(
                QRectF(self._time_to_x(sel_start), rect.top(), max(1.0, self._time_to_x(sel_end) - self._time_to_x(sel_start)), rect.height()),
                QColor(255, 255, 255, 24),
            )

        active = self._active_range()
        if active:
            self._draw_handle(painter, self._time_to_x(active["output_start"]), rect, QColor("#90cdf4"))
            self._draw_handle(painter, self._time_to_x(active["output_end"]), rect, QColor("#90cdf4"))

        # Draw channel lanes.
        for ch in range(channel_count):
            if self._audio.ndim == 1:
                channel = self._audio
            else:
                channel = self._audio[:, ch]
            lane_top = rect.top() + (ch * lane_height)
            lane_rect = QRectF(rect.left(), lane_top, rect.width(), lane_height)
            painter.setPen(QPen(lane_color, 1))
            painter.drawLine(int(lane_rect.left()), int(lane_rect.center().y()), int(lane_rect.right()), int(lane_rect.center().y()))

            if len(channel) == 0:
                continue

            width = max(1, int(rect.width()))
            samples_per_pixel = max(1, int(np.ceil(len(channel) / width)))
            center_y = lane_rect.center().y()
            amplitude = max(8.0, lane_rect.height() * 0.42)
            pen = QPen(palette[ch % len(palette)], 1)
            painter.setPen(pen)

            for x in range(width):
                start = x * samples_per_pixel
                if start >= len(channel):
                    break
                end = min(len(channel), start + samples_per_pixel)
                segment = channel[start:end]
                low = float(segment.min())
                high = float(segment.max())
                y1 = center_y - (high * amplitude)
                y2 = center_y - (low * amplitude)
                painter.drawLine(int(rect.left()) + x, int(y1), int(rect.left()) + x, int(y2))

        play_x = self._time_to_x(self._playhead)
        painter.setPen(QPen(QColor("#ff6b6b"), 2))
        painter.drawLine(int(play_x), rect.top(), int(play_x), rect.bottom())

    def _active_range(self):
        if 0 <= self._active_chunk_index < len(self._preview_ranges):
            return self._preview_ranges[self._active_chunk_index]
        return None

    def _chunk_index_at_time(self, seconds: float) -> int | None:
        for idx, chunk in enumerate(self._preview_ranges):
            if chunk["output_start"] <= seconds <= chunk["output_end"]:
                return idx
        return None

    def _draw_handle(self, painter, x, rect, color):
        painter.setPen(QPen(color, 1))
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(x - 4, rect.top() + 6, 8, rect.height() - 12), 2, 2)
