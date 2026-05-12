import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QListWidget

from src.ui.main_window import history_tags_actions as module
from src.ui.main_window.history_tags_actions import HistoryTagsActionsCoordinator


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
        self.history_list = QListWidget()
        self.collections_list = QListWidget()
        self.open_recording_tab = MagicMock()
        self.open_recording_editor_tab = MagicMock()
        self.open_note_tab = MagicMock()
        self.open_summary_tab = MagicMock()
        self.open_collection_tab = MagicMock()
        self.open_collection_chat = MagicMock()


def test_history_menu_routes_recording_and_note(monkeypatch):
    _app()
    monkeypatch.setattr(module, "QMenu", _Menu)
    coordinator = HistoryTagsActionsCoordinator(_Window())
    item = MagicMock()
    item.data.return_value = {"id": 11, "type": "recording"}
    coordinator.window.history_list.itemAt = MagicMock(return_value=item)

    _Menu.next_choice_label = "Open"
    coordinator.show_history_item_context_menu(QPoint(0, 0))
    coordinator.window.open_recording_tab.assert_called_once_with(11)

    coordinator.window.open_recording_tab.reset_mock()
    _Menu.next_choice_label = "Open Audio Editor Tab"
    coordinator.show_history_item_context_menu(QPoint(0, 0))
    coordinator.window.open_recording_editor_tab.assert_called_once_with(11)

    note = MagicMock()
    note.data.return_value = {"id": 12, "type": "note"}
    coordinator.window.history_list.itemAt = MagicMock(return_value=note)
    _Menu.next_choice_label = "Open"
    coordinator.show_history_item_context_menu(QPoint(0, 0))
    coordinator.window.open_note_tab.assert_called_once_with(12)


def test_tags_menu_routes_open_and_chat(monkeypatch):
    _app()
    monkeypatch.setattr(module, "QMenu", _Menu)
    coordinator = HistoryTagsActionsCoordinator(_Window())
    item = MagicMock()
    item.data.return_value = "alpha"
    coordinator.window.collections_list.itemAt = MagicMock(return_value=item)

    _Menu.next_choice_label = "Open"
    coordinator.show_tags_sidebar_context_menu(QPoint(0, 0))
    coordinator.window.open_collection_tab.assert_called_once_with("alpha")

    coordinator.window.open_collection_tab.reset_mock()
    _Menu.next_choice_label = "Chat"
    coordinator.show_tags_sidebar_context_menu(QPoint(0, 0))
    coordinator.window.open_collection_chat.assert_called_once_with("alpha")
