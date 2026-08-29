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
# along with this program.  See <https://www.gnu.org/licenses/>.

from typing import Dict, Mapping, Sequence, Any


def format_task_display(task: Mapping) -> str:
    t_type = task.get("type", "Unknown")
    label = f"[{str(t_type).replace('_', ' ').capitalize()}] "

    if t_type == "summary":
        label += task.get("title", "Unknown Recording")
    elif t_type == "task_extraction":
        label += f"Tasks for: {task.get('title', 'Unknown')}"
    elif t_type == "transcription":
        label += f"Transcription: {task.get('title', 'Unknown')}"
    elif t_type == "daily_summary":
        label += f"Day: {task.get('date', 'Unknown')}"
    elif t_type == "weekly_summary":
        label += f"Week: {task.get('date', 'Unknown')}"
    elif t_type == "rag_reindex":
        scope = task.get("reindex_scope", "all")
        label += "Rebuild semantic index (missing only)" if scope == "missing" else "Rebuild semantic index (all)"

    tags = task.get("tags_filter") or task.get("tags")
    if tags:
        label += f" ({tags})"

    source = task.get("source")
    if source:
        label += f" · {str(source).replace('_', ' ')}"
    return label


def format_history_entry(entry: Mapping) -> str:
    when = entry.get("time") or "--:--:--"
    event = (entry.get("event") or "info").replace("_", " ").capitalize()
    task = entry.get("task") or {}
    message = entry.get("message") or ""
    base = f"[{when}] {event}: {format_task_display(task)}"
    if message:
        base += f" - {message}"
    return base


def format_metrics_label(stats: Mapping[str, int] | None) -> str:
    data: Dict[str, int] = dict(stats or {})
    return (
        "Metrics: "
        f"running={int(data.get('running', 0))} "
        f"pending={int(data.get('pending', 0))} "
        f"queued={int(data.get('queued', 0))} "
        f"finished={int(data.get('finished', 0))} "
        f"failed={int(data.get('failed', 0))} "
        f"skipped={int(data.get('skipped', 0))}"
    )


def format_wait_label(is_waiting: bool, seconds_left: int, description: str) -> str:
    if not is_waiting:
        return "Wait: none"
    if description:
        return f"Wait: {int(seconds_left)}s - {description}"
    return f"Wait: {int(seconds_left)}s"


def format_current_task_label(task: Mapping | None) -> str:
    if not task:
        return "None (Idle)"
    return format_task_display(task)


def normalize_status_message(message: str) -> str:
    msg = str(message or "").strip()
    if not msg:
        return ""
    return f"Status: {msg}"


def build_queue_view_snapshot(
    *,
    current_task: Mapping | None,
    pending_tasks: Sequence[Mapping[str, Any]],
    is_waiting: bool,
    seconds_left: int,
    wait_description: str,
) -> Dict[str, Any]:
    return {
        "current_label": format_current_task_label(current_task),
        "has_current_task": bool(current_task),
        "wait_label": format_wait_label(is_waiting, seconds_left, wait_description),
        "pending_labels": [format_task_display(task) for task in pending_tasks],
    }


def build_queue_management_snapshot(
    *,
    current_task: Mapping | None,
    pending_tasks: Sequence[Mapping[str, Any]],
    is_waiting: bool,
    seconds_left: int,
    wait_description: str,
    history_entries: Sequence[Mapping[str, Any]] | None,
    runtime_stats: Mapping[str, int] | None,
    fallback_running: int = 0,
    fallback_pending: int = 0,
) -> Dict[str, Any]:
    queue_snapshot = build_queue_view_snapshot(
        current_task=current_task,
        pending_tasks=pending_tasks,
        is_waiting=is_waiting,
        seconds_left=seconds_left,
        wait_description=wait_description,
    )
    stats = runtime_stats if runtime_stats is not None else {
        "running": int(fallback_running),
        "pending": int(fallback_pending),
    }
    return {
        **queue_snapshot,
        "metrics_label": format_metrics_label(stats),
        "history_labels": [format_history_entry(entry) for entry in (history_entries or [])],
    }


def map_progress_state(value: int) -> Dict[str, int | str]:
    if value == -1:
        return {"mode": "indeterminate", "min": 0, "max": 0, "value": 0, "format": "Working..."}
    if value == -2:
        return {"mode": "idle", "min": 0, "max": 1, "value": 0, "format": "Idle"}
    if value < 0:
        return {"mode": "ignore", "min": 0, "max": 0, "value": 0, "format": ""}
    int_value = int(value)
    return {"mode": "determinate", "min": 0, "max": 100, "value": int_value, "format": f"{int_value}%"}
