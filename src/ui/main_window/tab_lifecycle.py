# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from PyQt6.QtWidgets import QMenu, QMessageBox
from PyQt6.QtGui import QAction

from src.ui.chat_widget import ChatWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.recording_widget import RecordingWidget
from src.ui.welcome_widget import WelcomeWidget


class TabLifecycleCoordinator:
    """Own tab close and tab context-menu behavior."""

    def __init__(self, window):
        self.window = window

    def close_tab(self, index):
        widget = self.window.central_tabs.widget(index)
        if widget is None:
            return
        if isinstance(widget, WelcomeWidget):
            return
        if isinstance(widget, RecordingInProgressWidget):
            if getattr(widget, "recording_started", False):
                widget.finish_recording()
                return
        if isinstance(widget, RecordingWidget):
            if hasattr(widget, "has_unsaved_changes") and widget.has_unsaved_changes():
                reply = QMessageBox.question(
                    self.window,
                    "Unsaved Changes",
                    "This recording has unsaved changes. Save them before closing?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    return
                if reply == QMessageBox.StandardButton.Save:
                    if hasattr(widget, "save_all_changes") and not widget.save_all_changes():
                        return
        if hasattr(widget, "cleanup"):
            try:
                widget.cleanup()
            except Exception:
                pass

        self.window.central_tabs.removeTab(index)
        widget.deleteLater()

        if self.window.central_tabs.count() == 0:
            self.window.show_welcome_screen()
        self.window._sync_chat_context_section()

    def show_tab_context_menu(self, point):
        index = self.window.central_tabs.tabBar().tabAt(point)
        if index == -1:
            return

        menu = QMenu(self.window)
        widget = self.window.central_tabs.widget(index)

        if isinstance(widget, ChatWidget):
            float_action = QAction("Move to Floating Window", self.window)
            float_action.triggered.connect(lambda: self.window.float_chat_widget(widget))
            menu.addAction(float_action)
            menu.addSeparator()
        elif isinstance(widget, RecordingWidget):
            editor_action = QAction("Open Audio Editor Tab", self.window)
            editor_action.triggered.connect(
                lambda: self.window.open_recording_editor_tab(widget.current_record_id)
            )
            menu.addAction(editor_action)
            menu.addSeparator()

        close_action = QAction("Close", self.window)
        close_action.triggered.connect(lambda: self.close_tab(index))
        menu.addAction(close_action)

        close_others_action = QAction("Close Others", self.window)
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        menu.addAction(close_others_action)

        close_all_action = QAction("Close All", self.window)
        close_all_action.triggered.connect(self.close_all_tabs)
        menu.addAction(close_all_action)

        menu.exec(self.window.central_tabs.mapToGlobal(point))

    def close_other_tabs(self, keep_index):
        count = self.window.central_tabs.count()
        for i in range(count - 1, -1, -1):
            if i != keep_index:
                self.close_tab(i)

    def close_all_tabs(self):
        count = self.window.central_tabs.count()
        for i in range(count - 1, -1, -1):
            self.close_tab(i)

        if self.window.central_tabs.count() == 0:
            self.window.show_welcome_screen()
