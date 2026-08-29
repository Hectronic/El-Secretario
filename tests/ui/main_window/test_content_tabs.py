import sys
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.main_window import content_tabs as content_tabs_module
from src.ui.main_window.content_tabs import ContentTabCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for callback in list(self.callbacks):
            callback(*args, **kwargs)


class _Tabs:
    def __init__(self):
        self.widgets = []
        self.titles = []
        self.current = None

    def count(self):
        return len(self.widgets)

    def widget(self, index):
        return self.widgets[index]

    def addTab(self, widget, title):
        self.widgets.append(widget)
        self.titles.append(title)
        self.current = widget
        return len(self.widgets) - 1

    def setCurrentIndex(self, index):
        self.current = self.widgets[index]

    def currentWidget(self):
        return self.current

    def tabText(self, index):
        return self.titles[index]


class _NoteWidget(QWidget):
    def __init__(self, *_args, **kwargs):
        super().__init__()
        self.current_record_id = kwargs.get("record_id")
        self.note_saved = _Signal()
        self.status_changed = _Signal()
        self.progress_changed = _Signal()
        self.close_requested = _Signal()


class _ChatWidget(QWidget):
    def __init__(self, *_args, **kwargs):
        super().__init__()
        self.session_id = kwargs.get("session_id")
        self.initial_contexts = kwargs.get("initial_contexts")
        self.updated = []

    def update_from_global_selection(self, monday, date_str, tags_filter):
        self.updated.append((monday, date_str, tags_filter))


class _HistoryWidget(QWidget):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.session_requested = _Signal()
        self.session_delete_requested = _Signal()
        self.sessions = None

    def set_sessions(self, sessions):
        self.sessions = sessions


class _SummaryWidget(QWidget):
    def __init__(self, summary_data, *_args, **_kwargs):
        super().__init__()
        self.summary_data = summary_data
        self.regenerate_requested = _Signal()
        self.open_recording_requested = _Signal()
        self.start_chat_requested = _Signal()
        self.start_chat_contexts_requested = _Signal()


class _ToolsWidget(QWidget):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.shown_tabs = []

    def show_tab(self, index):
        self.shown_tabs.append(index)


class _TasksWidget(QWidget):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.open_recording_requested = _Signal()
        self.tasks_changed = _Signal()
        self.global_filters = []
        self.refresh_calls = 0
        self.create_dialog_calls = 0

    def set_global_filters(self, monday, date_str, tags_filter):
        self.global_filters.append((monday, date_str, tags_filter))

    def refresh(self):
        self.refresh_calls += 1

    def open_create_dialog(self):
        self.create_dialog_calls += 1


class _CollectionWidget(QWidget):
    def __init__(self, tag):
        super().__init__()
        self.tag = tag
        self.open_recording = _Signal()
        self.start_chat = _Signal()


class _CalendarWidget(QWidget):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.start_chat_requested = _Signal()
        self.selection_changed = _Signal()
        self.selections = []

    def set_selection(self, monday, date_str, tag=None):
        self.selections.append((monday, date_str, tag))


class _FloatingHost:
    def __init__(self, chat_widget):
        self._chat_widget = chat_widget

    def property(self, name):
        return self._chat_widget if name == "chat_widget" else None


class _Window:
    def __init__(self):
        self.central_tabs = _Tabs()
        self.rag = object()
        self.summary_task_queue = object()
        self.db = MagicMock()
        self.notebook_db = MagicMock()
        self.rag = object()
        self.tag_filter_combo = MagicMock()
        self.tag_filter_combo.currentText.return_value = "work"
        self.current_week_monday = "mon"
        self.current_date_filter = "2026-05-06"
        self.open_recording_tab = MagicMock(return_value=MagicMock())
        self.close_tab = MagicMock()
        self.load_history = MagicMock()
        self.handle_status_message = MagicMock()
        self.handle_progress = MagicMock()
        self._connect_chat_widget = MagicMock()
        self._tab_title_for_chat = MagicMock(return_value="Chat")
        self._set_tab_action_buttons = MagicMock()
        self._sync_chat_context_section = MagicMock()
        self.float_chat_widget = MagicMock()
        self.dock_chat_widget_to_tab = MagicMock()
        self._find_chat_tab_index = MagicMock(return_value=-1)
        self._find_floating_chat_host = MagicMock(return_value=None)
        self.regenerate_summary = MagicMock()
        self.open_chat_tab_with_filters = MagicMock()
        self.open_chat_with_contexts = MagicMock()
        self.refresh_tasks_sidebar = MagicMock()
        self.open_collection_chat = MagicMock()
        self.on_tab_selection_sync = MagicMock()


def _coordinator(monkeypatch):
    monkeypatch.setattr(content_tabs_module, "NoteWidget", _NoteWidget)
    monkeypatch.setattr(content_tabs_module, "ChatWidget", _ChatWidget)
    monkeypatch.setattr(content_tabs_module, "ChatHistoryWidget", _HistoryWidget)
    monkeypatch.setattr(content_tabs_module, "SummaryViewerWidget", _SummaryWidget)
    monkeypatch.setattr(content_tabs_module, "ToolsWidget", _ToolsWidget)
    monkeypatch.setattr(content_tabs_module, "TasksListWidget", _TasksWidget)
    monkeypatch.setattr(content_tabs_module, "CollectionWidget", _CollectionWidget)
    monkeypatch.setattr(content_tabs_module, "CalendarWidget", _CalendarWidget)
    return ContentTabCoordinator(_Window())


