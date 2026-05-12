# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtWidgets import QApplication


class CalendarSidebarActionsCoordinator:
    """Own calendar sidebar navigation, syncing, and highlighting."""

    def __init__(self, window):
        self.window = window

    def on_calendar_date_changed(self):
        date = self.window.calendar.selectedDate()
        modifiers = QApplication.keyboardModifiers()

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self.window.current_date_filter = date.toString("yyyy-MM-dd")
            self.window.current_week_monday = None
        else:
            day_of_week = date.dayOfWeek()
            self.window.current_week_monday = date.addDays(-(day_of_week - 1))
            self.window.current_date_filter = date.toString("yyyy-MM-dd")

        self.window.update_calendar_visuals()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)
        self.window.sync_active_tabs()

    def sync_active_tabs(self):
        self.window.sidebar_sync.sync_active_tabs()

    def prev_week_sidebar(self):
        if not self.window.current_week_monday:
            dt = self.window.calendar.selectedDate()
            self.window.current_week_monday = dt.addDays(-(dt.dayOfWeek() - 1))

        self.window.current_week_monday = self.window.current_week_monday.addDays(-7)
        sunday = self.window.current_week_monday.addDays(6)
        self.window.current_date_filter = sunday.toString("yyyy-MM-dd")
        self.window.calendar.setSelectedDate(sunday)
        self.window.update_calendar_visuals()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)

    def next_week_sidebar(self):
        if not self.window.current_week_monday:
            dt = self.window.calendar.selectedDate()
            self.window.current_week_monday = dt.addDays(-(dt.dayOfWeek() - 1))

        self.window.current_week_monday = self.window.current_week_monday.addDays(7)
        sunday = self.window.current_week_monday.addDays(6)
        self.window.current_date_filter = sunday.toString("yyyy-MM-dd")
        self.window.calendar.setSelectedDate(sunday)
        self.window.update_calendar_visuals()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)

    def update_calendar_visuals(self):
        reset_fmt = QTextCharFormat()
        week_fmt = QTextCharFormat()
        week_fmt.setBackground(QColor("#E3F2FD"))
        selected_fmt = QTextCharFormat()
        selected_fmt.setBackground(QColor("#2196F3"))
        selected_fmt.setForeground(QColor("white"))

        if hasattr(self.window, "_last_highlighted_dates"):
            for d in self.window._last_highlighted_dates:
                self.window.calendar.setDateTextFormat(d, reset_fmt)

        highlighted = []
        if self.window.current_week_monday:
            mon = self.window.current_week_monday
            for i in range(7):
                d = mon.addDays(i)
                self.window.calendar.setDateTextFormat(d, week_fmt)
                highlighted.append(d)

            if self.window.current_date_filter:
                end_date = QDate.fromString(self.window.current_date_filter, "yyyy-MM-dd")
                if mon and end_date >= mon and end_date <= mon.addDays(6):
                    curr = mon
                    while curr <= end_date:
                        self.window.calendar.setDateTextFormat(curr, selected_fmt)
                        if curr not in highlighted:
                            highlighted.append(curr)
                        curr = curr.addDays(1)
                else:
                    self.window.calendar.setDateTextFormat(end_date, selected_fmt)
                    if end_date not in highlighted:
                        highlighted.append(end_date)
            else:
                for i in range(7):
                    d = mon.addDays(i)
                    self.window.calendar.setDateTextFormat(d, selected_fmt)
                    if d not in highlighted:
                        highlighted.append(d)
        elif self.window.current_date_filter:
            d = QDate.fromString(self.window.current_date_filter, "yyyy-MM-dd")
            self.window.calendar.setDateTextFormat(d, selected_fmt)
            highlighted.append(d)

        self.window._last_highlighted_dates = highlighted

    def reset_date_filter(self):
        self.window.current_date_filter = None
        self.window.current_week_monday = None
        self.window.update_calendar_visuals()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)
