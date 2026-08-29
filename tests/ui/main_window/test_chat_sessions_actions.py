import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QListWidget, QTabWidget, QWidget

from src.ui.main_window import chat_sessions_actions as module
from src.ui.main_window.chat_sessions_actions import ChatSessionsActionsCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Menu:
    next_choice_label = None

    def __init__(self, *_args, **_kwargs):
        self.actions = []

    def addAction(self, label):
        action = object()
        self.actions.append((label, action))
        return action

    def exec(self, _point):
        for label, action in self.actions:
            if label == self.next_choice_label:
                return action
        return None


class _Window:
    def __init__(self):
        self.sessions_list = QListWidget()
        self.central_tabs = QTabWidget()
        self.db = MagicMock()
        self.open_chat_tab = MagicMock()
        self.open_floating_chat = MagicMock()
        self.load_chat_sessions = MagicMock()
        self._sync_chat_context_section = MagicMock()
        self._remove_floating_host = MagicMock()
        self._find_floating_chat_host = MagicMock(return_value=None)


def test_context_menu_routes_open_and_floating(monkeypatch):
    _app()
    monkeypatch.setattr(module, "QMenu", _Menu)
    coordinator = ChatSessionsActionsCoordinator(_Window())
    item = MagicMock()
    item.data.return_value = {"id": 7}
    coordinator.window.sessions_list.itemAt = MagicMock(return_value=item)

    _Menu.next_choice_label = "Open"
    coordinator.show_chat_sidebar_context_menu(QPoint(0, 0))
    coordinator.window.open_chat_tab.assert_called_once_with(7)

    coordinator.window.open_chat_tab.reset_mock()
    _Menu.next_choice_label = "Open Floating"
    coordinator.show_chat_sidebar_context_menu(QPoint(0, 0))
    coordinator.window.open_floating_chat.assert_called_once_with(7)


def test_delete_chat_session_by_id_deletes_and_syncs(monkeypatch):
    _app()
    mock_box = MagicMock()
    mock_box.question.return_value = mock_box.StandardButton.Yes
    monkeypatch.setattr(module, "QMessageBox", mock_box)
    coordinator = ChatSessionsActionsCoordinator(_Window())
    coordinator.window.db.fetch_chat_sessions.return_value = [{"id": 8, "name": "Chat"}]
    widget = QWidget()
    widget.current_session_id = 8
    coordinator.window.central_tabs.addTab(widget, "Chat")

    coordinator.delete_chat_session_by_id(8)
    coordinator.window.db.delete_chat_session.assert_called_once_with(8)
    coordinator.window.load_chat_sessions.assert_called_once()
    coordinator.window._sync_chat_context_section.assert_called_once()
