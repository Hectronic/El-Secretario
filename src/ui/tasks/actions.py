"""Persistence mutations initiated by the task board."""

from datetime import date


def create_manual_task(db, *, record_id, filter_date, content, notes, tags, today=None):
    today = today or date.today()
    target_date = filter_date or today.isoformat()
    week_sunday = db._week_sunday(target_date) if hasattr(db, "_week_sunday") else None
    return db.save_task(
        record_id=record_id,
        content=content,
        tags=tags,
        day_date=target_date if filter_date else (today.isoformat() if not record_id else None),
        week_start=week_sunday if not record_id else None,
        notes=notes,
    )


def set_task_completion(db, task_ids, completed_state):
    for task_id in task_ids:
        db.toggle_task_completion(task_id, completed_state)


def delete_tasks(db, task_ids):
    for task_id in task_ids:
        db.delete_task(task_id)


def update_task_details(db, task_id, content, notes, tags):
    """Persist the complete editable task payload from the board dialog."""
    db.update_task_details(task_id, content, notes, tags)


def save_custom_order(db, task_ids):
    """Persist the visible task order when a board is manually reordered."""
    if task_ids:
        db.set_tasks_custom_order(task_ids)
