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

from typing import Any, Dict, Optional, Tuple


def normalize_source(source: Optional[str], default: str = "manual") -> str:
    value = str(source or "").strip().lower().replace(" ", "_")
    return value or default


def task_key(task: Dict) -> Tuple[Any, ...]:
    return (
        task.get("type", ""),
        task.get("date", ""),
        task.get("record_id", ""),
        task.get("tags_filter", ""),
        task.get("audio_path", ""),
        task.get("reindex_scope", ""),
    )


def build_daily_summary_task(summary_data: Dict) -> Optional[Dict]:
    date = summary_data.get("date")
    if not date:
        return None
    return {
        "type": "daily_summary",
        "date": date,
        "tags_filter": summary_data.get("tags_filter") or "",
        "source": normalize_source(summary_data.get("source"), "manual"),
    }


def build_recording_summary_task(record_id: int, text: str, title: str, source: str = "manual") -> Dict:
    return {
        "type": "summary",
        "record_id": record_id,
        "text": text,
        "title": title,
        "source": normalize_source(source, "manual"),
    }


def build_weekly_summary_task(
    week_sunday: str,
    text: str,
    tags_filter: str = "",
    source: str = "manual",
) -> Dict:
    return {
        "type": "weekly_summary",
        "date": week_sunday,
        "text": text,
        "tags_filter": tags_filter,
        "source": normalize_source(source, "manual"),
    }


def build_task_extraction_task(
    record_id: int,
    text: str = "",
    tags: str = "",
    title: str = "",
    force: bool = False,
    source: str = "manual",
) -> Dict:
    resolved_title = (title or f"Recording {record_id}").strip()
    return {
        "type": "task_extraction",
        "record_id": record_id,
        "text": text,
        "tags": tags,
        "title": resolved_title,
        "force": bool(force),
        "source": normalize_source(source, "manual"),
    }


def build_transcription_task(
    record_id: int,
    audio_path: str,
    model_size: str = "base",
    language: str = None,
    diarization: bool = False,
    title: str = "",
    source: str = "manual",
) -> Dict:
    return {
        "type": "transcription",
        "record_id": record_id,
        "audio_path": audio_path,
        "model_size": model_size,
        "language": language,
        "diarization": diarization,
        "title": title,
        "source": normalize_source(source, "manual"),
    }


def build_rag_reindex_task(scope: str = "all", source: str = "manual") -> Dict:
    normalized_scope = (scope or "all").strip().lower()
    if normalized_scope not in {"all", "missing"}:
        normalized_scope = "all"
    return {
        "type": "rag_reindex",
        "title": "RAG Reindex",
        "reindex_scope": normalized_scope,
        "source": normalize_source(source, "manual"),
    }

