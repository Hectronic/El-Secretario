import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.ui.main_window.history_navigation_actions import HistoryNavigationActionsCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Item:
    def __init__(self, data):
        self._data = data

    def data(self, role):
        return self._data if role == Qt.ItemDataRole.UserRole else None


class _Window:
    def __init__(self):
        self.open_recording_tab = MagicMock()
        self.open_note_tab = MagicMock()
        self.open_summary_tab = MagicMock()


def test_on_history_item_clicked_routes_by_type():
    _app()
    window = _Window()
    coordinator = HistoryNavigationActionsCoordinator(window)

    coordinator.on_history_item_clicked(_Item({"id": 1, "type": "recording"}))
    window.open_recording_tab.assert_called_once_with(1)

    coordinator.on_history_item_clicked(_Item({"id": 2, "type": "note"}))
    window.open_note_tab.assert_called_once_with(2)

    data = {"type": "daily", "date": "2026-05-11"}
    coordinator.on_history_item_clicked(_Item(data))
    window.open_summary_tab.assert_called_once_with(data)
