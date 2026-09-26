"""Validated, time-zone-aware recurrence expansion for local meetings."""

from __future__ import annotations

import re
import calendar
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def normalize_tags(value) -> list[str]:
    values = value.split(",") if isinstance(value, str) else (value or [])
    result, seen = [], set()
    for item in values:
        tag = str(item).strip()
        folded = tag.casefold()
        if tag and folded not in seen:
            result.append(tag)
            seen.add(folded)
    return result


def validate_template(data: dict) -> dict:
    """Validate and return the canonical v1 template representation."""
    title = str(data.get("title", "")).strip()
    if not title:
        raise ValueError("Meeting title is required")
    local_time = str(data.get("local_start_time", ""))
    if not _TIME_RE.fullmatch(local_time):
        raise ValueError("Start time must use HH:MM in 24-hour format")
    timezone_name = str(data.get("timezone", "")).strip()
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError("Choose a valid IANA time zone") from exc

    kind = str(data.get("recurrence_kind", ""))
    payload = data.get("recurrence_payload") or {}
    if kind not in {"daily", "weekly", "monthly"}:
        raise ValueError("Recurrence must be daily, weekly, or monthly")
    if int(payload.get("version", 1)) != 1:
        raise ValueError("Unsupported recurrence payload version")
    canonical_payload = {"version": 1}
    if kind == "weekly":
        weekdays = sorted({int(day) for day in payload.get("weekdays", [])})
        if not weekdays or any(day < 0 or day > 6 for day in weekdays):
            raise ValueError("Choose at least one weekday (Monday is 0)")
        canonical_payload["weekdays"] = weekdays
    elif kind == "monthly":
        day = int(payload.get("day", 0))
        if not 1 <= day <= 31:
            raise ValueError("Monthly day must be between 1 and 31")
        canonical_payload["day"] = day

    try:
        starts_on = date.fromisoformat(str(data["starts_on"])).isoformat()
        ends_on = date.fromisoformat(str(data["ends_on"])).isoformat() if data.get("ends_on") else None
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("A valid recurrence start date is required") from exc
    if ends_on and ends_on < starts_on:
        raise ValueError("End date cannot be before start date")

    occurrence_limit = data.get("occurrence_limit")
    occurrence_limit = int(occurrence_limit) if occurrence_limit not in (None, "", 0, "0") else None
    if occurrence_limit is not None and occurrence_limit < 1:
        raise ValueError("Occurrence count must be positive")
    duration = int(data.get("expected_duration_seconds", 0))
    lead = int(data.get("reminder_lead_seconds", 0))
    if duration <= 0:
        raise ValueError("Expected duration must be positive")
    if lead < 0 or lead > 7 * 24 * 3600:
        raise ValueError("Reminder lead must be between 0 and 7 days")

    return {
        "title": title,
        "tags": normalize_tags(data.get("tags")),
        "local_start_time": local_time,
        "timezone": timezone_name,
        "expected_duration_seconds": duration,
        "reminder_lead_seconds": lead,
        "recurrence_kind": kind,
        "recurrence_payload": canonical_payload,
        "starts_on": starts_on,
        "ends_on": ends_on,
        "occurrence_limit": occurrence_limit,
        "enabled": bool(data.get("enabled", True)),
    }


def resolve_local_datetime(local_date: date, local_time: str, timezone_name: str) -> datetime:
    """Resolve a local wall time using fold=0 and first-valid-after-gap policy."""
    zone = ZoneInfo(timezone_name)
    hour, minute = map(int, local_time.split(":"))
    naive = datetime.combine(local_date, time(hour, minute))
    for _ in range(181):
        first = naive.replace(tzinfo=zone, fold=0)
        second = naive.replace(tzinfo=zone, fold=1)
        first_valid = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == naive
        second_valid = second.astimezone(UTC).astimezone(zone).replace(tzinfo=None) == naive
        if first_valid:
            # For an ambiguous instant fold=0 is the first chronological instant.
            if second_valid and first.utcoffset() != second.utcoffset():
                return first
            return first
        if second_valid:
            return second
        naive += timedelta(minutes=1)
    raise ValueError(f"Could not resolve local time {local_time} on {local_date} in {timezone_name}")


def _matches(day: date, kind: str, payload: dict) -> bool:
    if kind == "daily":
        return True
    if kind == "weekly":
        return day.weekday() in payload["weekdays"]
    return day.day == payload["day"]


def _count_matches_through(start: date, end: date, kind: str, payload: dict) -> int:
    """Count valid recurrence dates without scanning old days one by one."""
    if end < start:
        return 0
    if kind == "daily":
        return (end - start).days + 1
    if kind == "weekly":
        total_days = (end - start).days + 1
        full_weeks, remainder = divmod(total_days, 7)
        weekdays = set(payload["weekdays"])
        return full_weeks * len(weekdays) + sum(
            (start.weekday() + offset) % 7 in weekdays for offset in range(remainder)
        )
    target_day = payload["day"]
    month_index = start.year * 12 + start.month - 1
    end_month_index = end.year * 12 + end.month - 1
    total = 0
    while month_index <= end_month_index:
        year, zero_month = divmod(month_index, 12)
        month = zero_month + 1
        if target_day <= calendar.monthrange(year, month)[1]:
            candidate = date(year, month, target_day)
            total += start <= candidate <= end
        month_index += 1
    return total


def expand_occurrences(template: dict, start_utc: datetime, end_utc: datetime) -> list[dict]:
    """Expand a template into UTC/local scheduled instances in an inclusive window."""
    item = validate_template(template)
    start_utc = _as_utc(start_utc)
    end_utc = _as_utc(end_utc)
    if end_utc < start_utc:
        return []
    zone = ZoneInfo(item["timezone"])
    begin = date.fromisoformat(item["starts_on"])
    finish = date.fromisoformat(item["ends_on"]) if item["ends_on"] else end_utc.astimezone(zone).date()
    local_end = min(finish, end_utc.astimezone(zone).date())
    if begin > local_end:
        return []

    local_start = start_utc.astimezone(zone).date()
    iteration_begin = max(begin, local_start - timedelta(days=1))
    before_count = _count_matches_through(
        begin, iteration_begin - timedelta(days=1), item["recurrence_kind"], item["recurrence_payload"]
    )
    if item["occurrence_limit"] is not None and before_count >= item["occurrence_limit"]:
        return []

    result = []
    count = before_count
    current = iteration_begin
    while current <= local_end:
        if _matches(current, item["recurrence_kind"], item["recurrence_payload"]):
            count += 1
            if item["occurrence_limit"] is not None and count > item["occurrence_limit"]:
                break
            resolved = resolve_local_datetime(current, item["local_start_time"], item["timezone"])
            scheduled_utc = resolved.astimezone(UTC)
            if start_utc <= scheduled_utc <= end_utc:
                result.append({
                    "scheduled_at_utc": _format_utc(scheduled_utc),
                    "scheduled_local": resolved.replace(tzinfo=None).isoformat(timespec="minutes"),
                    "timezone": item["timezone"],
                    "local_date": current.isoformat(),
                })
        current += timedelta(days=1)
    return result


def next_occurrences(template: dict, after_utc: datetime | None = None, count: int = 3) -> list[dict]:
    """Return the next ``count`` occurrences on/after a UTC instant."""
    after_utc = _as_utc(after_utc or datetime.now(UTC))
    if count <= 0:
        return []
    search_end = after_utc + timedelta(days=max(370, count * 40))
    rows = expand_occurrences(template, after_utc, search_end)
    return rows[:count]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("UTC-aware datetime required")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
