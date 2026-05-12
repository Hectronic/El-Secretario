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

from PyQt6.QtWidgets import QMessageBox

from src.ui.calendar_widget import CalendarWidget
from src.ui.chat_widget import ChatWidget
from src.ui.chat_history_widget import ChatHistoryWidget
from src.ui.collection_widget import CollectionWidget
from src.ui.note_widget import NoteWidget
from src.ui.summary_viewer import SummaryViewerWidget
from src.ui.tasks_list_widget import TasksListWidget
from src.ui.tools_widget import ToolsWidget


class ContentTabCoordinator:
    """Own note, chat, and summary tab lifecycle."""

    def __init__(self, window):
        self.window = window

    def _find_open_widget(self, widget_type, predicate=None):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, widget_type) and (predicate is None or predicate(widget)):
                return i, widget
        return -1, None

    def open_item_tab(self, record_id):
        record = self.window.db.fetch_record(record_id)
        if not record:
            return
        if record.get("type", "recording") == "note":
            return self.open_note_tab(record_id)
        return self.window.open_recording_tab(record_id)

    def open_note_tab(self, record_id=None):
        if record_id:
            index, widget = self._find_open_widget(
                NoteWidget,
                lambda w: getattr(w, "current_record_id", None) == record_id,
            )
            if widget is not None:
                self.window.central_tabs.setCurrentIndex(index)
                return widget

        note_widget = NoteWidget(self.window.rag, record_id=record_id, task_queue=self.window.summary_task_queue)
        note_widget.note_saved.connect(self.window.load_history)
        note_widget.status_changed.connect(self.window.handle_status_message)
        note_widget.progress_changed.connect(self.window.handle_progress)
        note_widget.close_requested.connect(lambda: self.window.close_tab(self.window.central_tabs.indexOf(note_widget)))

        title = "New Note"
        if record_id:
            record = self.window.db.fetch_record(record_id)
            if record:
                title = record["title"] if record.get("title") else f"Note {record['id']}"

        index = self.window.central_tabs.addTab(note_widget, title)
        self.window.central_tabs.setCurrentIndex(index)
        return note_widget

    def open_chat_tab(self, session_id=None, initial_contexts=None):
        if not self.window.rag:
            QMessageBox.warning(self.window, "RAG Error", "RAG Engine not initialized.")
            return

        if session_id:
            tab_index = self.window._find_chat_tab_index(session_id)
            if tab_index != -1:
                self.window.central_tabs.setCurrentIndex(tab_index)
                self.window._sync_chat_context_section(self.window.central_tabs.widget(tab_index))
                return self.window.central_tabs.widget(tab_index)
            floating_host = self.window._find_floating_chat_host(session_id)
            if floating_host is not None:
                chat_widget = floating_host.property("chat_widget")
                self.window.dock_chat_widget_to_tab(chat_widget)
                return chat_widget

        chat_widget = ChatWidget(self.window.rag, session_id, self.window, initial_contexts=initial_contexts)
        self.window._connect_chat_widget(chat_widget)
        title = self.window._tab_title_for_chat(chat_widget)
        index = self.window.central_tabs.addTab(chat_widget, title)
        self.window.central_tabs.setCurrentIndex(index)
        self.window._set_tab_action_buttons(chat_widget)
        self.window._sync_chat_context_section(chat_widget)
        return chat_widget

    def open_floating_chat(self, session_id=None, initial_contexts=None):
        chat_widget = self.open_chat_tab(session_id=session_id, initial_contexts=initial_contexts)
        if isinstance(chat_widget, ChatWidget):
            self.window.float_chat_widget(chat_widget)
        return chat_widget

    def open_chat_tab_from_current_context(self):
        tag = self.window.tag_filter_combo.currentText() if hasattr(self.window, "tag_filter_combo") else "All"
        tags_str = "" if not tag or tag == "All" else tag
        chat_widget = self.open_chat_tab(None)
        if isinstance(chat_widget, ChatWidget):
            chat_widget.update_from_global_selection(
                self.window.current_week_monday,
                self.window.current_date_filter,
                tags_str,
            )

    def open_chat_tab_with_filters(self, date_str, tags):
        contexts = []
        if date_str:
            contexts.append({"type": "date", "value": date_str, "label": date_str})
        if tags:
            for tag in tags:
                contexts.append({"type": "tag", "value": tag, "label": tag})
        self.open_chat_tab(initial_contexts=contexts)

    def open_chat_with_contexts(self, contexts, floating=False):
        normalized = list(contexts or [])
        if floating:
            return self.open_floating_chat(initial_contexts=normalized)
        return self.open_chat_tab(initial_contexts=normalized)

    def open_chat_history_tab(self):
        index, widget = self._find_open_widget(ChatHistoryWidget)
        if widget is not None:
            self.window.central_tabs.setCurrentIndex(index)
            return widget

        history_widget = ChatHistoryWidget(self.window)
        history_widget.session_requested.connect(self.window.open_chat_tab)
        history_widget.session_delete_requested.connect(self.window.delete_chat_session_by_id)
        history_widget.set_sessions(self.window.db.fetch_chat_sessions())
        index = self.window.central_tabs.addTab(history_widget, "💬 Chat History")
        self.window.central_tabs.setCurrentIndex(index)
        return history_widget

    def open_summary_tab(self, summary_data):
        def _same_summary(widget):
            w_data = widget.summary_data
            if w_data.get("type") != summary_data.get("type"):
                return False
            if w_data.get("type") == "daily":
                return (
                    w_data.get("date") == summary_data.get("date")
                    and (w_data.get("tags_filter") or "") == (summary_data.get("tags_filter") or "")
                )
            return w_data.get("type") == "weekly" and w_data.get("week_start") == summary_data.get("week_start")

        index, widget = self._find_open_widget(SummaryViewerWidget, _same_summary)
        if widget is not None:
            self.window.central_tabs.setCurrentIndex(index)
            return

        viewer = SummaryViewerWidget(summary_data, db=self.window.db, task_queue=self.window.summary_task_queue)
        viewer.regenerate_requested.connect(self.window.regenerate_summary)
        viewer.open_recording_requested.connect(self.window.open_recording_tab)
        viewer.start_chat_requested.connect(self.window.open_chat_tab_with_filters)
        viewer.start_chat_contexts_requested.connect(self.window.open_chat_with_contexts)

        type_ = summary_data.get("type")
        title = f"📅 {summary_data.get('date')}" if type_ == "daily" else f"📅 Week ending {summary_data.get('week_start')}"
        index = self.window.central_tabs.addTab(viewer, title)
        self.window.central_tabs.setCurrentIndex(index)

    def open_tools_tab(self, tab_index=0):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, ToolsWidget):
                self.window.central_tabs.setCurrentIndex(i)
                widget.show_tab(tab_index)
                return

        tools_widget = ToolsWidget(
            self.window.db,
            self.window.notebook_db,
            task_queue=self.window.summary_task_queue,
        )
        index = self.window.central_tabs.addTab(tools_widget, "⚙️ Tools")
        self.window.central_tabs.setCurrentIndex(index)
        tools_widget.show_tab(tab_index)

    def open_tasks_tab(self, create_new=False):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, TasksListWidget):
                self.window.central_tabs.setCurrentIndex(i)
                tag = self.window.tag_filter_combo.currentText()
                tags_filter = tag if tag != "All" else None
                widget.set_global_filters(
                    self.window.current_week_monday,
                    self.window.current_date_filter,
                    tags_filter,
                )
                widget.refresh()
                if create_new:
                    widget.open_create_dialog()
                return

        tasks_widget = TasksListWidget(self.window.db, limit=None)
        tasks_widget.open_recording_requested.connect(self.window.open_recording_tab)
        tasks_widget.tasks_changed.connect(self.window.refresh_tasks_sidebar)
        tag = self.window.tag_filter_combo.currentText()
        tags_filter = tag if tag != "All" else None
        tasks_widget.set_global_filters(
            self.window.current_week_monday,
            self.window.current_date_filter,
            tags_filter,
        )
        index = self.window.central_tabs.addTab(tasks_widget, "✅ Tasks")
        self.window.central_tabs.setCurrentIndex(index)
        if create_new:
            tasks_widget.open_create_dialog()

    def open_collection_tab(self, tag):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, CollectionWidget) and widget.tag == tag:
                self.window.central_tabs.setCurrentIndex(i)
                return

        col_widget = CollectionWidget(tag)
        col_widget.open_recording.connect(self.window.open_recording_tab)
        col_widget.start_chat.connect(self.window.open_collection_chat)
        index = self.window.central_tabs.addTab(col_widget, f"Collection: {tag}")
        self.window.central_tabs.setCurrentIndex(index)

    def open_calendar_tab(self):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, CalendarWidget):
                self.window.central_tabs.setCurrentIndex(i)
                widget.set_selection(self.window.current_week_monday, self.window.current_date_filter)
                return

        tab = CalendarWidget(self.window, task_queue=self.window.summary_task_queue)
        tab.start_chat_requested.connect(self.window.open_chat_tab_with_filters)
        tab.selection_changed.connect(self.window.on_tab_selection_sync)
        tag = self.window.tag_filter_combo.currentText()
        tab.set_selection(
            self.window.current_week_monday,
            self.window.current_date_filter,
            tag if tag != "All" else None,
        )
        index = self.window.central_tabs.addTab(tab, "Week Details")
        self.window.central_tabs.setCurrentIndex(index)
