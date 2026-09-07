"""History, filter, favourite, and deletion behavior for the main sidebar."""

import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem, QMessageBox

from src.ui.components import RecordingListItemWidget, SummaryListItemWidget


class SidebarHistoryCoordinator:
    """Own persisted recording/summary history rendering and its filters."""

    def __init__(self, window):
        self.window = window

    def load_history(self, tag_filter="All", favorites_only=False):
        window = self.window
        window.history_list.clear()
        if tag_filter == "All":
            tag_filter = window.tag_filter_combo.currentText()
        if not favorites_only:
            favorites_only = window.fav_filter_cb.isChecked()
        tags_for_query = [tag_filter] if tag_filter != "All" else None
        if window.current_week_monday:
            start_date = window.current_week_monday.toString("yyyy-MM-dd")
            end_date = window.current_date_filter or window.current_week_monday.addDays(6).toString("yyyy-MM-dd")
            records = window.db.fetch_by_date_range(start_date, end_date, tags_for_query, favorites_only=favorites_only)
        elif window.current_date_filter:
            records = window.db.fetch_by_date_range(window.current_date_filter, window.current_date_filter, tags_for_query, favorites_only=favorites_only)
        else:
            records = window.db.fetch_all(tag_filter=tag_filter, favorites_only=favorites_only)
        all_items = []
        for record in records:
            item_data = dict(record)
            item_data["type"] = item_data.get("type") or "recording"
            item_data["sort_date"] = item_data["created_at"]
            all_items.append(item_data)
        if not favorites_only:
            all_items.extend(self._summary_items(tag_filter))
        for item_data in sorted(all_items, key=lambda item: item["sort_date"], reverse=True):
            item = QListWidgetItem(window.history_list)
            if item_data["type"] in {"recording", "note"}:
                widget = RecordingListItemWidget(item_data)
                widget.favorite_toggled.connect(lambda checked, r_id=item_data["id"]: window.on_favorite_toggled(r_id, checked))
                widget.delete_requested.connect(lambda r_id=item_data["id"]: window.delete_recording(r_id))
            else:
                widget = SummaryListItemWidget(item_data)
            item.setSizeHint(widget.sizeHint())
            window.history_list.addItem(item)
            window.history_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, item_data)
        window.filter_history_list(window.search_input.text())
        if getattr(window, "welcome_widget", None):
            try:
                window.welcome_widget.load_favorites()
                window.welcome_widget.load_today()
            except Exception:
                logging.exception("Failed refreshing welcome widget after history load")

    def _summary_items(self, tag_filter):
        window = self.window
        tags_filter = tag_filter if tag_filter != "All" else None
        items = []
        if window.current_week_monday:
            start_date = window.current_week_monday.toString("yyyy-MM-dd")
            end_date = window.current_date_filter or window.current_week_monday.addDays(6).toString("yyyy-MM-dd")
            week_sunday = window.current_week_monday.addDays(6).toString("yyyy-MM-dd")
            weekly_summary = window.db.get_weekly_summary(week_sunday, tags_filter)
            if weekly_summary:
                items.append({"type": "weekly", "week_start": week_sunday, "summary": weekly_summary, "sort_date": week_sunday + " 23:59:59"})
            for summary in window.db.fetch_daily_summaries_by_range(start_date, end_date, tags_filter):
                item = dict(summary, type="daily")
                item["sort_date"] = item["date"] + " 23:59:59"
                items.append(item)
        elif window.current_date_filter:
            summary_text = window.db.get_daily_summary(window.current_date_filter, tags_filter)
            if summary_text:
                items.append({"type": "daily", "date": window.current_date_filter, "tags_filter": tags_filter or "", "summary": summary_text, "sort_date": window.current_date_filter + " 23:59:59"})
        else:
            for summary in window.db.fetch_daily_summaries(limit=20):
                item = dict(summary, type="daily")
                item["sort_date"] = item["date"] + " 23:59:59"
                items.append(item)
            for summary in window.db.fetch_weekly_summaries(limit=5):
                item = dict(summary, type="weekly")
                item["sort_date"] = item["week_start"] + " 23:59:59"
                items.append(item)
        return items

    def refresh_sidebar(self):
        self.window.request_sidebar_reload(include_tags=True, include_history=True)

    def request_sidebar_reload(self, include_tags=False, include_history=True, delay_ms=120):
        window = self.window
        window._pending_history_reload = window._pending_history_reload or include_history
        window._pending_tag_reload = window._pending_tag_reload or include_tags
        window._sidebar_refresh_timer.start(delay_ms)

    def apply_pending_sidebar_reload(self):
        window = self.window
        refresh_tags = window._pending_tag_reload
        refresh_history = window._pending_history_reload or refresh_tags
        window._pending_history_reload = False
        window._pending_tag_reload = False
        if refresh_tags:
            window.refresh_tag_filter()
        if refresh_history:
            window.load_history()
        window.refresh_tasks_sidebar()

    def refresh_tag_filter(self):
        window = self.window
        current_tag = window.tag_filter_combo.currentText()
        window.tag_filter_combo.blockSignals(True)
        window.tag_filter_combo.clear()
        window.tag_filter_combo.addItem("All")
        if window.current_date_filter:
            records = window.db.fetch_by_date_range(window.current_date_filter, window.current_date_filter)
            tags = {tag.strip() for record in records for tag in (record.get("tags") or "").split(",") if tag.strip()}
            sorted_tags = sorted(tags)
        else:
            sorted_tags = window.db.get_all_tags()
        window.tag_filter_combo.addItems(sorted_tags)
        index = window.tag_filter_combo.findText(current_tag)
        window.tag_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        window.tag_filter_combo.blockSignals(False)
        window.load_collections()

    def filter_history_list(self, text):
        for index in range(self.window.history_list.count()):
            item = self.window.history_list.item(index)
            record = item.data(Qt.ItemDataRole.UserRole)
            title = record.get("title", "") or ""
            date = record.get("created_at", "") or ""
            item.setHidden(bool(text) and text.lower() not in title.lower() and text.lower() not in date.lower())

    def on_favorite_toggled(self, record_id, is_favorite):
        self.window.db.toggle_favorite(record_id, is_favorite)

    def delete_recording(self, record_id):
        reply = QMessageBox.question(self.window, "Delete Recording", "Are you sure you want to delete this recording? This cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        filename = self.window.db.delete(record_id)
        if filename:
            try:
                path = os.path.join(os.getcwd(), "recordings", filename)
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                logging.exception("Error deleting recording file %s", filename)
        if self.window.rag:
            try:
                self.window.rag.delete_document(str(record_id))
            except Exception:
                logging.exception("Error deleting record_id=%s from RAG", record_id)
        self.window.load_history()
        self.window._close_recording_tabs(record_id)
