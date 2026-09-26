from datetime import datetime, timedelta, timezone

from src.app.scheduling.scheduler import MeetingScheduler
from src.database import DBManager


def meeting_template(**updates):
    values = {
        "title": "Weekly planning",
        "tags": ["Work", "Planning"],
        "timezone": "Europe/Madrid",
        "local_start_time": "10:00",
        "expected_duration_seconds": 3600,
        "reminder_lead_seconds": 600,
        "recurrence_kind": "weekly",
        "recurrence_payload": {"version": 1, "weekdays": [4]},
        "starts_on": "2026-09-25",
    }
    values.update(updates)
    return values


def test_scheduler_materializes_idempotently_notifies_once_and_snoozes(tmp_path):
    now = datetime(2026, 9, 25, 7, 50, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "meetings.sqlite"))
    template_id = db.create_template(meeting_template(), now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)

    due = scheduler.tick(now=now)
    assert len(due["reminders"]) == 1
    occurrence = due["reminders"][0]
    assert occurrence["state"] == "notified"
    assert occurrence["notification_revision"] == 1
    assert scheduler.tick(now=now)["reminders"] == []

    snoozed = scheduler.snooze(occurrence["id"], 5, now=now)
    assert snoozed["state"] == "snoozed"
    assert scheduler.tick(now=now + timedelta(minutes=4))["reminders"] == []
    repeated = scheduler.tick(now=now + timedelta(minutes=5))
    assert len(repeated["reminders"]) == 1
    assert repeated["reminders"][0]["notification_revision"] == 2
    assert db.meetings.list_occurrences(template_id=template_id)[0]["state"] == "notified"


def test_scheduler_dismissal_is_terminal_and_missed_catchup_is_claimed_once(tmp_path):
    now = datetime(2026, 9, 25, 7, 50, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "missed.sqlite"))
    db.create_template(meeting_template(), now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)
    occurrence = scheduler.tick(now=now)["reminders"][0]
    scheduler.dismiss(occurrence["id"], now=now)
    assert scheduler.tick(now=now + timedelta(minutes=11))["reminders"] == []

    missed_template_id = db.create_template(meeting_template(starts_on="2026-09-18", title="Past sync"), now=now)
    after_meeting = now + timedelta(days=7, minutes=11)
    catchup = scheduler.tick(now=after_meeting)["catch_up"]
    assert catchup is not None
    assert catchup["missed_count"] >= 1
    assert scheduler.tick(now=after_meeting)["catch_up"] is None
    missed = next(row for row in db.meetings.list_occurrences(template_id=missed_template_id) if row["state"] == "missed")
    assert scheduler.start(missed["id"], now=after_meeting)["state"] == "started"


def test_restart_backfills_downtime_beyond_the_rolling_catchup_window(tmp_path):
    first_run = datetime(2026, 1, 1, 7, 0, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "long-downtime.sqlite"))
    template_id = db.create_template(meeting_template(
        starts_on="2026-01-01", recurrence_kind="daily",
        recurrence_payload={"version": 1}, local_start_time="10:00",
        reminder_lead_seconds=600,
    ), now=first_run)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: first_run)
    scheduler.tick(now=first_run)
    restarted = first_run + timedelta(days=200)

    result = scheduler.tick(now=restarted)
    missed = db.meetings.list_occurrences(template_id=template_id, states=("missed",))
    assert len(missed) >= 190
    assert result["catch_up"]["missed_count"] == len(missed)
    assert scheduler.tick(now=restarted)["catch_up"] is None


def test_template_pause_resume_edit_and_recording_provenance(tmp_path):
    now = datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "provenance.sqlite"))
    template_id = db.create_template(meeting_template(), now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)
    scheduler.materialize(now=now)
    rows = db.meetings.list_occurrences(template_id=template_id)
    assert rows
    future = rows[0]

    db.set_enabled(template_id, False, now=now)
    assert db.meetings.get_occurrence(future["id"])["state"] == "cancelled"
    db.set_enabled(template_id, True, now=now)
    assert db.meetings.get_occurrence(future["id"])["state"] == "scheduled"

    started = scheduler.start(future["id"], now=now)
    record_id = db.save("meeting.wav", "", 0, title="Weekly planning",
                        meeting_occurrence_id=future["id"], meeting_tags="Work, Personal")
    record = db.fetch_record(record_id)
    linked = db.meetings.get_occurrence(future["id"])
    assert record["meeting_occurrence_id"] == future["id"]
    assert linked["state"] == "completed"
    assert linked["recording_id"] == record_id
    assert linked["title_snapshot"] == "Weekly planning"
    assert linked["tags"] == ["Work", "Personal"]
    event = next(item for item in db.fetch_timeline()
                 if item["event_type"] == "meeting_occurrence" and item["source_id"] == future["id"])
    assert event["metadata"]["recording_id"] == record_id

    changed = meeting_template(title="Revised planning", recurrence_payload={"version": 1, "weekdays": [1]})
    updated = db.update_template(template_id, changed, update_future=True, now=now)
    assert updated["title"] == "Revised planning"
    assert db.meetings.get_occurrence(future["id"])["state"] == "completed"
    assert db.meetings.get_occurrence(future["id"])["title_snapshot"] == "Weekly planning"


def test_confirmed_template_edit_recalculates_same_future_occurrence_without_duplicate(tmp_path):
    now = datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "edit.sqlite"))
    template_id = db.create_template(meeting_template(), now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)
    scheduler.materialize(now=now)
    original = db.meetings.list_occurrences(template_id=template_id)[0]
    changed = meeting_template(title="Changed title", local_start_time="11:00")
    db.update_template(template_id, changed, update_future=True, now=now)
    scheduler.materialize(now=now)
    rows = db.meetings.list_occurrences(template_id=template_id)
    recalculated = next(row for row in rows if row["scheduled_local"].endswith("11:00"))
    assert recalculated["id"] != original["id"]
    assert recalculated["title"] == "Changed title"
    assert db.meetings.get_occurrence(original["id"])["state"] == "cancelled"
    assert len(rows) == len({row["scheduled_local"] for row in rows})


def test_confirmed_title_and_timezone_edit_keeps_local_occurrence_identity(tmp_path):
    now = datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "timezone-edit.sqlite"))
    template_id = db.create_template(meeting_template(), now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)
    scheduler.materialize(now=now)
    original = db.meetings.list_occurrences(template_id=template_id)[0]

    changed = meeting_template(title="Retitled planning")
    db.update_template(template_id, changed, update_future=True, now=now)
    scheduler.materialize(now=now)
    retitled = db.meetings.get_occurrence(original["id"])
    assert retitled["state"] == "scheduled"
    assert retitled["title"] == "Retitled planning"

    changed["timezone"] = "Europe/London"
    db.update_template(template_id, changed, update_future=True, now=now)
    scheduler.materialize(now=now)
    moved = db.meetings.get_occurrence(original["id"])
    assert moved["id"] == original["id"]
    assert moved["timezone"] == "Europe/London"
    assert moved["scheduled_at_utc"] != original["scheduled_at_utc"]
