"""Resizable Qt host used when a chat leaves the central tab area."""

from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal
from PyQt6.QtWidgets import QFrame, QSizePolicy


class FloatingChatHost(QFrame):
    """Bounded, resizeable container for a floating ``ChatWidget``."""

    size_changed = pyqtSignal()

    DEFAULT_WIDTH = 420
    DEFAULT_HEIGHT = 380
    MIN_WIDTH = 320
    MIN_HEIGHT = 260
    MAX_WIDTH = 760
    MAX_HEIGHT = 680
    MINIMIZED_WIDTH = 260
    MINIMIZED_HEIGHT = 32
    RESIZE_HANDLE_SIZE = 18
    RESIZE_MARGIN = 3
    EDGE_NONE = 0
    EDGE_LEFT = 1
    EDGE_RIGHT = 2
    EDGE_TOP = 4
    EDGE_BOTTOM = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._preferred_size = QSize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        self._min_size = QSize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self._max_size = QSize(self.MAX_WIDTH, self.MAX_HEIGHT)
        self._resize_enabled = True
        self._resizing = False
        self._resize_edges = self.EDGE_NONE
        self._drag_origin = QPoint()
        self._start_size = QSize(self._preferred_size)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self):
        return QSize(self._preferred_size)

    def minimumSizeHint(self):
        return QSize(self.minimumWidth(), self.minimumHeight())

    def set_preferred_size(self, size: QSize):
        bounded = QSize(
            max(self._min_size.width(), min(size.width(), self._max_size.width())),
            max(self._min_size.height(), min(size.height(), self._max_size.height())),
        )
        self._preferred_size = bounded
        self.setFixedSize(bounded)
        self.updateGeometry()
        self.size_changed.emit()

    def set_size_bounds(self, min_size: QSize, max_size: QSize):
        self._min_size = QSize(min_size)
        self._max_size = QSize(max_size)
        self.setMinimumSize(self._min_size)
        self.setMaximumSize(self._max_size)

    def set_resize_enabled(self, enabled: bool):
        self._resize_enabled = bool(enabled)
        if not self._resize_enabled:
            self._resizing = False
            self._resize_edges = self.EDGE_NONE
            self.unsetCursor()

    def _resize_edges_for_pos(self, pos):
        if not self._resize_enabled:
            return self.EDGE_NONE

        edges = self.EDGE_NONE
        if pos.x() <= self.RESIZE_MARGIN:
            edges |= self.EDGE_LEFT
        if pos.x() >= self.width() - self.RESIZE_MARGIN:
            edges |= self.EDGE_RIGHT
        if pos.y() <= self.RESIZE_MARGIN:
            edges |= self.EDGE_TOP
        if pos.y() >= self.height() - self.RESIZE_MARGIN:
            edges |= self.EDGE_BOTTOM
        return edges

    def _cursor_for_edges(self, edges):
        if edges in (self.EDGE_TOP | self.EDGE_LEFT, self.EDGE_BOTTOM | self.EDGE_RIGHT):
            return Qt.CursorShape.SizeFDiagCursor
        if edges in (self.EDGE_TOP | self.EDGE_RIGHT, self.EDGE_BOTTOM | self.EDGE_LEFT):
            return Qt.CursorShape.SizeBDiagCursor
        if edges & (self.EDGE_LEFT | self.EDGE_RIGHT) and not edges & (self.EDGE_TOP | self.EDGE_BOTTOM):
            return Qt.CursorShape.SizeHorCursor
        if edges & (self.EDGE_TOP | self.EDGE_BOTTOM) and not edges & (self.EDGE_LEFT | self.EDGE_RIGHT):
            return Qt.CursorShape.SizeVerCursor
        if edges:
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.ArrowCursor

    def _begin_resize(self, edges, global_pos):
        if not self._resize_enabled or not edges:
            return
        self._resizing = True
        self._resize_edges = edges
        self._drag_origin = QPoint(global_pos)
        self._start_size = QSize(self.size())

    def _apply_resize(self, global_pos):
        if not self._resizing or not self._resize_edges:
            return
        delta = QPoint(global_pos) - self._drag_origin
        new_width = self._start_size.width()
        new_height = self._start_size.height()
        if self._resize_edges & self.EDGE_LEFT:
            new_width -= delta.x()
        elif self._resize_edges & self.EDGE_RIGHT:
            new_width += delta.x()
        if self._resize_edges & self.EDGE_TOP:
            new_height -= delta.y()
        elif self._resize_edges & self.EDGE_BOTTOM:
            new_height += delta.y()
        self.set_preferred_size(QSize(new_width, new_height))

    def _end_resize(self):
        self._resizing = False
        self._resize_edges = self.EDGE_NONE
        self.unsetCursor()

    def mousePressEvent(self, event):
        edges = self._resize_edges_for_pos(event.position().toPoint())
        if self._resize_enabled and event.button() == Qt.MouseButton.LeftButton and edges:
            self._begin_resize(edges, event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_enabled and self._resizing:
            self._apply_resize(event.globalPosition().toPoint())
            event.accept()
            return
        if self._resize_enabled:
            edges = self._resize_edges_for_pos(event.position().toPoint())
            self.setCursor(self._cursor_for_edges(edges))
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_enabled and self._resizing:
            self._end_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        if not self._resizing:
            self.unsetCursor()
        super().leaveEvent(event)
