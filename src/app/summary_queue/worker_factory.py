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

from typing import Any, Callable, Dict

from PyQt6.QtCore import QSettings

from src.app.summary_queue.workers import build_transcription_worker_kwargs
from src.summary_generator import SummaryGenerator
from src.ai_assistant import AIAssistant
from src.app.summary_queue.threads import RAGReindexThread
from src.worker_components.transcriber_thread import TranscriberThread


def build_queue_worker(
    task: Dict,
    *,
    parent,
    db,
    rag_engine,
    on_worker_completed: Callable[..., None],
    on_generator_recording_summary_completed: Callable[..., None],
    on_generator_progress: Callable[..., None],
    on_progress_emit: Callable[[int], None],
    on_status_update: Callable[[str], None],
    settings_cls=QSettings,
    summary_generator_cls=SummaryGenerator,
    transcriber_cls=TranscriberThread,
    rag_reindex_thread_cls=RAGReindexThread,
    ai_assistant_cls=AIAssistant,
):
    task_type = task["type"]
    if task_type == "daily_summary":
        tags_filter = task.get("tags_filter") or None
        worker = summary_generator_cls(
            generate_daily=True,
            generate_weekly=False,
            generate_recordings=True,
            tags_filter=tags_filter,
            specific_dates=[task["date"]],
            exclude_today=False,
            parent=parent,
        )
        worker.recording_summary_completed.connect(on_generator_recording_summary_completed)
        worker.all_tasks_finished.connect(lambda *args: on_worker_completed())
        worker.progress.connect(on_generator_progress)
        return worker

    if task_type == "transcription":
        settings = settings_cls("Hectronic", "Secretario")
        worker = transcriber_cls(**build_transcription_worker_kwargs(settings, task))
        worker.finished.connect(on_worker_completed)
        worker.progress.connect(on_progress_emit)
        worker.status_update.connect(on_status_update)
        return worker

    if task_type == "rag_reindex":
        worker = rag_reindex_thread_cls(
            db,
            rag_engine,
            scope=task.get("reindex_scope", "all"),
            parent=parent,
        )
        worker.task_completed.connect(on_worker_completed)
        worker.progress.connect(on_progress_emit)
        return worker

    worker = ai_assistant_cls("", task_type, task.get("text", ""))
    worker.task_completed.connect(lambda _t_type, result: on_worker_completed(result))
    on_progress_emit(-1)
    return worker
