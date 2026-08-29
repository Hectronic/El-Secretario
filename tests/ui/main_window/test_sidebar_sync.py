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

from src.ui.main_window import sidebar_sync as sidebar_sync_module
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator


class _ChatWidget:
    def __init__(self):
        self.context_panel = object()
        self.updates = []

    def update_from_global_selection(self, monday, date_str, tags_filter):
        self.updates.append((monday, date_str, tags_filter))


class _CalendarWidget:
    def __init__(self):
        self.selections = []

    def set_selection(self, monday, date_str, tags_filter):
        self.selections.append((monday, date_str, tags_filter))


class _TasksWidget:
    def __init__(self):
        self.filters = []

    def set_global_filters(self, monday, date_str, tags_filter):
        self.filters.append((monday, date_str, tags_filter))


class _SidebarPanel:
    def __init__(self):
        self.restored = []

    def restore_from_panel(self, panel):
        self.restored.append(panel)


class _VisibleBox:
    def __init__(self):
        self._visible = False

    def setVisible(self, value):
        self._visible = bool(value)

    def isVisible(self):
        return self._visible


class _Tabs:
    def __init__(self):
        self._widgets = []
        self._current = None

    def addTab(self, widget, _title):
        self._widgets.append(widget)
        if self._current is None:
            self._current = widget

    def count(self):
        return len(self._widgets)

    def widget(self, index):
        return self._widgets[index]

    def currentWidget(self):
        return self._current

    def setCurrentWidget(self, widget):
        self._current = widget


class _Host:
    def __init__(self, chat_widget):
        self._chat_widget = chat_widget

    def property(self, name):
        return self._chat_widget if name == "chat_widget" else None


class _TagCombo:
    def currentText(self):
        return "Work"


class _Window:
    def __init__(self):
        self.central_tabs = _Tabs()
        self.current_week_monday = "mon"
        self.current_date_filter = "2026-05-06"
        self.tag_filter_combo = _TagCombo()
        self.floating_chat_hosts = []
        self._right_sidebar_sections = {
            "chat_context": {
                "container": _VisibleBox(),
                "context_panel": _SidebarPanel(),
            },
            "tasks": {},
        }
        self._right_sidebar_last_non_chat_section = "tasks"
        self._active_right_section = "tasks"
        self.active_sections = []

    def _set_active_right_section(self, section_key):
        self._active_right_section = section_key
        self.active_sections.append(section_key)


def test_current_chat_widget_tracks_current_tab(monkeypatch):
    monkeypatch.setattr(sidebar_sync_module, "ChatWidget", _ChatWidget)
    window = _Window()
    coordinator = SidebarSyncCoordinator(window)

    chat = _ChatWidget()
    window.central_tabs.addTab(object(), "other")
    window.central_tabs.addTab(chat, "chat")
    window.central_tabs.setCurrentWidget(chat)

    assert coordinator.current_chat_widget() is chat


def test_sync_chat_context_section_hides_and_falls_back_when_no_chat(monkeypatch):
    monkeypatch.setattr(sidebar_sync_module, "ChatWidget", _ChatWidget)
    window = _Window()
    coordinator = SidebarSyncCoordinator(window)

    section = window._right_sidebar_sections["chat_context"]
    section["container"].setVisible(True)
    window._active_right_section = "chat_context"

    coordinator.sync_chat_context_section(None)

    assert section["container"].isVisible() is False
    assert window._active_right_section == "tasks"


def test_sync_chat_context_section_restores_panel_for_current_chat(monkeypatch):
    monkeypatch.setattr(sidebar_sync_module, "ChatWidget", _ChatWidget)
    window = _Window()
    coordinator = SidebarSyncCoordinator(window)

    chat = _ChatWidget()
    window.central_tabs.addTab(chat, "chat")
    window.central_tabs.setCurrentWidget(chat)

    coordinator.sync_chat_context_section(chat)

    assert window._right_sidebar_sections["chat_context"]["container"].isVisible() is True
    assert window._right_sidebar_sections["chat_context"]["context_panel"].restored == [chat.context_panel]
    assert window._active_right_section == "chat_context"


def test_sync_active_tabs_pushes_sidebar_state_to_visible_tabs(monkeypatch):
    monkeypatch.setattr(sidebar_sync_module, "ChatWidget", _ChatWidget)
    monkeypatch.setattr(sidebar_sync_module, "CalendarWidget", _CalendarWidget)
    monkeypatch.setattr(sidebar_sync_module, "TasksListWidget", _TasksWidget)

    window = _Window()
    coordinator = SidebarSyncCoordinator(window)
    calendar = _CalendarWidget()
    chat = _ChatWidget()
    tasks = _TasksWidget()
    window.central_tabs.addTab(calendar, "calendar")
    window.central_tabs.addTab(chat, "chat")
    window.central_tabs.addTab(tasks, "tasks")

    host = _Host(_ChatWidget())
    window.floating_chat_hosts = [host]

    coordinator.sync_active_tabs()

    assert calendar.selections == [("mon", "2026-05-06", "Work")]
    assert chat.updates == [("mon", "2026-05-06", "Work")]
    assert tasks.filters == [("mon", "2026-05-06", "Work")]
    assert host.property("chat_widget").updates == [("mon", "2026-05-06", "Work")]
