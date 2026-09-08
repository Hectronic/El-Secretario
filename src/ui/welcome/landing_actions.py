"""Landing search, favorites, and today-list interaction orchestration."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidgetItem

from src.ui.welcome.landing_data import fetch_favorites_page, fetch_today_items, search_result_items


class WelcomeLandingActions:
    def __init__(self, widget):
        self.widget = widget

    def trigger_search(self):
        query = self.widget.search_input.text().strip()
        if query:
            self.widget.search_triggered.emit(query)

    def display_results(self, results):
        self.widget.results_list.clear()
        if not results:
            self.widget.results_list.hide()
            return
        self.widget.results_list.show()
        self._populate(self.widget.results_list, search_result_items(results))

    def load_favorites(self):
        widget = self.widget
        widget.fav_list.clear()
        page = fetch_favorites_page(widget.db, page=widget.favorites_page)
        widget.favorites_page = page.page
        self._populate(widget.fav_list, page.items)
        widget.prev_btn.setEnabled(page.has_previous)
        widget.next_btn.setEnabled(page.has_next)

    def previous_page(self):
        if self.widget.favorites_page > 0:
            self.widget.favorites_page -= 1
            self.load_favorites()

    def next_page(self):
        self.widget.favorites_page += 1
        self.load_favorites()

    def load_today(self):
        self.widget.today_list.clear()
        self._populate(self.widget.today_list, fetch_today_items(self.widget.db))

    def open_item(self, item):
        self.widget.result_clicked.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    @staticmethod
    def _populate(list_widget, records):
        for record in records:
            item = QListWidgetItem(record.text)
            item.setData(Qt.ItemDataRole.UserRole, record.record_id)
            list_widget.addItem(item)
