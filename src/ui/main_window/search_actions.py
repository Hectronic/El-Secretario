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

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.ui.search_results_widget import SearchResultsWidget
from src.worker_components.threads import SearchThread


class SearchActionsCoordinator:
    """Own welcome search flow and search-tab opening behavior."""

    def __init__(self, window):
        self.window = window

    def perform_welcome_search(self, query):
        if not self.window.rag:
            QMessageBox.warning(self.window, "RAG Error", "RAG Engine not initialized.")
            return

        if not query:
            return

        if self.window.search_thread and self.window.search_thread.isRunning():
            return
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        self.window.search_thread = SearchThread(self.window.rag, query)
        self.window.search_thread.finished.connect(
            lambda results: self.on_search_finished_new_tab(results, query)
        )
        self.window.search_thread.error.connect(self.on_search_error)
        self.window.search_thread.start()

    def on_search_finished_new_tab(self, results, query):
        QApplication.restoreOverrideCursor()
        self.window.search_thread = None

        search_widget = SearchResultsWidget(query)
        search_widget.display_results(results)
        search_widget.result_clicked.connect(self.window.open_recording_tab)

        index = self.window.central_tabs.addTab(search_widget, f"Search: {query}")
        self.window.central_tabs.setCurrentIndex(index)

    def on_search_error(self, error_message):
        QApplication.restoreOverrideCursor()
        self.window.search_thread = None
        QMessageBox.critical(
            self.window,
            "Search Error",
            f"An error occurred during search: {error_message}",
        )
