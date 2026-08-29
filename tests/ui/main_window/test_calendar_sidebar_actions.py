import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QApplication, QCalendarWidget

from src.ui.main_window import calendar_sidebar_actions as module
from src.ui.main_window.calendar_sidebar_actions import CalendarSidebarActionsCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Window:
    def __init__(self):
        self.calendar = QCalendarWidget()
        self.current_week_monday = None
        self.current_date_filter = None
        self._last_highlighted_dates = []
        self.request_sidebar_reload = MagicMock()
        self.update_calendar_visuals = MagicMock()
        self.sync_active_tabs = MagicMock()
        self.sidebar_sync = MagicMock()


def test_on_calendar_date_changed_updates_filters_and_sync(monkeypatch):
    _app()
    monkeypatch.setattr(module.QApplication, "keyboardModifiers", lambda: Qt.KeyboardModifier.NoModifier)
    coordinator = CalendarSidebarActionsCoordinator(_Window())
    coordinator.window.calendar.setSelectedDate(QDate(2026, 3, 8))

    coordinator.on_calendar_date_changed()
    assert coordinator.window.current_date_filter == "2026-03-08"
    assert coordinator.window.current_week_monday == QDate(2026, 3, 2)
    coordinator.window.request_sidebar_reload.assert_called_once()
    coordinator.window.sync_active_tabs.assert_called_once()


def test_prev_next_week_sidebar_updates_date_and_requests_reload():
    _app()
    coordinator = CalendarSidebarActionsCoordinator(_Window())
    coordinator.window.calendar.setSelectedDate(QDate(2026, 3, 8))

    coordinator.prev_week_sidebar()
    assert coordinator.window.current_date_filter == "2026-03-01"
    coordinator.window.request_sidebar_reload.assert_called()

    coordinator.window.request_sidebar_reload.reset_mock()
    coordinator.next_week_sidebar()
    assert coordinator.window.current_date_filter == "2026-03-08"
    coordinator.window.request_sidebar_reload.assert_called_once()
