"""Task-board filter normalization and persistence queries."""

from datetime import date, timedelta

from PyQt6.QtCore import QDate


def date_to_iso(value):
    if value is None:
        return None
    if isinstance(value, QDate):
        return value.toString("yyyy-MM-dd") if value.isValid() else None
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def resolve_global_date_range(week_monday=None, date_filter=None):
    """Return the normalized inclusive range represented by calendar context."""
    if week_monday:
        start_date = date_to_iso(week_monday)
        if date_filter:
            return start_date, date_to_iso(date_filter)
        if isinstance(week_monday, QDate):
            return start_date, week_monday.addDays(6).toString("yyyy-MM-dd")
        if isinstance(week_monday, date):
            return start_date, (week_monday + timedelta(days=6)).isoformat()
        return start_date, start_date
    if date_filter:
        normalized = date_to_iso(date_filter)
        return normalized, normalized
    return None, None


def resolve_effective_tags_filter(
    *, snapshot_mode, global_start_date, global_end_date, global_tags_filter, local_tag
):
    if (snapshot_mode and global_tags_filter) or (global_start_date and global_end_date):
        return global_tags_filter
    return local_tag if local_tag and local_tag != "All" else None


def task_matches_tag(task, tags_filter):
    if not tags_filter:
        return True
    if isinstance(task.get("record_id"), int):
        tags_text = str(task.get("record_tags") or task.get("tags") or "")
    else:
        tags_text = str(task.get("tags") or task.get("record_tags") or "")
    return tags_filter in [tag.strip() for tag in tags_text.split(",") if tag.strip()]


def fetch_task_board_tasks(
    db,
    *,
    snapshot_mode,
    snapshot_ref,
    record_id,
    filter_date,
    limit,
    global_start_date,
    global_end_date,
    tags_filter,
    order_mode,
    include_completed,
):
    """Load the task collection appropriate to one visible board state."""
    if snapshot_mode in ("day_created", "day_completed"):
        day_ref = snapshot_ref or filter_date
        snapshot = db.get_daily_task_snapshot(day_ref, tags_filter) if day_ref else {}
        key = "created_this_day" if snapshot_mode == "day_created" else "completed_this_day"
        return snapshot.get(key, [])
    if snapshot_mode in ("week_created", "week_completed", "week_pending_before"):
        snapshot = db.get_weekly_task_snapshot(snapshot_ref, tags_filter) if snapshot_ref else {}
        keys = {
            "week_created": "created_this_week",
            "week_completed": "completed_this_week",
            "week_pending_before": "pending_from_before",
        }
        return snapshot.get(keys[snapshot_mode], [])
    if record_id:
        return [task for task in db.get_tasks_by_record(record_id) if task_matches_tag(task, tags_filter)]
    if filter_date:
        return db.get_tasks_by_date(filter_date, tags_filter, order_mode=order_mode)
    if global_start_date and global_end_date:
        return db.get_tasks_by_date_range(
            global_start_date,
            global_end_date,
            tags_filter=tags_filter,
            order_mode=order_mode,
            include_completed=include_completed,
        )
    tasks = db.get_tasks_for_board(
        order_mode=order_mode,
        include_completed=include_completed,
        limit=limit,
    )
    return [task for task in tasks if task_matches_tag(task, tags_filter)]
