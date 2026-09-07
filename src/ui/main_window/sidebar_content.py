"""Compatibility façade for main-window sidebar content behavior."""

from src.ui.main_window.sidebar_history import SidebarHistoryCoordinator
from src.ui.main_window.sidebar_organization import SidebarOrganizationCoordinator
from src.ui.main_window.sidebar_sessions import SidebarSessionsCoordinator


class SidebarContentCoordinator:
    """Preserve the public sidebar API while focused coordinators own behavior."""

    def __init__(self, window):
        self.window = window
        self.history = SidebarHistoryCoordinator(window)
        self.organization = SidebarOrganizationCoordinator(window)
        self.sessions = SidebarSessionsCoordinator(window)

    def load_history(self, tag_filter="All", favorites_only=False): return self.history.load_history(tag_filter, favorites_only)
    def refresh_sidebar(self): return self.history.refresh_sidebar()
    def request_sidebar_reload(self, include_tags=False, include_history=True, delay_ms=120): return self.history.request_sidebar_reload(include_tags, include_history, delay_ms)
    def _apply_pending_sidebar_reload(self): return self.history.apply_pending_sidebar_reload()
    def refresh_tag_filter(self): return self.history.refresh_tag_filter()
    def filter_history_list(self, text): return self.history.filter_history_list(text)
    def on_favorite_toggled(self, record_id, is_favorite): return self.history.on_favorite_toggled(record_id, is_favorite)
    def delete_recording(self, record_id): return self.history.delete_recording(record_id)
    def load_collections(self): return self.organization.load_collections()
    def load_notebooks(self): return self.organization.load_notebooks()
    def open_collections_list(self): return self.organization.open_collections_list()
    def open_notebooks_list(self): return self.organization.open_notebooks_list()
    def open_notebook(self, notebook_id, name): return self.organization.open_notebook(notebook_id, name)
    def open_notebook_chat(self, notebook_id, notebook_name): return self.organization.open_notebook_chat(notebook_id, notebook_name)
    def create_notebook(self): return self.organization.create_notebook()
    def rename_notebook(self, notebook_id): return self.organization.rename_notebook(notebook_id)
    def delete_notebook(self, notebook_id): return self.organization.delete_notebook(notebook_id)
    def show_notebooks_sidebar_context_menu(self, point): return self.organization.show_notebooks_sidebar_context_menu(point)
    def load_chat_sessions(self): return self.sessions.load_chat_sessions()
