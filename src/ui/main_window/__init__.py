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

import logging
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtGui import QIcon

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.main_window.recording_tabs import RecordingTabCoordinator
from src.ui.main_window.bootstrap import bootstrap_main_window
from src.ui.main_window.content_tabs import ContentTabCoordinator
from src.ui.main_window.chat_floating import FloatingChatCoordinator
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator
from src.ui.main_window.sidebar_content import SidebarContentCoordinator
from src.ui.main_window.sidebar_actions import SidebarActionsCoordinator
from src.ui.main_window.setup_actions import SetupActionsCoordinator
from src.ui.main_window.tab_lifecycle import TabLifecycleCoordinator
from src.ui.main_window.search_actions import SearchActionsCoordinator
from src.ui.main_window.selection_sync_actions import SelectionSyncActionsCoordinator
from src.ui.main_window.history_navigation_actions import HistoryNavigationActionsCoordinator
from src.ui.main_window.summary_actions import SummaryActionsCoordinator
from src.ui.main_window.summary_queue_status import SummaryQueueStatusCoordinator
from src.ui.main_window.runtime_startup import RuntimeStartupCoordinator
from src.ui.main_window.shell_actions import MainWindowShellCoordinator
from src.ui.main_window.layout import build_main_window_layout
from src.ui.styles import apply_theme

from src.ui.summary_task_queue import SummaryTaskQueueManager

