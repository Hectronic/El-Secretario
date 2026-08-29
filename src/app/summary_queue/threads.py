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

from src.app.summary_queue.rag_reindex import run_rag_reindex
from src.database import DBManager


class RAGReindexThread(QThread):
    """Rebuild RAG entries without blocking the queue manager or UI thread."""

    task_completed = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, db: DBManager, rag_engine, scope: str = "all", parent=None):
        super().__init__(parent)
        self.db = db
        self.rag = rag_engine
        self.scope = (scope or "all").strip().lower()

    def run(self):
        try:
            result = run_rag_reindex(
                self.db,
                self.rag,
                self.scope,
                is_interrupted=self.isInterruptionRequested,
                on_status=self.status_update.emit,
                on_progress=self.progress.emit,
            )
            self.task_completed.emit(result)
        except Exception as e:
            self.error.emit(str(e))
