from unittest.mock import MagicMock

from PyQt6.QtWidgets import QTabWidget, QWidget

from src.database import DBManager
from src.ui.chat_widget import ChatWidget
from src.ui.context_manager_panel import ContextManagerPanel
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator


class _Notebooks:
    def get_notebooks(self):
        return []

    def get_entries(self, _notebook_id):
        return []


class _Window:
    def __init__(self, db, notebook_db):
        self.central_tabs = QTabWidget()
        self._right_sidebar_sections = {}
        self._active_right_section = None
        self._right_sidebar_last_non_chat_section = "tasks"
        self.chat_context_panel = ContextManagerPanel(
            db, notebook_db, show_header=False, interactive=True
        )
        self._right_sidebar_sections["chat_context"] = {
            "container": QWidget(),
            "context_panel": self.chat_context_panel,
        }
        self._set_active_right_section = self.set_active_section
        self.sidebar_sync = SidebarSyncCoordinator(self)
        self.sidebar_sync.bind_chat_context_panel(self.chat_context_panel)

    def set_active_section(self, key):
        self._active_right_section = key


def test_right_sidebar_edits_only_the_active_chats_context(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-context-sidebar.sqlite"))
    notebooks = _Notebooks()
    window = _Window(db, notebooks)
    first = ChatWidget(MagicMock(), persistence=db, notebook_persistence=notebooks)
    second = ChatWidget(MagicMock(), persistence=db, notebook_persistence=notebooks)
    qtbot.addWidget(window.central_tabs)
    qtbot.addWidget(first)
    qtbot.addWidget(second)
    window.central_tabs.addTab(first, "First")
    window.central_tabs.addTab(second, "Second")

    first.context_panel.active_global_tags = ["first-only"]
    window.central_tabs.setCurrentWidget(first)
    window.sidebar_sync.sync_chat_context_section(first)
    assert window.chat_context_panel.get_active_tags() == ["first-only"]

    window.central_tabs.setCurrentWidget(second)
    window.sidebar_sync.sync_chat_context_section(second)
    window.chat_context_panel.active_global_tags = ["second-only"]
    window.chat_context_panel._update_status_labels()
    window.chat_context_panel.context_changed.emit()

    assert second.context_panel.get_active_tags() == ["second-only"]
    assert first.context_panel.get_active_tags() == ["first-only"]
    assert "second-only" in second.context_summary.text()
    assert "second-only" not in first.context_summary.text()