Recorder = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        import logging
        logging.info("Initializing MainWindow...")
        self.setWindowTitle("El Secretario")
        self.setWindowIcon(QIcon("logo.png"))
        self.resize(1450, 860)

        self.db = DBManager()
        self.notebook_db = NotebookDBManager()
        global Recorder
        if Recorder is None:
            from src.audio import Recorder as _Recorder
            Recorder = _Recorder
        self.recorder = Recorder()
        # We can connect global recorder signals here if needed,
        # but RecordingWidget handles its own UI updates.

        self.search_thread = None
        self.regen_worker = None
        self.summary_task_queue = SummaryTaskQueueManager(self)
        self.recording_tabs = RecordingTabCoordinator(self)
        self.content_tabs = ContentTabCoordinator(self)
        self.sidebar_sync = SidebarSyncCoordinator(self)
        self.chat_floating = FloatingChatCoordinator(self)
        self.sidebar_content = SidebarContentCoordinator(self)
        self.sidebar_actions = SidebarActionsCoordinator(self)
        self.setup_actions = SetupActionsCoordinator(self)
        self.tab_lifecycle = TabLifecycleCoordinator(self)
        self.search_actions = SearchActionsCoordinator(self)
        self.selection_sync_actions = SelectionSyncActionsCoordinator(self)
        self.history_navigation_actions = HistoryNavigationActionsCoordinator(self)
        self.summary_actions = SummaryActionsCoordinator(self)
        self.summary_queue_status = SummaryQueueStatusCoordinator(self)
        self.runtime_startup = RuntimeStartupCoordinator(self)
        self.shell_actions = MainWindowShellCoordinator(self)
        self.tasks_sidebar_limit = 20
        self._pending_history_reload = False
        self._pending_tag_reload = False
        self._sidebar_refresh_timer = QTimer(self)
        self._sidebar_refresh_timer.setSingleShot(True)
        self._sidebar_refresh_timer.timeout.connect(self._apply_pending_sidebar_reload)
        self._right_sidebar_sections = {}
        self._active_right_section = None
        self._right_sidebar_layout = None
        self._right_sidebar_bottom_spacer_index = None
        self._right_sidebar_last_non_chat_section = "tasks"
        self.floating_chat_hosts = []

        apply_theme()

        self.init_ui()
        bootstrap_main_window(self)
        logging.info("MainWindow initialized.")

    def _apply_rag_runtime_env(self, rag_config):
        self.runtime_startup.apply_rag_runtime_env(rag_config)

    def _propagate_rag_engine_to_open_tabs(self):
        self.runtime_startup.propagate_rag_engine_to_open_tabs()

    def _build_rag_engine(self, rag_config, reason="runtime"):
        self.runtime_startup.build_rag_engine(rag_config, reason)

    def _log_user_settings_snapshot(self, context: str):
        self.runtime_startup.log_user_settings_snapshot(context)

    def _enqueue_missing_previous_week_summary_if_enabled(self):
        self.runtime_startup.enqueue_missing_previous_week_summary_if_enabled()

    def _enqueue_missing_previous_daily_summary_if_enabled(self):
        self.runtime_startup.enqueue_missing_previous_daily_summary_if_enabled()

    def _get_summary_queue_status(self):
        """Return the queue-status coordinator, including during early startup."""
        coordinator = self.__dict__.get("summary_queue_status")
        if coordinator is None:
            coordinator = SummaryQueueStatusCoordinator(self)
            self.__dict__["summary_queue_status"] = coordinator
        return coordinator

    def _setup_task_status_bar(self):
        self._get_summary_queue_status().setup_status_bar()

    def open_queue_manager_tab(self):
        self._get_summary_queue_status().open_queue_manager_tab()

    def _connect_task_queue_signals(self):
        self._get_summary_queue_status().connect_task_queue_signals()

    def _refresh_task_metrics(self):
        self._get_summary_queue_status().refresh_task_metrics()

    def _format_task_name(self, task):
        return self._get_summary_queue_status().format_task_name(task)

    def _on_summary_task_enqueued(self, task, position):
        self._get_summary_queue_status().on_summary_task_enqueued(task, position)

    def _on_summary_task_started(self, task, remaining_pending):
        self._get_summary_queue_status().on_summary_task_started(task, remaining_pending)

    def _on_summary_task_finished(self, task):
        self._get_summary_queue_status().on_summary_task_finished(task)

    def _on_summary_task_failed(self, task, error_msg):
        self._get_summary_queue_status().on_summary_task_failed(task, error_msg)

    def _on_summary_task_skipped(self, task, reason):
        self._get_summary_queue_status().on_summary_task_skipped(task, reason)

    def _on_summary_queue_changed(self, pending_count, is_running):
        self._get_summary_queue_status().on_summary_queue_changed(pending_count, is_running)

    def handle_status_message(self, message):
        self._get_summary_queue_status().handle_status_message(message)

    def handle_progress(self, value):
        self._get_summary_queue_status().handle_progress(value)

    def _refresh_daily_summary_viewers(self, date, tags_filter):
        self._get_summary_queue_status().refresh_daily_summary_viewers(date, tags_filter)

    def init_ui(self):
        build_main_window_layout(self)
    def _on_right_section_header_clicked(self, section_key):
        self.shell_actions.on_right_section_header_clicked(section_key)

    def _set_active_right_section(self, section_key):
        self.shell_actions.set_active_right_section(section_key)

    def _on_central_tab_changed(self, _index):
        self.shell_actions.on_central_tab_changed(_index)

    def _sync_chat_context_section(self, chat_widget=None):
        self.sidebar_sync.sync_chat_context_section(chat_widget)

    def show_welcome_screen(self):
        self.shell_actions.show_welcome_screen()

    def open_item_tab(self, record_id):
        return self.content_tabs.open_item_tab(record_id)

    def generate_today_daily_summary(self):
        self.runtime_startup.enqueue_today_daily_summary()

    def start_new_recording(self, config):
        self.recording_tabs.start_new_recording(config)

    def _sync_recording_tab_titles(self, record_id):
        self.recording_tabs.sync_recording_tab_titles(record_id)

    def _handle_recording_widget_saved(self, rec_widget):
        self.recording_tabs.handle_recording_widget_saved(rec_widget)

    def _handle_recording_widget_deleted(self, record_id):
        self.recording_tabs.handle_recording_widget_deleted(record_id)

    def _close_recording_tabs(self, record_id):
        self.recording_tabs.close_recording_tabs(record_id)

    def open_recording_tab(self, record_id, config=None, force_new=False):
        """Open a recording tab for an existing record."""
        return self.recording_tabs.open_recording_tab(record_id, config=config, force_new=force_new)

    def open_recording_editor_tab(self, record_id, config=None):
        """Open a dedicated audio-editing tab for an existing recording."""
        return self.recording_tabs.open_recording_editor_tab(record_id, config=config)

    def open_note_tab(self, record_id=None):
        return self.content_tabs.open_note_tab(record_id)

    def on_recording_finished(self, file_path, config, widget):
        self.recording_tabs.on_recording_finished(file_path, config, widget)



    def changeEvent(self, event):
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.StyleChange,
        ) and hasattr(self, "floating_chat_bar"):
            self.chat_floating.refresh_floating_chat_bar()
        super().changeEvent(event)

    def _connect_chat_widget(self, chat_widget):
        self.chat_floating.connect_chat_widget(chat_widget)

    def _find_chat_tab_index(self, session_id):
        return self.chat_floating.find_chat_tab_index(session_id)

    def _find_floating_chat_host(self, session_id):
        return self.chat_floating.find_floating_chat_host(session_id)

    def _find_floating_chat_host_by_widget(self, chat_widget):
        return self.chat_floating.find_floating_chat_host_by_widget(chat_widget)

    def _remove_floating_host(self, host):
        self.chat_floating.remove_floating_host(host)

    def _refresh_floating_chat_bar(self):
        self.chat_floating.refresh_floating_chat_bar()

    def _tab_title_for_chat(self, chat_widget):
        return self.chat_floating.tab_title_for_chat(chat_widget)

    def _set_tab_action_buttons(self, widget):
        self.chat_floating.set_tab_action_buttons(widget)

    def _sync_chat_widget_title(self, chat_widget, title):
        self.chat_floating.sync_chat_widget_title(chat_widget, title)

    def float_chat_widget(self, chat_widget):
        self.chat_floating.float_chat_widget(chat_widget)

    def minimize_floating_chat(self, chat_widget):
        self.chat_floating.minimize_floating_chat(chat_widget)

    def restore_floating_chat(self, chat_widget):
        self.chat_floating.restore_floating_chat(chat_widget)

    def dock_chat_widget_to_tab(self, chat_widget):
        self.chat_floating.dock_chat_widget_to_tab(chat_widget)

    def close_chat_widget(self, chat_widget):
        self.chat_floating.close_chat_widget(chat_widget)

    def open_chat_tab(self, session_id=None, initial_contexts=None):
        return self.content_tabs.open_chat_tab(session_id=session_id, initial_contexts=initial_contexts)

    def open_floating_chat(self, session_id=None, initial_contexts=None):
        return self.content_tabs.open_floating_chat(session_id=session_id, initial_contexts=initial_contexts)

    def open_chat_tab_from_current_context(self):
        return self.content_tabs.open_chat_tab_from_current_context()

    def open_chat_history_tab(self):
        return self.content_tabs.open_chat_history_tab()

    def open_tools_tab(self, tab_index=0):
        return self.content_tabs.open_tools_tab(tab_index=tab_index)

    def open_tasks_tab(self, create_new=False):
        return self.content_tabs.open_tasks_tab(create_new=create_new)

    def close_tab(self, index):
        return self.tab_lifecycle.close_tab(index)

    def close_floating_chat(self, chat_widget):
        self.chat_floating.close_floating_chat(chat_widget)

    def show_tab_context_menu(self, point):
        return self.tab_lifecycle.show_tab_context_menu(point)

    def show_history_item_context_menu(self, point):
        return self.sidebar_actions.show_history_item_context_menu(point)

    def close_other_tabs(self, keep_index):
        return self.tab_lifecycle.close_other_tabs(keep_index)

    def close_all_tabs(self):
        return self.tab_lifecycle.close_all_tabs()

    def load_history(self, tag_filter="All", favorites_only=False):
        self.sidebar_content.load_history(tag_filter=tag_filter, favorites_only=favorites_only)

    def refresh_sidebar(self):
        self.sidebar_content.refresh_sidebar()

    def request_sidebar_reload(self, include_tags=False, include_history=True, delay_ms=120):
        self.sidebar_content.request_sidebar_reload(
            include_tags=include_tags,
            include_history=include_history,
            delay_ms=delay_ms,
        )

    def _apply_pending_sidebar_reload(self):
        self.sidebar_content._apply_pending_sidebar_reload()

    def refresh_tag_filter(self):
        self.sidebar_content.refresh_tag_filter()

    def load_collections(self):
        self.sidebar_content.load_collections()

    def load_notebooks(self):
        self.sidebar_content.load_notebooks()

    def on_notebook_clicked(self, item):
        """Handle notebook click in sidebar."""
        notebook_id = item.data(Qt.ItemDataRole.UserRole)
        notebook_name = item.text().replace("📓 ", "")
        self.open_notebook(notebook_id, notebook_name)

    def on_collection_clicked(self, item):
        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            return
        self.open_collection_tab(tag)

    def create_notebook(self):
        self.sidebar_content.create_notebook()

    def rename_notebook(self, notebook_id):
        self.sidebar_content.rename_notebook(notebook_id)

    def delete_notebook(self, notebook_id):
        self.sidebar_content.delete_notebook(notebook_id)

    def show_notebooks_sidebar_context_menu(self, point):
        self.sidebar_content.show_notebooks_sidebar_context_menu(point)

    def open_selected_tag_chat(self):
        item = self.collections_list.currentItem()
        if item is None:
            self.open_chat_tab(None)
            return

        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            self.open_chat_tab(None)
            return
        self.open_collection_chat(tag)

    def show_tags_sidebar_context_menu(self, point):
        return self.sidebar_actions.show_tags_sidebar_context_menu(point)

    def open_collection_tab(self, tag):
        return self.content_tabs.open_collection_tab(tag)

    def open_collection_chat(self, tag):
        self.open_chat_tab(initial_contexts=[{"type": "tag", "value": tag, "label": tag}])

    def open_calendar_tab(self):
        return self.content_tabs.open_calendar_tab()

    def on_tag_filter_changed(self, tag):
        self.request_sidebar_reload(include_history=True)
        self.sync_active_tabs()

    def on_tab_selection_sync(self, monday, date_str, tag=None):
        return self.selection_sync_actions.on_tab_selection_sync(monday, date_str, tag=tag)



    def open_chat_tab_with_filters(self, date_str, tags):
        return self.content_tabs.open_chat_tab_with_filters(date_str, tags)

    def open_chat_with_contexts(self, contexts, floating=False):
        return self.content_tabs.open_chat_with_contexts(contexts, floating=floating)

    def on_history_item_clicked(self, item):
        self.history_navigation_actions.on_history_item_clicked(item)

    def open_summary_tab(self, summary_data):
        return self.content_tabs.open_summary_tab(summary_data)

    def regenerate_summary(self, summary_data):
        self.summary_actions.regenerate_summary(summary_data)



    def perform_welcome_search(self, query):
        self.search_actions.perform_welcome_search(query)

    def on_search_finished_new_tab(self, results, query):
        self.search_actions.on_search_finished_new_tab(results, query)

    def on_search_error(self, error_message):
        self.search_actions.on_search_error(error_message)

    def load_chat_sessions(self):
        self.sidebar_content.load_chat_sessions()

    def refresh_tasks_sidebar(self):
        self.sidebar_actions.refresh_tasks_sidebar()

    def on_task_sidebar_item_changed(self, item):
        self.sidebar_actions.on_task_sidebar_item_changed(item)

    def show_tasks_sidebar_context_menu(self, point):
        self.sidebar_actions.show_tasks_sidebar_context_menu(point)

    def on_chat_session_clicked(self, item):
        self.sidebar_actions.on_chat_session_clicked(item)

    def show_chat_sidebar_context_menu(self, point):
        self.sidebar_actions.show_chat_sidebar_context_menu(point)

    def delete_chat_session_by_id(self, session_id):
        self.sidebar_actions.delete_chat_session_by_id(session_id)

    def delete_selected_chat_session(self):
        self.sidebar_actions.delete_selected_chat_session()

    def on_calendar_date_changed(self):
        self.sidebar_actions.on_calendar_date_changed()

    def sync_active_tabs(self):
        self.sidebar_actions.sync_active_tabs()

    def prev_week_sidebar(self):
        self.sidebar_actions.prev_week_sidebar()

    def next_week_sidebar(self):
        self.sidebar_actions.next_week_sidebar()

    def update_calendar_visuals(self):
        self.sidebar_actions.update_calendar_visuals()

    def reset_date_filter(self):
        self.sidebar_actions.reset_date_filter()

    def filter_history_list(self, text):
        self.sidebar_content.filter_history_list(text)

    def on_favorite_toggled(self, record_id, is_favorite):
        self.sidebar_content.on_favorite_toggled(record_id, is_favorite)

    def delete_recording(self, record_id):
        self.sidebar_content.delete_recording(record_id)

    def open_settings_tab(self):
        self.setup_actions.open_settings_tab()

    def import_audio_file(self, config):
        self.setup_actions.import_audio_file(config)

    def open_collections_list(self):
        self.sidebar_content.open_collections_list()

    def open_notebooks_list(self):
        self.sidebar_content.open_notebooks_list()

    def open_notebook(self, notebook_id, name):
        self.sidebar_content.open_notebook(notebook_id, name)

    def open_notebook_chat(self, notebook_id, notebook_name):
        self.sidebar_content.open_notebook_chat(notebook_id, notebook_name)

    # open_maintenance_tab removed - now handled by open_tools_tab

    def closeEvent(self, event):
        logging.warning(
            "MainWindow.closeEvent triggered. tabs=%d queue_running=%s recorder_recording=%s",
            self.central_tabs.count(),
            self.summary_task_queue.is_running if self.summary_task_queue else None,
            self.recorder.is_recording if self.recorder else None,
        )
        self._sidebar_refresh_timer.stop()
        self._pending_history_reload = False
        self._pending_tag_reload = False

        # Stop background workers before Qt starts tearing down widgets.
        if self.search_thread and self.search_thread.isRunning():
            try:
                self.search_thread.requestInterruption()
                self.search_thread.quit()
                self.search_thread.wait(3000)
            except Exception:
                pass
        self.search_thread = None

        if self.summary_task_queue:
            self.summary_task_queue.cancel_all()
            logging.info("Summary task queue cancelled during closeEvent.")
        self.regen_worker = None

        # Close tabs from right to left and allow each widget to cleanup resources.
        for i in range(self.central_tabs.count() - 1, -1, -1):
            widget = self.central_tabs.widget(i)
            if widget and hasattr(widget, "cleanup"):
                try:
                    widget.cleanup()
                except Exception:
                    pass
        for host in list(self.floating_chat_hosts):
            widget = host.property("chat_widget")
            if widget and hasattr(widget, "cleanup"):
                try:
                    widget.cleanup()
                except Exception:
                    pass
            self.chat_floating.remove_floating_host(host)

        if self.recorder and self.recorder.is_recording:
            try:
                self.recorder.stop()
                logging.info("Active recorder stopped during closeEvent.")
            except Exception:
                logging.exception("Failed stopping recorder during closeEvent.")

        try:
            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.chat_floating.reposition_floating_chat_bar()
        logging.warning("MainWindow.closeEvent completed.")
