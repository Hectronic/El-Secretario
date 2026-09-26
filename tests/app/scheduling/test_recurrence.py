from datetime import date, datetime, timezone

import pytest

from src.app.scheduling.recurrence import expand_occurrences, next_occurrences, resolve_local_datetime, validate_template


def template(**updates):
    result = {
        "title": "Weekly sync",
        "tags": "Work, planning, work",
        "timezone": "Europe/Madrid",
        "local_start_time": "09:00",
        "expected_duration_seconds": 3600,
        "reminder_lead_seconds": 600,
        "recurrence_kind": "weekly",
        "recurrence_payload": {"version": 1, "weekdays": [0]},
        "starts_on": "2026-09-21",
        "ends_on": None,
        "occurrence_limit": None,
    }
    result.update(updates)
    return result


def test_weekly_next_occurrences_are_local_and_deduplicated():
    rows = next_occurrences(template(), datetime(2026, 9, 21, 6, tzinfo=timezone.utc), 3)
    assert [row["scheduled_local"] for row in rows] == [
        "2026-09-21T09:00", "2026-09-28T09:00", "2026-10-05T09:00"
    ]
    assert rows[0]["scheduled_at_utc"] == "2026-09-21T07:00:00Z"


def test_monthly_invalid_short_month_day_is_skipped_and_occurrence_count_applies():
    item = template(
        starts_on="2026-01-01", recurrence_kind="monthly",
        recurrence_payload={"version": 1, "day": 31}, occurrence_limit=3,
    )
    rows = expand_occurrences(
        item, datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 5, 1, tzinfo=timezone.utc)
    )
    assert [row["local_date"] for row in rows] == ["2026-01-31", "2026-03-31"]


def test_dst_ambiguous_time_uses_first_fold():
    resolved = resolve_local_datetime(date(2026, 10, 25), "02:30", "Europe/Madrid")
    assert resolved.fold == 0
    assert resolved.utcoffset().total_seconds() == 7200
    assert resolved.astimezone(timezone.utc).isoformat() == "2026-10-25T00:30:00+00:00"


def test_dst_missing_time_moves_to_first_valid_local_instant():
    resolved = resolve_local_datetime(date(2026, 3, 29), "02:30", "Europe/Madrid")
    assert resolved.replace(tzinfo=None).isoformat(timespec="minutes") == "2026-03-29T03:00"
    assert resolved.astimezone(timezone.utc).isoformat() == "2026-03-29T01:00:00+00:00"


def test_recurrence_payload_and_required_fields_are_validated():
    normalized = validate_template(template())
    assert normalized["tags"] == ["Work", "planning"]
    with pytest.raises(ValueError, match="weekday"):
        validate_template(template(recurrence_payload={"version": 1, "weekdays": []}))
    with pytest.raises(ValueError, match="time zone"):
        validate_template(template(timezone="No/Such_Zone"))


def test_old_daily_template_occurrence_limit_is_respected_near_window():
    item = template(
        starts_on="2000-01-01", recurrence_kind="daily",
        recurrence_payload={"version": 1}, occurrence_limit=3,
    )
    rows = next_occurrences(item, datetime(2026, 9, 21, tzinfo=timezone.utc), 3)
    assert rows == []
