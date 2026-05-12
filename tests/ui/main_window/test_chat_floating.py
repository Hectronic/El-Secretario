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
import sys
import unittest

from PyQt6.QtCore import QPoint, QSize, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QMainWindow, QTabWidget, QWidget

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.ui.main_window import chat_floating as floating_module
from src.ui.main_window.chat_floating import FloatingChatCoordinator


class _Signal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _ContextPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.context_changed = _Signal()


class _ChatWidget(QWidget):
    def __init__(self, session_id=7, title="Chat Title"):
        super().__init__()
        self.current_session_id = session_id
        self._title = title
        self.display_mode = "tab"
        self.floating_minimized = False
        self.cleanup_called = False
        self.session_updated = _Signal()
        self.float_requested = _Signal()
        self.tab_requested = _Signal()
        self.minimize_requested = _Signal()
        self.restore_requested = _Signal()
        self.close_requested = _Signal()
        self.title_changed = _Signal()
        self.context_panel = _ContextPanel()

    def set_display_mode(self, mode):
        self.display_mode = mode
        self.context_panel.setVisible(mode == "tab")

    def set_floating_minimized(self, minimized):
        self.floating_minimized = bool(minimized)

    def get_chat_title(self):
        return self._title

    def cleanup(self):
        self.cleanup_called = True


class _Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.central = QWidget()
        self.central.setFixedSize(800, 600)
        self.setCentralWidget(self.central)
        self.central_tabs = QTabWidget(self.central)
        self.central_tabs.setGeometry(0, 0, 400, 300)
        self.floating_chat_bar = QFrame(self.central)
        self.floating_chat_bar.setVisible(False)
        self.floating_chat_layout = QHBoxLayout(self.floating_chat_bar)
        self.floating_chat_layout.setContentsMargins(0, 0, 0, 0)
        self.floating_chat_layout.setSpacing(12)
        self.floating_chat_hosts = []
        self.sync_calls = []
        self.load_chat_sessions_calls = 0

    def load_chat_sessions(self):
        self.load_chat_sessions_calls += 1

    def _sync_chat_context_section(self, chat_widget=None):
        self.sync_calls.append(chat_widget)

    def close_tab(self, index):
        self.central_tabs.removeTab(index)


