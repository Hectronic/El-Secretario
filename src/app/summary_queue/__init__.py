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

from src.app.summary_queue.completion import (
    build_rag_reindex_status,
    handle_worker_completion,
    persist_summary_result,
    persist_task_extraction_result,
    persist_transcription_result,
    persist_weekly_summary_result,
    should_chain_summary_after_transcription,
)
from src.app.summary_queue.actions import QueueActionCoordinator
from src.app.summary_queue.history import QueueHistory
from src.app.summary_queue.helpers import (
    parse_task_extraction_result,
    read_audio_duration_seconds,
)
from src.app.summary_queue.presentation import (
    build_queue_management_snapshot,
    build_queue_view_snapshot,
    format_current_task_label,
    format_history_entry,
    format_metrics_label,
    format_task_display,
    format_wait_label,
    map_progress_state,
    normalize_status_message,
)
from src.app.summary_queue.rag_reindex import (
    build_rag_metadata,
    collect_reindex_candidates,
    is_indexed_in_rag,
    normalize_reindex_scope,
    run_rag_reindex,
)
from src.app.summary_queue.runtime import (
    build_retry_wait_state,
    cleanup_between_jobs,
    collect_runtime_stats,
    stop_worker,
)
from src.app.summary_queue.worker_factory import build_queue_worker
from src.app.summary_queue.worker_signals import connect_queue_worker_signals
from src.app.summary_queue.worker_lifecycle import start_queue_worker_lifecycle
from src.app.summary_queue.tasks import (
    build_daily_summary_task,
    build_rag_reindex_task,
    build_recording_summary_task,
    build_task_extraction_task,
    build_transcription_task,
    build_weekly_summary_task,
    normalize_source,
    task_key,
)
from src.app.summary_queue.threads import RAGReindexThread
from src.app.summary_queue.workers import build_transcription_worker_kwargs

__all__ = [
    "build_rag_reindex_status",
    "build_queue_worker",
    "connect_queue_worker_signals",
    "start_queue_worker_lifecycle",
    "build_queue_view_snapshot",
    "build_queue_management_snapshot",
    "build_daily_summary_task",
    "build_rag_metadata",
    "build_rag_reindex_task",
    "build_recording_summary_task",
    "build_retry_wait_state",
    "build_task_extraction_task",
    "build_transcription_task",
    "build_transcription_worker_kwargs",
    "build_weekly_summary_task",
    "collect_reindex_candidates",
    "collect_runtime_stats",
    "cleanup_between_jobs",
    "QueueActionCoordinator",
    "format_history_entry",
    "format_metrics_label",
    "format_task_display",
    "format_wait_label",
    "map_progress_state",
    "format_current_task_label",
    "normalize_status_message",
    "handle_worker_completion",
    "is_indexed_in_rag",
    "normalize_source",
    "normalize_reindex_scope",
    "parse_task_extraction_result",
    "persist_summary_result",
    "persist_task_extraction_result",
    "persist_transcription_result",
    "persist_weekly_summary_result",
    "QueueHistory",
    "RAGReindexThread",
    "read_audio_duration_seconds",
    "run_rag_reindex",
    "should_chain_summary_after_transcription",
    "stop_worker",
    "task_key",
]
