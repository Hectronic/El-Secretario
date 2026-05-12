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

import logging

from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTabBar,
    QToolButton,
    QSizePolicy,
    QVBoxLayout,
)

from src.ui.chat_widget import ChatWidget
from src.ui.welcome_widget import WelcomeWidget


class FloatingChatHost(QFrame):
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

    def resizeEvent(self, event):
        super().resizeEvent(event)


class FloatingChatCoordinator:
    def __init__(self, window):
        self.window = window

    def connect_chat_widget(self, chat_widget):
        chat_widget.session_updated.connect(self.window.load_chat_sessions)
        chat_widget.float_requested.connect(self.float_chat_widget)
        chat_widget.tab_requested.connect(self.dock_chat_widget_to_tab)
        chat_widget.minimize_requested.connect(self.minimize_floating_chat)
        chat_widget.restore_requested.connect(self.restore_floating_chat)
        chat_widget.close_requested.connect(self.close_chat_widget)
        chat_widget.title_changed.connect(self.sync_chat_widget_title)
        chat_widget.context_panel.context_changed.connect(
            lambda w=chat_widget: self.window._sync_chat_context_section(w)
        )

    def find_chat_tab_index(self, session_id):
        if session_id is None:
            return -1
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, ChatWidget) and widget.current_session_id == session_id:
                return i
        return -1

    def find_floating_chat_host(self, session_id):
        if session_id is None:
            return None
        for host in self.window.floating_chat_hosts:
            widget = host.property("chat_widget")
            if isinstance(widget, ChatWidget) and widget.current_session_id == session_id:
                return host
        return None

    def is_dark_theme(self):
        app = QApplication.instance()
        sheet = (app.styleSheet() if app else "").lower()
        if "#2b2b2b" in sheet and "#eeeeee" in sheet:
            return True
        if "#f5f5f5" in sheet and "#333333" in sheet:
            return False
        return self.window.palette().color(QPalette.ColorRole.Window).lightness() < 128

    def apply_floating_chat_host_style(self, host):
        if host is None:
            return
        is_dark = self.is_dark_theme()
        border_color = "rgba(100, 181, 246, 0.55)" if is_dark else "rgba(84, 110, 122, 0.45)"
        bg_color = "#232831" if is_dark else "#f5f7fb"
        host.setStyleSheet(f"""
            QFrame#floatingChatHost {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)

    def wrap_floating_chat(self, chat_widget):
        host = FloatingChatHost()
        host.setObjectName("floatingChatHost")
        host.setProperty("chat_widget", chat_widget)
        host.setProperty("chat_minimized", False)
        host.setProperty(
            "normal_size",
            QSize(FloatingChatHost.DEFAULT_WIDTH, FloatingChatHost.DEFAULT_HEIGHT),
        )
        self.apply_floating_chat_host_style(host)
        host.set_size_bounds(
            QSize(FloatingChatHost.MIN_WIDTH, FloatingChatHost.MIN_HEIGHT),
            QSize(FloatingChatHost.MAX_WIDTH, FloatingChatHost.MAX_HEIGHT),
        )
        host.size_changed.connect(lambda h=host: self.on_floating_chat_host_size_changed(h))
        host.set_preferred_size(QSize(FloatingChatHost.DEFAULT_WIDTH, FloatingChatHost.DEFAULT_HEIGHT))
        layout = QVBoxLayout(host)
        layout.setContentsMargins(
            FloatingChatHost.RESIZE_MARGIN,
            FloatingChatHost.RESIZE_MARGIN,
            FloatingChatHost.RESIZE_MARGIN,
            FloatingChatHost.RESIZE_MARGIN,
        )
        layout.setSpacing(0)
        layout.addWidget(chat_widget)
        self.set_floating_chat_minimized(host, False)
        return host

    def on_floating_chat_host_size_changed(self, host):
        if host is None or host.property("chat_minimized"):
            self.refresh_floating_chat_bar()
            return
        host.setProperty("normal_size", QSize(host.size()))
        self.refresh_floating_chat_bar()

    def set_floating_chat_minimized(self, host, minimized):
        if host is None:
            return
        chat_widget = host.property("chat_widget")
        if chat_widget is None:
            return
        minimized = bool(minimized)
        host.setProperty("chat_minimized", minimized)
        chat_widget.setVisible(True)
        chat_widget.set_floating_minimized(minimized)
        if minimized:
            if not host.property("normal_size"):
                host.setProperty("normal_size", QSize(host.size()))
            else:
                host.setProperty("normal_size", QSize(host.size()))
            host.set_size_bounds(
                QSize(FloatingChatHost.MINIMIZED_WIDTH, FloatingChatHost.MINIMIZED_HEIGHT),
                QSize(FloatingChatHost.MINIMIZED_WIDTH, FloatingChatHost.MINIMIZED_HEIGHT),
            )
            host.set_resize_enabled(False)
            host.set_preferred_size(
                QSize(FloatingChatHost.MINIMIZED_WIDTH, FloatingChatHost.MINIMIZED_HEIGHT)
            )
            return

        normal_size = host.property("normal_size")
        if not isinstance(normal_size, QSize):
            normal_size = QSize(FloatingChatHost.DEFAULT_WIDTH, FloatingChatHost.DEFAULT_HEIGHT)
        host.set_size_bounds(
            QSize(FloatingChatHost.MIN_WIDTH, FloatingChatHost.MIN_HEIGHT),
            QSize(FloatingChatHost.MAX_WIDTH, FloatingChatHost.MAX_HEIGHT),
        )
        host.set_resize_enabled(True)
        host.set_preferred_size(normal_size)

    def find_floating_chat_host_by_widget(self, chat_widget):
        return next((h for h in self.window.floating_chat_hosts if h.property("chat_widget") is chat_widget), None)

    def remove_floating_host(self, host):
        if host is None:
            return
        self.window.floating_chat_layout.removeWidget(host)
        if host in self.window.floating_chat_hosts:
            self.window.floating_chat_hosts.remove(host)
        host.deleteLater()
        self.refresh_floating_chat_bar()

    def refresh_floating_chat_bar(self):
        visible = bool(self.window.floating_chat_hosts)
        self.window.floating_chat_bar.setVisible(visible)
        if visible:
            for host in self.window.floating_chat_hosts:
                self.apply_floating_chat_host_style(host)
                self.window.floating_chat_layout.setAlignment(host, Qt.AlignmentFlag.AlignBottom)
            QTimer.singleShot(0, self.reposition_floating_chat_bar)
            self.window.floating_chat_bar.raise_()

    def reposition_floating_chat_bar(self):
        if not hasattr(self.window, "floating_chat_bar") or self.window.floating_chat_bar is None:
            return
        parent = self.window.centralWidget()
        if parent is None:
            return

        margin = 16
        spacing = self.window.floating_chat_layout.spacing()

        total_width = 0
        max_height = 0
        visible_hosts = 0
        for i in range(self.window.floating_chat_layout.count()):
            item = self.window.floating_chat_layout.itemAt(i)
            widget = item.widget()
            if widget and widget.isVisible():
                total_width += widget.width()
                max_height = max(max_height, widget.height())
                visible_hosts += 1

        if visible_hosts > 0:
            total_width += spacing * (visible_hosts - 1)

        available_width = max(260, parent.width() - (margin * 2))
        width = min(total_width, available_width)
        height = max_height

        width += self.window.floating_chat_layout.contentsMargins().left() + self.window.floating_chat_layout.contentsMargins().right()
        height += self.window.floating_chat_layout.contentsMargins().top() + self.window.floating_chat_layout.contentsMargins().bottom()

        self.window.floating_chat_bar.resize(width, height)

        status = self.window.statusBar()
        if status is not None and status.isVisible():
            status_top = parent.mapFrom(self.window, QPoint(0, status.geometry().top())).y()
            y = status_top - height
        else:
            y = parent.height() - height

        x = parent.width() - width - margin
        self.window.floating_chat_bar.move(x, max(0, y))

    def tab_title_for_chat(self, chat_widget):
        return chat_widget.get_chat_title()

    def set_tab_action_buttons(self, widget):
        if widget is None:
            return
        index = self.window.central_tabs.indexOf(widget)
        if index == -1:
            return

        tab_bar = self.window.central_tabs.tabBar()

        if isinstance(widget, WelcomeWidget):
            tab_bar.setTabButton(index, QTabBar.ButtonPosition.LeftSide, None)
            tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, None)
            return

        if not isinstance(widget, ChatWidget):
            return

        buttons = QFrame(tab_bar)
        layout = QHBoxLayout(buttons)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        float_btn = QToolButton(buttons)
        float_btn.setText("↗")
        float_btn.setToolTip("Move chat to floating window")
        float_btn.setAutoRaise(True)
        float_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        float_btn.setFixedSize(18, 18)
        float_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 0px;
                background: transparent;
                color: #6f8698;
                font-size: 11px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: rgba(33, 150, 243, 0.16);
                color: #2196F3;
            }
        """)
        float_btn.clicked.connect(lambda _checked=False, w=widget: self.float_chat_widget(w))
        layout.addWidget(float_btn)

        close_btn = QToolButton(buttons)
        close_btn.setText("×")
        close_btn.setToolTip("Close tab")
        close_btn.setAutoRaise(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet("""
            QToolButton {
                border: none;
                border-radius: 6px;
                padding: 0px;
                background: transparent;
                color: #6f8698;
                font-size: 12px;
                font-weight: 700;
            }
            QToolButton:hover {
                background-color: rgba(244, 67, 54, 0.15);
                color: #f44336;
            }
        """)
        close_btn.clicked.connect(
            lambda _checked=False, w=widget: self.window.close_tab(self.window.central_tabs.indexOf(w))
        )
        layout.addWidget(close_btn)

        tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, buttons)

    def sync_chat_widget_title(self, chat_widget, title):
        tab_index = self.window.central_tabs.indexOf(chat_widget)
        if tab_index != -1:
            self.window.central_tabs.setTabText(tab_index, title)
        host = self.find_floating_chat_host_by_widget(chat_widget)
        if host is not None:
            host.setToolTip(title)

    def float_chat_widget(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self.find_floating_chat_host_by_widget(chat_widget)
        if host is not None:
            self.set_floating_chat_minimized(host, False)
            return
        tab_index = self.window.central_tabs.indexOf(chat_widget)
        if tab_index != -1:
            self.window.central_tabs.removeTab(tab_index)
        chat_widget.setParent(None)
        chat_widget.set_display_mode("floating")
        host = self.wrap_floating_chat(chat_widget)
        self.window.floating_chat_hosts.append(host)
        self.window.floating_chat_layout.insertWidget(
            self.window.floating_chat_layout.count(),
            host,
            0,
            Qt.AlignmentFlag.AlignBottom,
        )
        self.sync_chat_widget_title(chat_widget, chat_widget.get_chat_title())
        self.refresh_floating_chat_bar()
        self.window._sync_chat_context_section()

    def minimize_floating_chat(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self.find_floating_chat_host_by_widget(chat_widget)
        if host is None:
            self.float_chat_widget(chat_widget)
            host = self.find_floating_chat_host_by_widget(chat_widget)
        self.set_floating_chat_minimized(host, True)
        self.refresh_floating_chat_bar()

    def restore_floating_chat(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self.find_floating_chat_host_by_widget(chat_widget)
        self.set_floating_chat_minimized(host, False)
        self.refresh_floating_chat_bar()

    def dock_chat_widget_to_tab(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self.find_floating_chat_host_by_widget(chat_widget)
        if host is None:
            tab_index = self.window.central_tabs.indexOf(chat_widget)
            if tab_index != -1:
                self.window.central_tabs.setCurrentIndex(tab_index)
            return
        self.window.floating_chat_layout.removeWidget(host)
        if host in self.window.floating_chat_hosts:
            self.window.floating_chat_hosts.remove(host)
        chat_widget.setParent(None)
        chat_widget.set_display_mode("tab")
        host.deleteLater()
        title = self.tab_title_for_chat(chat_widget)
        index = self.window.central_tabs.addTab(chat_widget, title)
        self.window.central_tabs.setCurrentIndex(index)
        self.set_tab_action_buttons(chat_widget)
        self.refresh_floating_chat_bar()
        self.window._sync_chat_context_section(chat_widget)

    def close_chat_widget(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        tab_index = self.window.central_tabs.indexOf(chat_widget)
        if tab_index != -1:
            self.window.close_tab(tab_index)
            return
        self.close_floating_chat(chat_widget)
        self.window._sync_chat_context_section()

    def close_floating_chat(self, chat_widget):
        if not isinstance(chat_widget, ChatWidget):
            return
        host = self.find_floating_chat_host_by_widget(chat_widget)
        if host is None:
            return
        if hasattr(chat_widget, "cleanup"):
            try:
                chat_widget.cleanup()
            except Exception:
                pass
        chat_widget.setParent(None)
        self.remove_floating_host(host)
        chat_widget.deleteLater()
