"""Pure-ish persistence and queue orchestration for summary batches."""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SummaryBatchOptions:
    include_recordings: bool
    include_daily: bool
    include_weekly: bool
    exclude_today: bool
    exclude_current_week: bool


def pending_counts(db, options):
    return (
        len(db.get_records_without_summary()),
        len(db.get_dates_without_summary(exclude_today=options.exclude_today)),
        len(db.get_weeks_without_summary(exclude_current_week=options.exclude_current_week)),
    )


def week_dates(week_sunday):
    sunday = datetime.strptime(week_sunday, "%Y-%m-%d").date()
    monday = sunday - timedelta(days=6)
    return [(monday + timedelta(days=index)).isoformat() for index in range(7)]


def recordings_text(db, recordings):
    return "".join(
        f"\n\n--- Recording: {recording.get('title', 'Untitled')} ({recording.get('created_at', '')}) ---\n"
        f"{db.compose_ai_text(recording.get('transcription', ''), recording.get('recording_notes', ''))}"
        for recording in recordings
    )


def enqueue_missing_summaries(db, task_queue, options):
    """Queue all eligible summary scopes and return their accepted count."""
    accepted = 0
    if options.include_recordings:
        for recording in db.get_records_without_summary():
            text = db.compose_ai_text(recording.get("transcription", ""), recording.get("recording_notes", ""))
            if text.strip() and task_queue.enqueue_recording_summary(
                int(recording["id"]), text, recording.get("title") or f"Recording {recording['id']}", source="batch_summary"
            ):
                accepted += 1
    if options.include_daily:
        for date in db.get_dates_without_summary(exclude_today=options.exclude_today):
            if db.fetch_by_dates([date], None) and task_queue.enqueue_daily_summary(
                {"date": date, "tags_filter": "", "source": "batch_summary"}
            ):
                accepted += 1
    if options.include_weekly:
        for week in db.get_weeks_without_summary(exclude_current_week=options.exclude_current_week):
            text = recordings_text(db, db.fetch_by_dates(week_dates(week), None))
            if text.strip() and task_queue.enqueue_weekly_summary(week, text, "", source="batch_summary"):
                accepted += 1
    return accepted
