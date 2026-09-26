"""Clock-injectable local materialization and reminder state machine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.app.scheduling.recurrence import expand_occurrences, validate_template
from src.persistence.meetings import format_utc, parse_utc, utc_now


class MeetingScheduler:
    """Materialize a rolling window and transition reminders without Qt dependency."""

    def __init__(self, repository, *, clock=utc_now, window_days: int = 60):
        self.repository = repository
        self.clock = clock
        self.window_days = max(7, int(window_days))

    def materialize(self, *, now: datetime | None = None):
        now = (now or self.clock()).astimezone(timezone.utc)
        end = now + timedelta(days=self.window_days)
        inserted = []
        for template in self.repository.list_templates():
            if not template["enabled"]:
                continue
            try:
                normalized = validate_template(template)
                normalized["id"] = template["id"]
                backfill_start = parse_utc(template.get("last_materialized_at") or template["created_at"])
                if backfill_start > now:
                    backfill_start = now
                occurrences = expand_occurrences(normalized, backfill_start, end)
            except (ValueError, TypeError, KeyError):
                continue
            for scheduled in occurrences:
                at = parse_utc(scheduled["scheduled_at_utc"])
                state = "missed" if at <= now else "scheduled"
                reminder = at - timedelta(seconds=normalized["reminder_lead_seconds"])
                occurrence_id = self.repository.insert_occurrence(
                    template, scheduled, reminder_at_utc=format_utc(reminder), now=now,
                    initial_state=state,
                )
                if occurrence_id is not None:
                    inserted.append(occurrence_id)
            self.repository.mark_materialized(int(template["id"]), now=now)
        return inserted

    def tick(self, *, now: datetime | None = None) -> dict:
        """Return newly due reminders and one collapsed, persistent missed catch-up."""
        now = (now or self.clock()).astimezone(timezone.utc)
        self.materialize(now=now)
        transitions = self.repository.list_occurrences(states=("scheduled", "notified", "snoozed"))
        reminders = []
        for occurrence in transitions:
            scheduled_at = parse_utc(occurrence["scheduled_at_utc"])
            if scheduled_at <= now:
                self.repository.transition(occurrence["id"], "missed", now=now)
                continue
            due_at = (
                parse_utc(occurrence["snoozed_until_utc"])
                if occurrence["state"] == "snoozed" and occurrence.get("snoozed_until_utc")
                else parse_utc(occurrence["reminder_at_utc"])
            )
            if occurrence["state"] in ("scheduled", "snoozed") and due_at <= now:
                reminders.append(self.repository.transition(occurrence["id"], "notified", now=now))
        return {"reminders": reminders, "catch_up": self.repository.claim_missed_catch_up()}

    def snooze(self, occurrence_id: int, minutes: int, *, now: datetime | None = None):
        if int(minutes) not in (5, 10, 15):
            raise ValueError("Snooze must be 5, 10, or 15 minutes")
        now = (now or self.clock()).astimezone(timezone.utc)
        return self.repository.transition(
            occurrence_id, "snoozed", now=now,
            snoozed_until_utc=format_utc(now + timedelta(minutes=int(minutes))),
        )

    def dismiss(self, occurrence_id: int, *, now: datetime | None = None):
        return self.repository.transition(occurrence_id, "dismissed", now=(now or self.clock()).astimezone(timezone.utc))

    def start(self, occurrence_id: int, *, now: datetime | None = None):
        occurrence = self.repository.get_occurrence(occurrence_id)
        if occurrence is None:
            raise ValueError("Meeting occurrence not found")
        if occurrence["state"] in ("started", "completed"):
            return occurrence
        return self.repository.transition(occurrence_id, "started", now=(now or self.clock()).astimezone(timezone.utc))

    def cancel_started(self, occurrence_id: int, *, now: datetime | None = None):
        return self.repository.transition(occurrence_id, "cancelled", now=(now or self.clock()).astimezone(timezone.utc))
