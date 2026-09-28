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

import asyncio
import inspect
import threading

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
        self._cancel_requested = threading.Event()
        self._async_loop = None
        self._async_task = None

    def cancel(self):
        """Cancel the in-flight async provider request when supported."""
        self._cancel_requested.set()
        loop = self._async_loop
        task = self._async_task
        if loop is not None and task is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass

    async def _request(self):
        from PyQt6.QtCore import QSettings
        from src.ai_provider import get_ai_provider

        settings = QSettings("Hectronic", "Secretario")
        provider = get_ai_provider(settings)
        chat_async = getattr(provider, "chat_async", None)
        if callable(chat_async) and inspect.iscoroutinefunction(chat_async):
            return await chat_async(self.history, self.query, self.context_text)
        # Compatibility for third-party/test providers that only implement chat.
        return await asyncio.to_thread(provider.chat, self.history, self.query, self.context_text)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._async_loop = loop
        task = loop.create_task(self._request())
        self._async_task = task
        try:
            if self._cancel_requested.is_set():
                task.cancel()
            response = loop.run_until_complete(task)
            self.finished.emit(response)
        except asyncio.CancelledError:
            # Emit an empty completion only to release runtime ownership; its
            # cancelled callback is suppressed by ChatConversationRuntime.
            self.finished.emit("")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._async_task = None
            self._async_loop = None
            asyncio.set_event_loop(None)
            loop.close()
