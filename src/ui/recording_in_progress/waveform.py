"""Bounded, palette-aware RMS history for the active capture screen."""

from collections import deque
import math

from PyQt6.QtCore import QPointF, QTimer, pyqtSlot
from PyQt6.QtGui import QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class RealTimeWaveformVisualizer(QWidget):
    """Display four seconds of RMS levels at the recorder's maximum 20 Hz."""

    HISTORY_SIZE = 80
    DISPLAY_GAIN = 10.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.samples = deque([0.0] * self.HISTORY_SIZE, maxlen=self.HISTORY_SIZE)
        self._paused = False
        self._closed = False
        self.decay_timer = QTimer(self)
        self.decay_timer.setInterval(50)
        self.decay_timer.timeout.connect(self._decay)
        self.setAccessibleName("Recording amplitude history")
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @pyqtSlot(float)
    def add_amplitude(self, amplitude):
        if self._closed or self._paused:
            return
        level = min(1.0, max(0.0, amplitude * self.DISPLAY_GAIN)) if math.isfinite(amplitude) else 0.0
        self.samples.append(level)
        self.update()

    def set_paused(self, paused):
        if self._closed:
            return
        self._paused = paused
        if paused and any(self.samples):
            self.decay_timer.start()
        else:
            self.decay_timer.stop()

    def _decay(self):
        self.samples = deque(
            (value * 0.75 if value * 0.75 >= 0.001 else 0.0 for value in self.samples),
            maxlen=self.HISTORY_SIZE,
        )
        if not any(self.samples):
            self.decay_timer.stop()
        self.update()

    def waveform_path(self):
        """Build a symmetric envelope with bounded, horizontal cubic tangents."""
        rect = self.contentsRect().toRectF().adjusted(2, 2, -2, -2)
        path = QPainterPath()
        if rect.width() <= 0 or rect.height() <= 0:
            return path
        center = rect.center().y()
        step = rect.width() / (self.HISTORY_SIZE - 1)
        for side in (-1, 1):
            points = [QPointF(rect.left() + i * step, center + side * value * rect.height() / 2)
                      for i, value in enumerate(self.samples)]
            if side == 1:
                points.reverse()
                path.lineTo(points[0])
            else:
                path.moveTo(points[0])
            for previous, point in zip(points, points[1:]):
                middle = (previous.x() + point.x()) / 2
                path.cubicTo(QPointF(middle, previous.y()), QPointF(middle, point.y()), point)
        path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        painter.fillRect(self.rect(), palette.brush(QPalette.ColorRole.Window))
        painter.setPen(QPen(palette.color(QPalette.ColorRole.Mid), 1))
        painter.drawLine(QPointF(0, self.height() / 2), QPointF(self.width(), self.height() / 2))
        color = palette.color(QPalette.ColorRole.Highlight)
        painter.setPen(QPen(color, 1.5))
        color.setAlpha(90)
        painter.setBrush(color)
        painter.drawPath(self.waveform_path())

    def cleanup(self):
        self._closed = True
        self.decay_timer.stop()
        self.samples = deque([0.0] * self.HISTORY_SIZE, maxlen=self.HISTORY_SIZE)
        self.update()

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)
