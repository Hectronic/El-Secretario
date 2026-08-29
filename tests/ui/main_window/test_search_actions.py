import sys
from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication

from src.ui.main_window import search_actions as module
from src.ui.main_window.search_actions import SearchActionsCoordinator


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


class _Thread:
    def __init__(self, *_args, **_kwargs):
        self.finished = _Signal()
        self.error = _Signal()
        self.started = False

    def isRunning(self):
        return False

    def start(self):
        self.started = True


class _SearchWidget:
    def __init__(self, query):
        self.query = query
        self.result_clicked = _Signal()
        self.results = None

    def display_results(self, results):
        self.results = results


class _Tabs:
    def __init__(self):
        self.widgets = []
        self.current = -1

    def addTab(self, widget, _title):
        self.widgets.append(widget)
        return len(self.widgets) - 1

    def setCurrentIndex(self, index):
        self.current = index


class _Window:
    def __init__(self):
        self.rag = object()
        self.search_thread = None
        self.open_recording_tab = MagicMock()
        self.central_tabs = _Tabs()


def test_perform_welcome_search_creates_and_starts_thread(monkeypatch):
    _app()
    monkeypatch.setattr(module, "SearchThread", _Thread)
    coordinator = SearchActionsCoordinator(_Window())

    coordinator.perform_welcome_search("alpha")
    assert isinstance(coordinator.window.search_thread, _Thread)
    assert coordinator.window.search_thread.started is True


def test_on_search_finished_new_tab_opens_results(monkeypatch):
    _app()
    monkeypatch.setattr(module, "SearchResultsWidget", _SearchWidget)
    coordinator = SearchActionsCoordinator(_Window())
    coordinator.window.search_thread = MagicMock()

    coordinator.on_search_finished_new_tab([{"id": 1}], "alpha")
    assert coordinator.window.search_thread is None
    assert len(coordinator.window.central_tabs.widgets) == 1
    assert coordinator.window.central_tabs.current == 0
