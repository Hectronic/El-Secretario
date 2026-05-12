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
from src.app.summary_queue.history import QueueHistory
from src.app.summary_queue.helpers import (
    parse_task_extraction_result,
    read_audio_duration_seconds,
)
from src.app.summary_queue.rag_reindex import (
    build_rag_metadata,
    collect_reindex_candidates,
    is_indexed_in_rag,
    normalize_reindex_scope,
    run_rag_reindex,
)
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
from src.app.summary_queue.workers import build_transcription_worker_kwargs

__all__ = [
    "build_rag_reindex_status",
    "build_daily_summary_task",
    "build_rag_metadata",
    "build_rag_reindex_task",
    "build_recording_summary_task",
    "build_task_extraction_task",
    "build_transcription_task",
    "build_transcription_worker_kwargs",
    "build_weekly_summary_task",
    "collect_reindex_candidates",
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
    "read_audio_duration_seconds",
    "run_rag_reindex",
    "should_chain_summary_after_transcription",
    "task_key",
]
