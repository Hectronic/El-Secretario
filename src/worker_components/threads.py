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

from PyQt6.QtCore import QThread, pyqtSignal


class SearchThread(QThread):
    """Run RAG search outside the UI thread and return a list of matches."""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, rag_engine, query):
        super().__init__()
        self.rag = rag_engine
        self.query = query

    def run(self):
        try:
            results = self.rag.search(self.query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ChatThread(QThread):
    """Run chat completion outside the UI thread using the configured provider.

    ``api_key`` and ``model_name`` are kept in the constructor for compatibility
    with older callers; provider selection now comes from ``QSettings``.
    """

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, query, context_text, history=None, model_name="gemini-3-flash-preview"):
        super().__init__()
        self.query = query
        self.context_text = context_text
        self.history = history or []
        self._legacy_api_key = api_key
        self._legacy_model_name = model_name

    def run(self):
        try:
            from PyQt6.QtCore import QSettings
            from src.ai_provider import get_ai_provider

            settings = QSettings("Hectronic", "Secretario")
            provider = get_ai_provider(settings)
            response = provider.chat(self.history, self.query, self.context_text)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))