class TestFloatingChatCoordinator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.window = _Window()
        self.coordinator = FloatingChatCoordinator(self.window)
        self._chat_patch = unittest.mock.patch.object(floating_module, "ChatWidget", _ChatWidget)
        self._welcome_patch = unittest.mock.patch.object(floating_module, "WelcomeWidget", QWidget)
        self.mock_chat_cls = self._chat_patch.start()
        self._welcome_patch.start()

    def tearDown(self):
        self._welcome_patch.stop()
        self._chat_patch.stop()
        self.window.close()

    def test_connect_chat_widget_wires_signals(self):
        chat = _ChatWidget()
        float_calls = []
        dock_calls = []
        minimize_calls = []
        restore_calls = []
        close_calls = []

        self.coordinator.float_chat_widget = lambda widget: float_calls.append(widget)
        self.coordinator.dock_chat_widget_to_tab = lambda widget: dock_calls.append(widget)
        self.coordinator.minimize_floating_chat = lambda widget: minimize_calls.append(widget)
        self.coordinator.restore_floating_chat = lambda widget: restore_calls.append(widget)
        self.coordinator.close_chat_widget = lambda widget: close_calls.append(widget)

        self.coordinator.connect_chat_widget(chat)
        chat.session_updated.emit()
        chat.float_requested.emit(chat)
        chat.tab_requested.emit(chat)
        chat.minimize_requested.emit(chat)
        chat.restore_requested.emit(chat)
        chat.close_requested.emit(chat)
        chat.title_changed.emit(chat, "Renamed")
        chat.context_panel.context_changed.emit()

        self.assertEqual(self.window.load_chat_sessions_calls, 1)
        self.assertEqual(float_calls, [chat])
        self.assertEqual(dock_calls, [chat])
        self.assertEqual(minimize_calls, [chat])
        self.assertEqual(restore_calls, [chat])
        self.assertEqual(close_calls, [chat])
        self.assertEqual(self.window.sync_calls[-1], chat)

    def test_float_dock_and_close_chat_widget(self):
        chat = _ChatWidget(session_id=5, title="Project Chat")
        self.window.central_tabs.addTab(chat, "Project Chat")

        self.coordinator.float_chat_widget(chat)
        self.assertEqual(self.window.central_tabs.count(), 0)
        self.assertEqual(len(self.window.floating_chat_hosts), 1)
        self.assertFalse(self.window.floating_chat_bar.isHidden())
        self.assertEqual(chat.display_mode, "floating")
        self.assertFalse(chat.context_panel.isVisible())
        self.assertEqual(self.window.sync_calls[-1], None)

        self.coordinator.dock_chat_widget_to_tab(chat)
        self.assertEqual(self.window.central_tabs.count(), 1)
        self.assertEqual(len(self.window.floating_chat_hosts), 0)
        self.assertTrue(self.window.floating_chat_bar.isHidden())
        self.assertEqual(chat.display_mode, "tab")
        self.assertTrue(chat.context_panel.isVisible())
        self.assertEqual(self.window.central_tabs.widget(0), chat)
        self.assertEqual(self.window.sync_calls[-1], chat)

        self.coordinator.close_chat_widget(chat)
        self.assertEqual(self.window.central_tabs.count(), 0)

    def test_minimize_and_restore_floating_chat(self):
        chat = _ChatWidget(session_id=8, title="Focus Chat")
        self.window.central_tabs.addTab(chat, "Focus Chat")

        self.coordinator.float_chat_widget(chat)
        host = self.window.floating_chat_hosts[0]

        self.coordinator.minimize_floating_chat(chat)
        self.assertTrue(host.property("chat_minimized"))
        self.assertTrue(chat.floating_minimized)

        self.coordinator.restore_floating_chat(chat)
        self.assertFalse(host.property("chat_minimized"))
        self.assertFalse(chat.floating_minimized)

    def test_floating_chat_host_can_be_resized_directly(self):
        chat = _ChatWidget(session_id=9, title="Resizable Chat")
        self.window.central_tabs.addTab(chat, "Resizable Chat")

        self.coordinator.float_chat_widget(chat)
        host = self.window.floating_chat_hosts[0]
        original_size = QSize(host.size())

        host.set_preferred_size(QSize(610, 470))

        self.assertNotEqual(host.size(), original_size)
        self.assertEqual(host.size(), QSize(610, 470))

    def test_floating_chat_host_drag_resizes_inside_layout(self):
        chat = _ChatWidget(session_id=13, title="Top Left")
        self.window.central_tabs.addTab(chat, "Top Left")

        self.coordinator.float_chat_widget(chat)
        host = self.window.floating_chat_hosts[0]
        original_size = QSize(host.size())

        QTest.mousePress(host, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(2, 2))
        self.app.processEvents()
        QTest.mouseMove(host, QPoint(32, 32))
        self.app.processEvents()
        QTest.mouseRelease(host, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(32, 32))
        self.app.processEvents()

        self.assertNotEqual(host.size(), original_size)
        self.assertLess(host.width(), original_size.width())
        self.assertLess(host.height(), original_size.height())

    def test_floating_chat_host_resize_edges_cover_all_sides(self):
        chat = _ChatWidget(session_id=10, title="Edges")
        self.window.central_tabs.addTab(chat, "Edges")

        self.coordinator.float_chat_widget(chat)
        host = self.window.floating_chat_hosts[0]

        self.assertEqual(host._resize_edges_for_pos(host.rect().topLeft()), host.EDGE_TOP | host.EDGE_LEFT)
        self.assertEqual(host._resize_edges_for_pos(host.rect().topRight()), host.EDGE_TOP | host.EDGE_RIGHT)
        self.assertEqual(host._resize_edges_for_pos(host.rect().bottomLeft()), host.EDGE_BOTTOM | host.EDGE_LEFT)
        self.assertEqual(host._resize_edges_for_pos(host.rect().bottomRight()), host.EDGE_BOTTOM | host.EDGE_RIGHT)

    def test_find_indexes_and_hosts(self):
        chat = _ChatWidget(session_id=11, title="Lookup")
        self.window.central_tabs.addTab(chat, "Lookup")

        self.assertEqual(self.coordinator.find_chat_tab_index(11), 0)
        self.assertEqual(self.coordinator.find_chat_tab_index(None), -1)
        self.assertIsNone(self.coordinator.find_floating_chat_host(11))

        self.coordinator.float_chat_widget(chat)
        host = self.coordinator.find_floating_chat_host(11)
        self.assertIsNotNone(host)
        self.assertIs(self.coordinator.find_floating_chat_host_by_widget(chat), host)

    def test_floating_chat_resize_border_is_small_and_active(self):
        chat = _ChatWidget(session_id=12, title="Handle")
        self.window.central_tabs.addTab(chat, "Handle")

        self.coordinator.float_chat_widget(chat)
        host = self.window.floating_chat_hosts[0]
        self.assertEqual(host._resize_edges_for_pos(QPoint(3, 3)), host.EDGE_TOP | host.EDGE_LEFT)
        self.assertEqual(host._resize_edges_for_pos(QPoint(4, 4)), host.EDGE_NONE)


if __name__ == "__main__":
    unittest.main()
