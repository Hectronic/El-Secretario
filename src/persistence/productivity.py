"""Persistence for focus sessions, notes, and the shared activity timeline."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .base import RepositoryBase


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def normalize_tags(tags):
    if isinstance(tags, str):
        tags = tags.split(",")
    result = []
    seen = set()
    for tag in tags or []:
        label = str(tag).strip()
        if label and label.casefold() not in seen:
            seen.add(label.casefold())
            result.append(label)
    return result


def _decode(row):
    if row is None:
        return None
    value = dict(row)
    if "tags" in value:
        value["tags"] = json.loads(value["tags"])
    if "tags_snapshot" in value:
        value["tags_snapshot"] = json.loads(value["tags_snapshot"])
    if "metadata" in value:
        value["metadata"] = json.loads(value["metadata"])
    return value


class ProductivityRepository(RepositoryBase):
    def get_productivity_tags(self, start_date=None, end_date=None):
        """Offer timeline and active-focus tags to the global tag selector."""
        def date_clauses(column):
            clauses = []
            values = []
            if start_date:
                clauses.append(f"substr({column},1,10) >= ?")
                values.append(str(start_date))
            if end_date:
                clauses.append(f"substr({column},1,10) <= ?")
                values.append(str(end_date))
            return (" WHERE " + " AND ".join(clauses)) if clauses else "", values

        event_where, event_values = date_clauses("occurred_at")
        focus_where, focus_values = date_clauses("started_at")
        focus_where += " AND state IN ('running','paused')" if focus_where else " WHERE state IN ('running','paused')"
        with self.get_connection() as conn:
            event_tags = [json.loads(row[0]) for row in conn.execute(
                "SELECT tags_snapshot FROM timeline_events" + event_where, event_values)]
            active_tags = [json.loads(row[0]) for row in conn.execute(
                "SELECT tags FROM pomodoros" + focus_where, focus_values)]
        return sorted(normalize_tags(tag for group in event_tags + active_tags for tag in group), key=str.casefold)

    def upsert_timeline_event(self, event_type, source_id, occurred_at, title, tags=(),
                              *, parent_source_id=None, metadata=None):
        """Allow another feature owner to publish an idempotent activity reference."""
        if not event_type or not str(title).strip():
            raise ValueError("Timeline events require a type and title")
        with self.get_connection() as conn:
            conn.execute("""INSERT INTO timeline_events
                (event_type,source_id,parent_source_id,occurred_at,title_snapshot,tags_snapshot,metadata)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(event_type,source_id) DO UPDATE SET
                    parent_source_id=excluded.parent_source_id,
                    occurred_at=excluded.occurred_at,
                    title_snapshot=excluded.title_snapshot,
                    tags_snapshot=excluded.tags_snapshot,
                    metadata=excluded.metadata""",
                (event_type, source_id, parent_source_id, occurred_at, str(title).strip(),
                 json.dumps(normalize_tags(tags)), json.dumps(metadata or {})))
            conn.commit()

    def create_break(self, kind, planned_seconds, started_at=None):
        if kind not in ("short", "long") or not isinstance(planned_seconds, int) or planned_seconds <= 0:
            raise ValueError("A valid break kind and duration are required")
        started_at = started_at or now_iso()
        with self.get_connection() as conn:
            cursor = conn.execute("""INSERT INTO pomodoro_breaks
                (kind,state,started_at,planned_seconds,run_started_at,created_at,updated_at)
                VALUES (?,'running',?,?,?,?,?)""",
                (kind, started_at, planned_seconds, started_at, started_at, started_at))
            conn.commit()
            return cursor.lastrowid

    def fetch_break(self, break_id):
        with self.get_connection() as conn:
            return _decode(conn.execute("SELECT * FROM pomodoro_breaks WHERE id=?", (break_id,)).fetchone())

    def fetch_active_break(self):
        with self.get_connection() as conn:
            return _decode(conn.execute("SELECT * FROM pomodoro_breaks WHERE state IN ('running','paused') LIMIT 1").fetchone())

    def update_break(self, break_id, *, state, elapsed_seconds, run_started_at, updated_at):
        with self.get_connection() as conn:
            conn.execute("""UPDATE pomodoro_breaks SET state=?, elapsed_seconds=?,
                run_started_at=?, updated_at=? WHERE id=?""",
                (state, elapsed_seconds, run_started_at, updated_at, break_id))
            conn.commit()

    def end_break(self, break_id, ended_at, elapsed_seconds, *, completed):
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM pomodoro_breaks WHERE id=?", (break_id,)).fetchone()
            if row is None or row["state"] in ("completed", "cancelled"):
                return False
            state = "completed" if completed else "cancelled"
            actual = max(0, min(float(elapsed_seconds), row["planned_seconds"]))
            conn.execute("""UPDATE pomodoro_breaks SET state=?, ended_at=?, elapsed_seconds=?,
                run_started_at=NULL, updated_at=? WHERE id=?""",
                (state, ended_at, actual, ended_at, break_id))
            if completed:
                conn.execute("""INSERT INTO timeline_events
                    (event_type,source_id,occurred_at,title_snapshot,tags_snapshot,metadata)
                    VALUES ('break',?,?,?,?,?) ON CONFLICT(event_type,source_id) DO NOTHING""",
                    (break_id, ended_at, f"{row['kind'].capitalize()} break", "[]",
                     json.dumps({"kind": row["kind"], "elapsed_seconds": actual})))
            conn.commit()
            return True

    def create_pomodoro(self, title, tags, planned_seconds, started_at=None):
        title = str(title).strip()
        if not title or int(planned_seconds) <= 0:
            raise ValueError("A title and positive duration are required")
        started_at = started_at or now_iso()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO pomodoros
                   (title,tags,state,started_at,planned_seconds,run_started_at,created_at,updated_at)
                   VALUES (?,?,'running',?,?,?,?,?)""",
                (title, json.dumps(normalize_tags(tags)), started_at, int(planned_seconds), started_at, started_at, started_at),
            )
            conn.commit()
            return cursor.lastrowid

    def fetch_pomodoro(self, pomodoro_id):
        with self.get_connection() as conn:
            return _decode(conn.execute("SELECT * FROM pomodoros WHERE id=?", (pomodoro_id,)).fetchone())

    def fetch_active_pomodoro(self):
        with self.get_connection() as conn:
            return _decode(conn.execute("SELECT * FROM pomodoros WHERE state IN ('running','paused') LIMIT 1").fetchone())

    def update_pomodoro(self, pomodoro_id, *, state=None, elapsed_seconds=None, run_started_at=None,
                        title=None, tags=None, updated_at=None):
        fields = []
        values = []
        for key, value in (("state", state), ("elapsed_seconds", elapsed_seconds),
                           ("run_started_at", run_started_at), ("title", title),
                           ("tags", json.dumps(normalize_tags(tags)) if tags is not None else None)):
            if value is not None:
                fields.append(f"{key}=?")
                values.append(value)
        fields.append("updated_at=?")
        values.append(updated_at or now_iso())
        values.append(pomodoro_id)
        with self.get_connection() as conn:
            conn.execute(f"UPDATE pomodoros SET {', '.join(fields)} WHERE id=?", values)
            conn.commit()

    def complete_pomodoro(self, pomodoro_id, ended_at, elapsed_seconds, outcome):
        if outcome not in ("completed", "ended_early"):
            raise ValueError("Invalid focus outcome")
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM pomodoros WHERE id=?", (pomodoro_id,)).fetchone()
            if row is None:
                raise ValueError("Pomodoro not found")
            if row["state"] == "completed":
                return False
            if row["state"] == "cancelled":
                raise ValueError("Cancelled Pomodoro cannot complete")
            actual = max(0, min(float(elapsed_seconds), int(row["planned_seconds"])))
            conn.execute("""UPDATE pomodoros SET state='completed', ended_at=?, elapsed_seconds=?,
                            run_started_at=NULL, outcome=?, updated_at=? WHERE id=?""",
                         (ended_at, actual, outcome, ended_at, pomodoro_id))
            conn.execute("""INSERT INTO timeline_events
                            (event_type,source_id,occurred_at,title_snapshot,tags_snapshot,metadata)
                            VALUES ('pomodoro',?,?,?,?,?)
                            ON CONFLICT(event_type,source_id) DO NOTHING""",
                         (pomodoro_id, ended_at, row["title"], row["tags"],
                          json.dumps({"planned_seconds": row["planned_seconds"], "elapsed_seconds": actual,
                                      "outcome": outcome, "started_at": row["started_at"]})))
            conn.commit()
        return True

    def cancel_pomodoro(self, pomodoro_id, ended_at, elapsed_seconds):
        with self.get_connection() as conn:
            row = conn.execute("SELECT state FROM pomodoros WHERE id=?", (pomodoro_id,)).fetchone()
            if row is None or row["state"] in ("cancelled", "completed"):
                return False
            conn.execute("""UPDATE pomodoros SET state='cancelled', ended_at=?, elapsed_seconds=?,
                            run_started_at=NULL, updated_at=? WHERE id=?""",
                         (ended_at, max(0, elapsed_seconds), ended_at, pomodoro_id))
            conn.execute("UPDATE productivity_notes SET pomodoro_id=NULL WHERE pomodoro_id=?", (pomodoro_id,))
            conn.execute("UPDATE timeline_events SET parent_source_id=NULL WHERE parent_source_id=?", (pomodoro_id,))
            conn.commit()
        return True

    def delete_pomodoro(self, pomodoro_id):
        """Remove a finished focus interval and leave its saved notes standalone."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT state FROM pomodoros WHERE id=?", (pomodoro_id,)).fetchone()
            if row is None:
                return False
            if row["state"] in ("running", "paused"):
                raise ValueError("Finish or cancel an active Pomodoro before deleting it")
            conn.execute("UPDATE productivity_notes SET pomodoro_id=NULL WHERE pomodoro_id=?", (pomodoro_id,))
            conn.execute("UPDATE timeline_events SET parent_source_id=NULL WHERE parent_source_id=?", (pomodoro_id,))
            conn.execute("DELETE FROM timeline_events WHERE event_type='pomodoro' AND source_id=?", (pomodoro_id,))
            conn.execute("DELETE FROM pomodoros WHERE id=?", (pomodoro_id,))
            conn.commit()
            return True

    def create_productivity_note(self, kind, title, tags, *, body=None, audio_ref=None,
                                 duration_seconds=None, pomodoro_id=None, captured_at=None):
        title = str(title).strip()
        if not title or kind not in ("text", "audio"):
            raise ValueError("A note kind and title are required")
        if kind == "text" and not str(body or "").strip():
            raise ValueError("A text note requires a body")
        if kind == "audio" and (not audio_ref or not Path(audio_ref).is_absolute() or
                                duration_seconds is None or float(duration_seconds) <= 0):
            raise ValueError("An audio note requires an absolute file reference and duration")
        if kind == "text" and audio_ref:
            raise ValueError("Text notes cannot contain audio")
        captured_at = captured_at or now_iso()
        with self.get_connection() as conn:
            if pomodoro_id is not None and not conn.execute("SELECT 1 FROM pomodoros WHERE id=?", (pomodoro_id,)).fetchone():
                raise ValueError("Pomodoro not found")
            cursor = conn.execute("""INSERT INTO productivity_notes
                (kind,title,body,audio_ref,duration_seconds,tags,pomodoro_id,captured_at,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (kind, title, body, audio_ref, duration_seconds, json.dumps(normalize_tags(tags)),
                 pomodoro_id, captured_at, captured_at, captured_at))
            note_id = cursor.lastrowid
            conn.execute("""INSERT INTO timeline_events
                (event_type,source_id,parent_source_id,occurred_at,title_snapshot,tags_snapshot)
                VALUES (?,?,?,?,?,?)""",
                (f"{kind}_note", note_id, pomodoro_id, captured_at, title, json.dumps(normalize_tags(tags))))
            conn.commit()
            return note_id

    def fetch_productivity_note(self, note_id):
        with self.get_connection() as conn:
            return _decode(conn.execute("SELECT * FROM productivity_notes WHERE id=?", (note_id,)).fetchone())

    def fetch_productivity_notes(self, pomodoro_id):
        with self.get_connection() as conn:
            return [_decode(row) for row in conn.execute("SELECT * FROM productivity_notes WHERE pomodoro_id=? ORDER BY captured_at,id", (pomodoro_id,))]

    def update_productivity_note_transcription(self, note_id, transcription):
        with self.get_connection() as conn:
            conn.execute("UPDATE productivity_notes SET transcription=?, updated_at=? WHERE id=?",
                         (transcription, now_iso(), note_id))
            conn.commit()

    def delete_productivity_note(self, note_id):
        with self.get_connection() as conn:
            row = conn.execute("SELECT audio_ref FROM productivity_notes WHERE id=?", (note_id,)).fetchone()
            if row is None:
                return None
            conn.execute("DELETE FROM timeline_events WHERE event_type IN ('text_note','audio_note') AND source_id=?", (note_id,))
            conn.execute("DELETE FROM productivity_notes WHERE id=?", (note_id,))
            conn.commit()
            return row["audio_ref"]

    def fetch_timeline(self, *, start_date=None, end_date=None, tag=None, limit=50, offset=0, show_breaks=False):
        if limit < 1 or limit > 200 or offset < 0:
            raise ValueError("Invalid timeline page")
        clauses = []
        values = []
        if start_date:
            clauses.append("substr(e.occurred_at,1,10) >= ?")
            values.append(str(start_date))
        if end_date:
            clauses.append("substr(e.occurred_at,1,10) <= ?")
            values.append(str(end_date))
        if not show_breaks:
            clauses.append("e.event_type != 'break'")
        if tag:
            clauses.append("""(
                EXISTS (SELECT 1 FROM json_each(e.tags_snapshot) WHERE lower(value)=lower(?))
                OR EXISTS (SELECT 1 FROM json_each(p.tags) WHERE lower(value)=lower(?))
            )""")
            values.extend((tag, tag))
        sql = "SELECT e.*, p.tags AS parent_tags FROM timeline_events e LEFT JOIN pomodoros p ON p.id=e.parent_source_id"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY e.occurred_at DESC, e.id DESC LIMIT ? OFFSET ?"
        values.extend((limit, offset))
        with self.get_connection() as conn:
            rows = [_decode(row) for row in conn.execute(sql, values)]
        for row in rows:
            parent = json.loads(row.pop("parent_tags")) if row["parent_tags"] else []
            row["display_tags"] = normalize_tags(row["tags_snapshot"] + parent)
        return rows
