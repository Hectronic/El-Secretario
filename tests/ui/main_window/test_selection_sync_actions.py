import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication, QCalendarWidget, QComboBox

from src.ui.main_window.selection_sync_actions import SelectionSyncActionsCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Window:
    def __init__(self):
        self.current_week_monday = None
        self.current_date_filter = None
        self.calendar = QCalendarWidget()
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItems(["All", "work", "ops"])
        self.update_calendar_visuals = MagicMock()
        self.request_sidebar_reload = MagicMock()
        self.sync_active_tabs = MagicMock()


def test_on_tab_selection_sync_updates_calendar_and_tag():
    _app()
    window = _Window()
    coordinator = SelectionSyncActionsCoordinator(window)
    monday = QDate(2026, 3, 2)

    coordinator.on_tab_selection_sync(monday, "2026-03-05", tag="ops")

    assert window.current_week_monday == monday
    assert window.current_date_filter == "2026-03-05"
    assert window.calendar.selectedDate() == QDate(2026, 3, 5)
    assert window.tag_filter_combo.currentText() == "ops"
    window.update_calendar_visuals.assert_called_once()
    window.request_sidebar_reload.assert_called_once_with(include_tags=True, include_history=True)
    window.sync_active_tabs.assert_called_once()


def test_on_tab_selection_sync_handles_all_tag():
    _app()
    window = _Window()
    coordinator = SelectionSyncActionsCoordinator(window)
    monday = QDate(2026, 3, 2)

    coordinator.on_tab_selection_sync(monday, "2026-03-05", tag="")
    assert window.tag_filter_combo.currentIndex() == 0