def test_open_item_tab_routes_note_and_recording(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window
    window.db.fetch_record.side_effect = [
        {"id": 1, "type": "note", "title": "Note"},
        {"id": 2, "type": "recording"},
        None,
    ]

    note = MagicMock()
    coordinator.open_note_tab = MagicMock(return_value=note)

    assert coordinator.open_item_tab(1) is note
    coordinator.window.open_recording_tab.assert_not_called()
    coordinator.open_note_tab.assert_called_once_with(1)

    assert coordinator.open_item_tab(2) is coordinator.window.open_recording_tab.return_value
    coordinator.window.open_recording_tab.assert_called_once_with(2)

    assert coordinator.open_item_tab(3) is None


def test_open_note_tab_reuses_existing_and_titles_from_record(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window
    window.db.fetch_record.return_value = {"id": 7, "title": "Sprint note"}

    note = coordinator.open_note_tab(7)
    assert note.current_record_id == 7
    assert window.central_tabs.tabText(0) == "Sprint note"

    reopened = coordinator.open_note_tab(7)
    assert reopened is note


def test_open_chat_tab_reuses_existing_session_and_docks_floating(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window

    existing = _ChatWidget(session_id=9)
    window.central_tabs.addTab(existing, "Chat")
    window._find_chat_tab_index.return_value = 0
    assert coordinator.open_chat_tab(9) is existing
    window._sync_chat_context_section.assert_called_once_with(existing)

    host_chat = _ChatWidget(session_id=10)
    window._find_chat_tab_index.return_value = -1
    window._find_floating_chat_host.return_value = _FloatingHost(host_chat)
    assert coordinator.open_chat_tab(10) is host_chat
    window.dock_chat_widget_to_tab.assert_called_once_with(host_chat)


def test_open_chat_context_helpers_build_expected_payloads(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    coordinator.open_chat_tab = MagicMock(return_value=_ChatWidget())

    coordinator.open_chat_tab_with_filters("2026-05-06", ["work", "urgent"])
    coordinator.open_chat_tab.assert_called_once_with(
        initial_contexts=[
            {"type": "date", "value": "2026-05-06", "label": "2026-05-06"},
            {"type": "tag", "value": "work", "label": "work"},
            {"type": "tag", "value": "urgent", "label": "urgent"},
        ]
    )

    coordinator.open_chat_tab.reset_mock()
    coordinator.open_chat_with_contexts([{"type": "tag", "value": "work"}], floating=False)
    coordinator.open_chat_tab.assert_called_once_with(initial_contexts=[{"type": "tag", "value": "work"}])


def test_open_summary_tab_reuses_matching_summary(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window
    existing = _SummaryWidget({"type": "daily", "date": "2026-05-06", "tags_filter": "work"})
    window.central_tabs.addTab(existing, "Daily")

    coordinator.open_summary_tab({"type": "daily", "date": "2026-05-06", "tags_filter": "work"})
    assert window.central_tabs.currentWidget() is existing

    coordinator.open_summary_tab({"type": "weekly", "week_start": "2026-05-05"})
    assert window.central_tabs.tabText(1) == "📅 Week ending 2026-05-05"


def test_open_tools_tab_reuses_existing_and_switches_subtab(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window

    coordinator.open_tools_tab(tab_index=2)
    tools_widget = window.central_tabs.currentWidget()
    assert isinstance(tools_widget, _ToolsWidget)
    assert tools_widget.shown_tabs == [2]
    assert window.central_tabs.tabText(0) == "⚙️ Tools"

    coordinator.open_tools_tab(tab_index=1)
    assert len(window.central_tabs.widgets) == 1
    assert tools_widget.shown_tabs == [2, 1]


def test_open_tasks_tab_reuses_existing_applies_filters_and_create(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window
    window.tag_filter_combo.currentText.return_value = "work"

    coordinator.open_tasks_tab(create_new=False)
    tasks_widget = window.central_tabs.currentWidget()
    assert isinstance(tasks_widget, _TasksWidget)
    assert tasks_widget.global_filters[-1] == ("mon", "2026-05-06", "work")
    assert tasks_widget.create_dialog_calls == 0

    window.tag_filter_combo.currentText.return_value = "All"
    coordinator.open_tasks_tab(create_new=True)
    assert len(window.central_tabs.widgets) == 1
    assert tasks_widget.global_filters[-1] == ("mon", "2026-05-06", None)
    assert tasks_widget.refresh_calls == 1
    assert tasks_widget.create_dialog_calls == 1


def test_open_collection_tab_reuses_by_tag(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window

    coordinator.open_collection_tab("backend")
    created = window.central_tabs.currentWidget()
    assert isinstance(created, _CollectionWidget)
    assert created.tag == "backend"
    assert window.central_tabs.tabText(0) == "Collection: backend"

    coordinator.open_collection_tab("backend")
    assert len(window.central_tabs.widgets) == 1


def test_open_calendar_tab_reuses_existing_and_syncs_selection(monkeypatch):
    _app()
    coordinator = _coordinator(monkeypatch)
    window = coordinator.window
    window.tag_filter_combo.currentText.return_value = "work"

    coordinator.open_calendar_tab()
    calendar = window.central_tabs.currentWidget()
    assert isinstance(calendar, _CalendarWidget)
    assert calendar.selections[-1] == ("mon", "2026-05-06", "work")
    assert window.central_tabs.tabText(0) == "Week Details"

    coordinator.open_calendar_tab()
    assert len(window.central_tabs.widgets) == 1
    assert calendar.selections[-1] == ("mon", "2026-05-06", None)
