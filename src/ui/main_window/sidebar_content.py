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
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
)

from src.ui.collection_widget import CollectionWidget
from src.ui.components import RecordingListItemWidget, SidebarChatSessionWidget, SidebarTaskCompactWidget, SummaryListItemWidget
from src.ui.notebook_widget import NotebookWidget
from src.ui.chat_history_widget import ChatHistoryWidget
from src.ui.notebooks_list_widget import NotebooksListWidget
from src.ui.summary_viewer import SummaryViewerWidget
from src.ui.tasks_list_widget import TaskEditDialog
from src.ui.welcome_widget import WelcomeWidget


class SidebarContentCoordinator:
    def __init__(self, window):
        self.window = window

    def load_history(self, tag_filter="All", favorites_only=False):
        self.window.history_list.clear()

        if tag_filter == "All":
            tag_filter = self.window.tag_filter_combo.currentText()
        if not favorites_only:
            favorites_only = self.window.fav_filter_cb.isChecked()

        records = []
        tags_for_query = [tag_filter] if tag_filter != "All" else None

        if self.window.current_week_monday:
            start_date = self.window.current_week_monday.toString("yyyy-MM-dd")
            if self.window.current_date_filter:
                end_date = self.window.current_date_filter
            else:
                end_date = self.window.current_week_monday.addDays(6).toString("yyyy-MM-dd")
            records = self.window.db.fetch_by_date_range(
                start_date,
                end_date,
                tags_for_query,
                favorites_only=favorites_only,
            )
        elif self.window.current_date_filter:
            records = self.window.db.fetch_by_date_range(
                self.window.current_date_filter,
                self.window.current_date_filter,
                tags_for_query,
                favorites_only=favorites_only,
            )
        else:
            records = self.window.db.fetch_all(tag_filter=tag_filter, favorites_only=favorites_only)

        all_items = []
        for record in records:
            if "type" not in record or not record["type"]:
                record["type"] = "recording"
            record["sort_date"] = record["created_at"]
            all_items.append(record)

        if not favorites_only:
            tags_filter = tag_filter if tag_filter != "All" else None

            if self.window.current_week_monday:
                start_date = self.window.current_week_monday.toString("yyyy-MM-dd")
                if self.window.current_date_filter:
                    end_date = self.window.current_date_filter
                else:
                    end_date = self.window.current_week_monday.addDays(6).toString("yyyy-MM-dd")

                week_sunday = self.window.current_week_monday.addDays(6).toString("yyyy-MM-dd")
                weekly_summary = self.window.db.get_weekly_summary(week_sunday, tags_filter)
                if weekly_summary:
                    all_items.append(
                        {
                            "type": "weekly",
                            "week_start": week_sunday,
                            "summary": weekly_summary,
                            "sort_date": week_sunday + " 23:59:59",
                        }
                    )

                daily_sums = self.window.db.fetch_daily_summaries_by_range(start_date, end_date, tags_filter)
                for daily_summary in daily_sums:
                    daily_summary["type"] = "daily"
                    daily_summary["sort_date"] = daily_summary["date"] + " 23:59:59"
                    all_items.append(daily_summary)
            elif self.window.current_date_filter:
                summary_text = self.window.db.get_daily_summary(self.window.current_date_filter, tags_filter)
                if summary_text:
                    all_items.append(
                        {
                            "type": "daily",
                            "date": self.window.current_date_filter,
                            "tags_filter": tags_filter if tags_filter else "",
                            "summary": summary_text,
                            "sort_date": self.window.current_date_filter + " 23:59:59",
                        }
                    )
            else:
                for daily_summary in self.window.db.fetch_daily_summaries(limit=20):
                    daily_summary["type"] = "daily"
                    daily_summary["sort_date"] = daily_summary["date"] + " 23:59:59"
                    all_items.append(daily_summary)

                for weekly_summary in self.window.db.fetch_weekly_summaries(limit=5):
                    weekly_summary["type"] = "weekly"
                    weekly_summary["sort_date"] = weekly_summary["week_start"] + " 23:59:59"
                    all_items.append(weekly_summary)

        all_items.sort(key=lambda item: item["sort_date"], reverse=True)

        for item_data in all_items:
            item = QListWidgetItem(self.window.history_list)
            if item_data["type"] in ["recording", "note"]:
                widget = RecordingListItemWidget(item_data)
                widget.favorite_toggled.connect(
                    lambda checked, r_id=item_data["id"]: self.window.on_favorite_toggled(r_id, checked)
                )
                widget.delete_requested.connect(lambda r_id=item_data["id"]: self.window.delete_recording(r_id))
            else:
                widget = SummaryListItemWidget(item_data)

            item.setSizeHint(widget.sizeHint())
            self.window.history_list.addItem(item)
            self.window.history_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, item_data)

        self.window.filter_history_list(self.window.search_input.text())

        if hasattr(self.window, "welcome_widget") and self.window.welcome_widget:
            try:
                self.window.welcome_widget.load_favorites()
                self.window.welcome_widget.load_today()
            except Exception:
                logging.exception("Failed refreshing welcome widget after history load")

    def refresh_sidebar(self):
        self.window.request_sidebar_reload(include_tags=True, include_history=True)

    def request_sidebar_reload(self, include_tags=False, include_history=True, delay_ms=120):
        self.window._pending_history_reload = self.window._pending_history_reload or include_history
        self.window._pending_tag_reload = self.window._pending_tag_reload or include_tags
        self.window._sidebar_refresh_timer.start(delay_ms)

    def _apply_pending_sidebar_reload(self):
        refresh_tags = self.window._pending_tag_reload
        refresh_history = self.window._pending_history_reload or refresh_tags
        self.window._pending_history_reload = False
        self.window._pending_tag_reload = False

        if refresh_tags:
            self.window.refresh_tag_filter()
        if refresh_history:
            self.window.load_history()
        self.window.refresh_tasks_sidebar()

    def refresh_tag_filter(self):
        current_tag = self.window.tag_filter_combo.currentText()
        self.window.tag_filter_combo.blockSignals(True)
        self.window.tag_filter_combo.clear()
        self.window.tag_filter_combo.addItem("All")

        if self.window.current_date_filter:
            records = self.window.db.fetch_by_date_range(self.window.current_date_filter, self.window.current_date_filter)
            tags = set()
            for record in records:
                if record["tags"]:
                    tags.update([t.strip() for t in record["tags"].split(",") if t.strip()])
            sorted_tags = sorted(list(tags))
        else:
            sorted_tags = self.window.db.get_all_tags()

        self.window.tag_filter_combo.addItems(sorted_tags)

        index = self.window.tag_filter_combo.findText(current_tag)
        if index >= 0:
            self.window.tag_filter_combo.setCurrentIndex(index)
        else:
            self.window.tag_filter_combo.setCurrentIndex(0)
        self.window.tag_filter_combo.blockSignals(False)
        self.window.load_collections()

    def load_collections(self):
        if not hasattr(self.window, "collections_list"):
            return
        self.window.collections_list.clear()
        tags = self.window.db.get_all_tags()
        if not tags:
            self.window.collections_list.addItem("No tags.")
            return
        for tag in tags:
            item = QListWidgetItem(tag)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.window.collections_list.addItem(item)

    def load_notebooks(self):
        self.window.notebooks_list.clear()
        notebooks = self.window.notebook_db.get_notebooks()
        for notebook in notebooks[:5]:
            item = QListWidgetItem(f"📓 {notebook['name']}")
            item.setData(Qt.ItemDataRole.UserRole, notebook["id"])
            self.window.notebooks_list.addItem(item)

    def filter_history_list(self, text):
        for i in range(self.window.history_list.count()):
            item = self.window.history_list.item(i)
            record = item.data(Qt.ItemDataRole.UserRole)
            title = record.get("title", "") or ""
            date = record.get("created_at", "") or ""

            if not text or text.lower() in title.lower() or text.lower() in date.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def on_favorite_toggled(self, record_id, is_favorite):
        self.window.db.toggle_favorite(record_id, is_favorite)

    def delete_recording(self, record_id):
        reply = QMessageBox.question(
            self.window,
            "Delete Recording",
            "Are you sure you want to delete this recording? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        logging.info("delete_recording requested for record_id=%s", record_id)
        filename = self.window.db.delete(record_id)

        if filename:
            try:
                file_path = os.path.join(os.getcwd(), "recordings", filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                logging.exception("Error deleting recording file %s", filename)

        if self.window.rag:
            try:
                logging.info("delete_recording: deleting record_id=%s from RAG", record_id)
                self.window.rag.delete_document(str(record_id))
            except Exception:
                logging.exception("Error deleting record_id=%s from RAG", record_id)

        self.window.load_history()
        self.window._close_recording_tabs(record_id)

    def load_chat_sessions(self):
        self.window.sessions_list.clear()
        sessions = self.window.db.fetch_chat_sessions()
        for session in sessions:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, session)
            self.window.sessions_list.addItem(item)
            widget = SidebarChatSessionWidget(session, parent=self.window.sessions_list)
            widget.expand_requested.connect(lambda _session_id=None: self.window.open_chat_history_tab())
            item.setSizeHint(widget.sizeHint())
            self.window.sessions_list.setItemWidget(item, widget)
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, ChatHistoryWidget):
                widget.set_sessions(sessions)

    def open_collections_list(self):
        for i in range(self.window.central_tabs.count()):
            if self.window.central_tabs.tabText(i) == "Colecciones":
                self.window.central_tabs.setCurrentIndex(i)
                return

        collections_widget = QWidget()
        layout = QVBoxLayout(collections_widget)
        layout.setSpacing(10)

        title = QLabel("<h2>🏷️ Todas las Colecciones</h2>")
        layout.addWidget(title)

        tags = self.window.db.get_all_tags()
        if not tags:
            layout.addWidget(QLabel("No hay colecciones aún. Añade tags a tus grabaciones."))
        else:
            list_widget = QListWidget()
            list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            for tag in tags:
                item = QListWidgetItem(f"🏷️ {tag}")
                item.setData(Qt.ItemDataRole.UserRole, tag)
                list_widget.addItem(item)
            list_widget.itemClicked.connect(lambda item: self.window.open_collection_tab(item.data(Qt.ItemDataRole.UserRole)))
            layout.addWidget(list_widget)

        layout.addStretch()
        index = self.window.central_tabs.addTab(collections_widget, "Colecciones")
        self.window.central_tabs.setCurrentIndex(index)

    def open_notebooks_list(self):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, NotebooksListWidget):
                self.window.central_tabs.setCurrentIndex(i)
                return

        nb_list = NotebooksListWidget(self.window.notebook_db)
        nb_list.notebook_opened.connect(self.window.open_notebook)
        nb_list.chat_requested.connect(self.window.open_notebook_chat)

        index = self.window.central_tabs.addTab(nb_list, "Libretas")
        self.window.central_tabs.setCurrentIndex(index)

    def open_notebook(self, notebook_id, name):
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, NotebookWidget) and widget.notebook_id == notebook_id:
                self.window.central_tabs.setCurrentIndex(i)
                return

        nb_widget = NotebookWidget(self.window.notebook_db, notebook_id, name, self.window.recorder)
        nb_widget.chat_requested.connect(self.window.open_notebook_chat)

        index = self.window.central_tabs.addTab(nb_widget, f"📓 {name}")
        self.window.central_tabs.setCurrentIndex(index)

    def open_notebook_chat(self, notebook_id, notebook_name):
        self.window.open_chat_tab(
            initial_contexts=[{"type": "notebook", "value": notebook_id, "label": notebook_name}]
        )

    def _find_notebook_by_id(self, notebook_id):
        notebooks = self.window.notebook_db.get_notebooks()
        return next((nb for nb in notebooks if nb.get("id") == notebook_id), None)

    def create_notebook(self):
        name, ok = QInputDialog.getText(self.window, "New Notebook", "Notebook Name:")
        if ok and name.strip():
            self.window.notebook_db.create_notebook(name.strip())
            self.window.load_notebooks()

    def rename_notebook(self, notebook_id):
        notebook = self._find_notebook_by_id(notebook_id)
        if not notebook:
            return
        new_name, ok = QInputDialog.getText(self.window, "Rename Notebook", "New Name:", text=notebook["name"])
        if ok and new_name.strip():
            self.window.notebook_db.rename_notebook(notebook_id, new_name.strip())
            self.window.load_notebooks()

    def delete_notebook(self, notebook_id):
        notebook = self._find_notebook_by_id(notebook_id)
        if not notebook:
            return
        reply = QMessageBox.question(
            self.window,
            "Delete Notebook",
            f"Are you sure you want to delete '{notebook['name']}' and all its notes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.window.notebook_db.delete_notebook(notebook_id)
            self.window.load_notebooks()

    def show_notebooks_sidebar_context_menu(self, point):
        item = self.window.notebooks_list.itemAt(point)
        if not item:
            return

        notebook_id = item.data(Qt.ItemDataRole.UserRole)
        notebook_name = item.text().replace("📓 ", "")
        if not isinstance(notebook_id, int):
            return

        menu = QMenu(self.window)
        open_action = menu.addAction("Open")
        chat_action = menu.addAction("Chat")
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.window.notebooks_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.window.open_notebook(notebook_id, notebook_name)
        elif chosen == chat_action:
            self.window.open_notebook_chat(notebook_id, notebook_name)
        elif chosen == rename_action:
            self.rename_notebook(notebook_id)
        elif chosen == delete_action:
            self.delete_notebook(notebook_id)
