"""SQLite repositories for recurring meeting templates and occurrences."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .base import RepositoryBase
from src.app.scheduling.recurrence import validate_template


UTC = timezone.utc
PENDING_STATES = ("scheduled", "notified", "snoozed")
ALLOWED_TRANSITIONS = {
    "scheduled": {"notified", "missed", "started", "dismissed", "cancelled"},
    "notified": {"snoozed", "missed", "started", "dismissed", "cancelled"},
    "snoozed": {"notified", "missed", "started", "dismissed", "cancelled"},
    "missed": {"started", "dismissed", "cancelled"},
    "started": {"completed", "cancelled"},
    "dismissed": set(),
    "completed": set(),
    "cancelled": set(),
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)


class RecurringMeetingsRepository(RepositoryBase):
    """Own persisted recurring templates, occurrence state, and timeline rows."""

    @staticmethod
    def _template(row):
        if row is None:
            return None
        item = dict(row)
        item["tags"] = json.loads(item["tags"] or "[]")
        item["recurrence_payload"] = json.loads(item["recurrence_payload"] or "{}")
        item["enabled"] = bool(item["enabled"])
        item["archived"] = bool(item["archived"])
        return item

    @staticmethod
    def _occurrence(row):
        if row is None:
            return None
        return dict(row)

    def create_template(self, data: dict, *, now: datetime | None = None) -> int:
        item = validate_template(data)
        stamp = format_utc(now or utc_now())
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO recurring_meetings
                (title,tags,timezone,local_start_time,expected_duration_seconds,
                 reminder_lead_seconds,recurrence_kind,recurrence_payload,starts_on,
                 ends_on,occurrence_limit,enabled,last_materialized_at,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item["title"], json.dumps(item["tags"], ensure_ascii=False), item["timezone"],
                 item["local_start_time"], item["expected_duration_seconds"],
                 item["reminder_lead_seconds"], item["recurrence_kind"],
                 json.dumps(item["recurrence_payload"]), item["starts_on"], item["ends_on"],
                 item["occurrence_limit"], int(item["enabled"]), stamp, stamp, stamp),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_template(self, template_id: int, data: dict, *, update_future: bool,
                        now: datetime | None = None) -> dict:
        item = validate_template(data)
        stamp = format_utc(now or utc_now())
        with self.get_connection() as conn:
            exists = conn.execute("SELECT id FROM recurring_meetings WHERE id=? AND archived=0", (template_id,)).fetchone()
            if not exists:
                raise ValueError("Meeting template not found")
            conn.execute(
                """UPDATE recurring_meetings SET title=?,tags=?,timezone=?,local_start_time=?,
                expected_duration_seconds=?,reminder_lead_seconds=?,recurrence_kind=?,
                recurrence_payload=?,starts_on=?,ends_on=?,occurrence_limit=?,enabled=?,last_materialized_at=?,updated_at=?
                WHERE id=?""",
                (item["title"], json.dumps(item["tags"], ensure_ascii=False), item["timezone"],
                 item["local_start_time"], item["expected_duration_seconds"],
                 item["reminder_lead_seconds"], item["recurrence_kind"],
                 json.dumps(item["recurrence_payload"]), item["starts_on"], item["ends_on"],
                 item["occurrence_limit"], int(item["enabled"]), stamp, stamp, template_id),
            )
            if update_future:
                conn.execute(
                    "UPDATE meeting_occurrences SET cancellation_reason='template_edited',updated_at=? WHERE recurring_meeting_id=? AND state='cancelled' AND cancellation_reason='template_paused' AND scheduled_at_utc>?",
                    (stamp, template_id, stamp),
                )
                self._cancel_pending(conn, template_id, stamp, reason="template_edited", after=stamp)
            conn.commit()
        return self.get_template(template_id)

    def get_template(self, template_id: int):
        with self.get_connection() as conn:
            return self._template(conn.execute("SELECT * FROM recurring_meetings WHERE id=?", (template_id,)).fetchone())

    def mark_materialized(self, template_id: int, *, now: datetime):
        """Persist the scheduler cursor so a later startup can recover downtime."""
        stamp = format_utc(now)
        with self.get_connection() as conn:
            conn.execute("UPDATE recurring_meetings SET last_materialized_at=? WHERE id=? AND enabled=1 AND archived=0",
                         (stamp, int(template_id)))
            conn.commit()

    def list_templates(self, *, include_archived=False):
        query = "SELECT * FROM recurring_meetings"
        if not include_archived:
            query += " WHERE archived=0"
        query += " ORDER BY enabled DESC, title COLLATE NOCASE, id"
        with self.get_connection() as conn:
            return [self._template(row) for row in conn.execute(query)]

    def set_enabled(self, template_id: int, enabled: bool, *, now: datetime | None = None):
        stamp = format_utc(now or utc_now())
        with self.get_connection() as conn:
            row = conn.execute("SELECT archived,reminder_lead_seconds,title,tags,timezone,expected_duration_seconds FROM recurring_meetings WHERE id=?", (template_id,)).fetchone()
            if row is None or row["archived"]:
                raise ValueError("Meeting template not found")
            conn.execute("UPDATE recurring_meetings SET enabled=?,last_materialized_at=?,updated_at=? WHERE id=?",
                         (int(enabled), stamp, stamp, template_id))
            if enabled:
                rows = conn.execute(
                    "SELECT * FROM meeting_occurrences WHERE recurring_meeting_id=? AND state='cancelled' AND cancellation_reason='template_paused' AND scheduled_at_utc>?",
                    (template_id, stamp),
                ).fetchall()
                for occ in rows:
                    conn.execute("""UPDATE meeting_occurrences SET state='scheduled', reminder_at_utc=?,
                        title_snapshot=?,tags_snapshot=?,timezone_snapshot=?,expected_duration_snapshot=?,
                        cancellation_reason=NULL, updated_at=? WHERE id=?""",
                        (format_utc(parse_utc(occ["scheduled_at_utc"]) - timedelta(seconds=row["reminder_lead_seconds"])),
                         row["title"], row["tags"], row["timezone"], row["expected_duration_seconds"], stamp, occ["id"]))
                    self._write_timeline(conn, int(occ["id"]), template_id, "scheduled", stamp)
            else:
                self._cancel_pending(conn, template_id, stamp, reason="template_paused")
            conn.commit()
        return self.get_template(template_id)

    def archive_template(self, template_id: int, *, now: datetime | None = None):
        stamp = format_utc(now or utc_now())
        with self.get_connection() as conn:
            cursor = conn.execute("UPDATE recurring_meetings SET enabled=0,archived=1,updated_at=? WHERE id=?", (stamp, template_id))
            if cursor.rowcount == 0:
                raise ValueError("Meeting template not found")
            self._cancel_pending(conn, template_id, stamp, reason="template_deleted")
            conn.commit()

    def _cancel_pending(self, conn, template_id, stamp, *, reason, after=None):
        conditions = ["recurring_meeting_id=?", "state IN ('scheduled','notified','snoozed')"]
        match_values = [template_id]
        if after:
            conditions.append("scheduled_at_utc>?")
            match_values.append(after)
        where = " AND ".join(conditions)
        rows = conn.execute(f"SELECT id FROM meeting_occurrences WHERE {where}", match_values).fetchall()
        conn.execute(f"UPDATE meeting_occurrences SET state='cancelled',cancellation_reason=?,updated_at=? WHERE {where}",
                     (reason, stamp, *match_values))
        for row in rows:
            self._write_timeline(conn, int(row["id"]), template_id, "cancelled", stamp)

    def list_occurrences(self, *, start_utc: datetime | None = None, end_utc: datetime | None = None,
                         template_id: int | None = None, states: tuple[str, ...] | None = None,
                         local_date: str | None = None):
        clauses, values = [], []
        if start_utc is not None:
            clauses.append("o.scheduled_at_utc>=?")
            values.append(format_utc(start_utc))
        if end_utc is not None:
            clauses.append("o.scheduled_at_utc<=?")
            values.append(format_utc(end_utc))
        if template_id is not None:
            clauses.append("o.recurring_meeting_id=?")
            values.append(int(template_id))
        if local_date is not None:
            clauses.append("substr(o.scheduled_local,1,10)=?")
            values.append(str(local_date))
        if states:
            clauses.append("o.state IN (" + ",".join("?" for _ in states) + ")")
            values.extend(states)
        query = "SELECT o.*,o.title_snapshot AS title,o.tags_snapshot AS tags,o.timezone_snapshot AS timezone,o.expected_duration_snapshot AS expected_duration_seconds,m.local_start_time,m.reminder_lead_seconds FROM meeting_occurrences o JOIN recurring_meetings m ON m.id=o.recurring_meeting_id"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY o.scheduled_at_utc,o.id"
        with self.get_connection() as conn:
            return [dict(row) for row in conn.execute(query, values)]

    def get_occurrence(self, occurrence_id: int):
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT o.*,o.title_snapshot AS title,o.tags_snapshot AS tags,o.timezone_snapshot AS timezone,m.local_start_time,o.expected_duration_snapshot AS expected_duration_seconds,m.reminder_lead_seconds FROM meeting_occurrences o JOIN recurring_meetings m ON m.id=o.recurring_meeting_id WHERE o.id=?",
                (occurrence_id,),
            ).fetchone()
            item = self._occurrence(row)
            if item:
                item["tags"] = json.loads(item["tags"] or "[]")
            return item

    def insert_occurrence(self, template: dict, scheduled: dict, *, reminder_at_utc: str,
                          now: datetime, initial_state="scheduled") -> int | None:
        stamp = format_utc(now)
        with self.get_connection() as conn:
            previous = conn.execute(
                "SELECT * FROM meeting_occurrences WHERE recurring_meeting_id=? AND scheduled_local=?",
                (template["id"], scheduled["scheduled_local"]),
            ).fetchone()
            if previous is None:
                previous = conn.execute(
                    "SELECT * FROM meeting_occurrences WHERE recurring_meeting_id=? AND scheduled_at_utc=?",
                    (template["id"], scheduled["scheduled_at_utc"]),
                ).fetchone()
            if previous and previous["state"] == "cancelled" and previous["cancellation_reason"] == "template_edited":
                conn.execute("""UPDATE meeting_occurrences SET title_snapshot=?,tags_snapshot=?,timezone_snapshot=?,
                    expected_duration_snapshot=?,scheduled_at_utc=?,scheduled_local=?,state=?,reminder_at_utc=?,
                    cancellation_reason=NULL,updated_at=? WHERE id=?""",
                    (template["title"], json.dumps(template["tags"], ensure_ascii=False), template["timezone"],
                     template["expected_duration_seconds"], scheduled["scheduled_at_utc"], scheduled["scheduled_local"], initial_state,
                     reminder_at_utc, stamp, previous["id"]))
                self._write_timeline(conn, int(previous["id"]), int(template["id"]), initial_state, stamp)
                conn.commit()
                return int(previous["id"])
            cursor = conn.execute(
                """INSERT OR IGNORE INTO meeting_occurrences
                (recurring_meeting_id,title_snapshot,tags_snapshot,timezone_snapshot,expected_duration_snapshot,
                 scheduled_at_utc,scheduled_local,state,reminder_at_utc,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (template["id"], template["title"], json.dumps(template["tags"], ensure_ascii=False),
                 template["timezone"], template["expected_duration_seconds"],
                 scheduled["scheduled_at_utc"], scheduled["scheduled_local"], initial_state,
                 reminder_at_utc, stamp, stamp),
            )
            if cursor.rowcount == 0:
                return None
            occurrence_id = int(cursor.lastrowid)
            self._write_timeline(conn, occurrence_id, int(template["id"]), initial_state, stamp,
                                 title=template["title"], tags=template["tags"])
            conn.commit()
            return occurrence_id

    def transition(self, occurrence_id: int, target: str, *, now: datetime,
                   snoozed_until_utc: str | None = None, recording_id: int | None = None):
        stamp = format_utc(now)
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM meeting_occurrences WHERE id=?", (occurrence_id,)).fetchone()
            if row is None:
                raise ValueError("Meeting occurrence not found")
            current = row["state"]
            if target == current:
                return self.get_occurrence(occurrence_id)
            if target not in ALLOWED_TRANSITIONS.get(current, set()):
                if target == "started" and current in {"started", "completed"}:
                    return self.get_occurrence(occurrence_id)
                raise ValueError(f"Invalid meeting occurrence transition: {current} -> {target}")
            revision = int(row["notification_revision"])
            if target == "notified":
                revision += 1
            conn.execute(
                "UPDATE meeting_occurrences SET state=?,snoozed_until_utc=?,notification_revision=?,recording_id=COALESCE(?,recording_id),cancellation_reason=?,updated_at=? WHERE id=?",
                (target, snoozed_until_utc, revision, recording_id,
                 "recording_cancelled" if target == "cancelled" and current == "started" else None,
                 stamp, occurrence_id),
            )
            self._write_timeline(conn, occurrence_id, int(row["recurring_meeting_id"]), target, stamp)
            conn.commit()
        return self.get_occurrence(occurrence_id)

    def claim_missed_catch_up(self):
        """Claim missed rows once, returning one latest in-app catch-up summary."""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT id FROM meeting_occurrences WHERE state='missed' AND catch_up_offered=0 ORDER BY scheduled_at_utc DESC").fetchall()
            if not rows:
                return None
            ids = [int(row["id"]) for row in rows]
            conn.executemany("UPDATE meeting_occurrences SET catch_up_offered=1 WHERE id=?", [(item,) for item in ids])
            conn.commit()
        latest = self.get_occurrence(ids[0])
        latest["missed_count"] = len(ids)
        return latest

    def link_recording(self, occurrence_id: int, recording_id: int, *, now: datetime | None = None):
        stamp = format_utc(now or utc_now())
        with self.get_connection() as conn:
            row = conn.execute("SELECT state,recording_id FROM meeting_occurrences WHERE id=?", (occurrence_id,)).fetchone()
            if row is None:
                raise ValueError("Meeting occurrence not found")
            if row["recording_id"] not in (None, recording_id):
                raise ValueError("Meeting occurrence already links to another recording")
            conn.execute("UPDATE meeting_occurrences SET state='completed',recording_id=?,updated_at=? WHERE id=?",
                         (int(recording_id), stamp, occurrence_id))
            self._write_timeline(conn, occurrence_id, self._template_id_for_occurrence(conn, occurrence_id), "completed", stamp)
            conn.commit()
        return self.get_occurrence(occurrence_id)

    @staticmethod
    def _template_id_for_occurrence(conn, occurrence_id):
        row = conn.execute("SELECT recurring_meeting_id FROM meeting_occurrences WHERE id=?", (occurrence_id,)).fetchone()
        return int(row[0])

    @staticmethod
    def _write_timeline(conn, occurrence_id, template_id, state, stamp, *, title=None, tags=None):
        if title is None or tags is None:
            row = conn.execute("SELECT title_snapshot,tags_snapshot FROM meeting_occurrences WHERE id=?", (occurrence_id,)).fetchone()
            if row and row["title_snapshot"]:
                title = title or row["title_snapshot"]
                tags = tags if tags is not None else json.loads(row["tags_snapshot"] or "[]")
            else:
                row = conn.execute("SELECT title,tags FROM recurring_meetings WHERE id=?", (template_id,)).fetchone()
                if row:
                    title = title or row["title"]
                    tags = tags if tags is not None else json.loads(row["tags"] or "[]")
                else:
                    title, tags = title or "Meeting", tags or []
        scheduled = conn.execute("SELECT scheduled_local,timezone_snapshot FROM meeting_occurrences WHERE id=?", (occurrence_id,)).fetchone()
        occurred_at = scheduled["scheduled_local"] if scheduled else stamp
        timezone_name = scheduled["timezone_snapshot"] if scheduled else "UTC"
        conn.execute(
            """INSERT INTO timeline_events(event_type,source_id,occurred_at,title_snapshot,tags_snapshot,metadata)
            VALUES('meeting_occurrence',?,?,?,?,?) ON CONFLICT(event_type,source_id) DO UPDATE SET
            occurred_at=excluded.occurred_at,title_snapshot=excluded.title_snapshot,
            tags_snapshot=excluded.tags_snapshot,metadata=excluded.metadata""",
            (occurrence_id, occurred_at, title, json.dumps(tags or [], ensure_ascii=False),
             json.dumps({"template_id": template_id, "state": state,
                         "scheduled_local": occurred_at, "timezone": timezone_name})),
        )
