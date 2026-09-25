"""Monotonic focus timer with durable state and explicit restart recovery."""

from __future__ import annotations

import logging
import time
from datetime import datetime


class SystemClock:
    monotonic = staticmethod(time.monotonic)

    @staticmethod
    def now():
        return datetime.now().astimezone().isoformat(timespec="seconds")


class PomodoroService:
    def __init__(self, persistence, *, clock=None, notify=None):
        self.db = persistence
        self.clock = clock or SystemClock()
        self.notify = notify or (lambda _title, _body: None)
        self._session = self.db.fetch_active_pomodoro()
        self._run_anchor = None
        self._elapsed_before_run = float(self._session["elapsed_seconds"]) if self._session else 0.0
        self.recovery_required = bool(self._session)
        self.state = self._session["state"] if self._session else "idle"
        self.pomodoro_id = self._session["id"] if self._session else None

    @property
    def title(self):
        return self._session["title"] if self._session else ""

    @property
    def planned_seconds(self):
        return self._session["planned_seconds"] if self._session else 0

    @property
    def elapsed_seconds(self):
        if self.state == "running" and self._run_anchor is not None:
            return max(0.0, self._elapsed_before_run + self.clock.monotonic() - self._run_anchor)
        return max(0.0, self._elapsed_before_run)

    @property
    def remaining_seconds(self):
        return max(0, self.planned_seconds - self.elapsed_seconds)

    def _require_ready(self):
        if self.recovery_required:
            raise RuntimeError("Resolve the previous focus session first")

    def start(self, title, tags=None, planned_seconds=1500):
        self._require_ready()
        if self.state in ("running", "paused"):
            raise RuntimeError("A focus session is already active")
        if self.db.fetch_active_break():
            raise RuntimeError("Finish the active break before starting focus")
        if not str(title).strip() or not isinstance(planned_seconds, int) or planned_seconds <= 0:
            raise ValueError("A title and positive duration are required")
        started_at = self.clock.now()
        self.pomodoro_id = self.db.create_pomodoro(title, tags or [], planned_seconds, started_at)
        self._session = self.db.fetch_pomodoro(self.pomodoro_id)
        self._elapsed_before_run = 0.0
        self._run_anchor = self.clock.monotonic()
        self.state = "running"
        return self.pomodoro_id

    def pause(self):
        self._require_ready()
        if self.state != "running":
            return False
        self._elapsed_before_run = min(self.elapsed_seconds, self.planned_seconds)
        self._run_anchor = None
        self.state = "paused"
        self.db.update_pomodoro(self.pomodoro_id, state="paused", elapsed_seconds=self._elapsed_before_run,
                                run_started_at="", updated_at=self.clock.now())
        return True

    def resume(self):
        self._require_ready()
        if self.state != "paused":
            return False
        self._run_anchor = self.clock.monotonic()
        self.state = "running"
        self.db.update_pomodoro(self.pomodoro_id, state="running", run_started_at=self.clock.now())
        return True

    def update_metadata(self, title, tags):
        self._require_ready()
        if self.state not in ("running", "paused") or not str(title).strip():
            raise ValueError("An active session and title are required")
        self.db.update_pomodoro(self.pomodoro_id, title=title.strip(), tags=tags)
        self._session = self.db.fetch_pomodoro(self.pomodoro_id)

    def tick(self):
        self._require_ready()
        if self.state == "running" and self.remaining_seconds <= 0:
            self.finish()
            return True
        return False

    def finish(self):
        self._require_ready()
        if self.state not in ("running", "paused"):
            return False
        actual = min(self.elapsed_seconds, self.planned_seconds)
        outcome = "completed" if actual >= self.planned_seconds else "ended_early"
        did_complete = self.db.complete_pomodoro(self.pomodoro_id, self.clock.now(), actual, outcome)
        self._elapsed_before_run = actual
        self._run_anchor = None
        self.state = "completed"
        self._session = self.db.fetch_pomodoro(self.pomodoro_id)
        if did_complete:
            try:
                self.notify("Pomodoro complete", self.title)
            except Exception:
                # Notification failure must never roll back a completed interval.
                logging.exception("Pomodoro completion notification unavailable")
        return did_complete

    def cancel(self):
        self._require_ready()
        if self.state not in ("running", "paused"):
            return False
        actual = min(self.elapsed_seconds, self.planned_seconds)
        did_cancel = self.db.cancel_pomodoro(self.pomodoro_id, self.clock.now(), actual)
        self._elapsed_before_run = actual
        self._run_anchor = None
        self.state = "cancelled"
        return did_cancel

    def checkpoint(self):
        """Persist elapsed progress before a clean application shutdown."""
        if self.state == "running" and not self.recovery_required:
            self.db.update_pomodoro(self.pomodoro_id, elapsed_seconds=min(self.elapsed_seconds, self.planned_seconds),
                                    run_started_at=self.clock.now())

    def confirm_recovery(self, choice):
        if not self.recovery_required or choice not in ("complete", "discard", "resume"):
            raise ValueError("Choose complete, discard, or resume for an interrupted session")
        row = self.db.fetch_pomodoro(self.pomodoro_id)
        stored = float(row["elapsed_seconds"])
        if row["state"] == "running" and row["run_started_at"]:
            try:
                now = datetime.fromisoformat(self.clock.now())
                earlier = datetime.fromisoformat(row["run_started_at"])
                estimated = max(0, (now - earlier).total_seconds())
                stored = min(row["planned_seconds"], stored + estimated)
            except (ValueError, TypeError):
                pass
        self._elapsed_before_run = stored
        self._run_anchor = None
        self.recovery_required = False
        self.state = "paused"
        if choice == "discard":
            self.cancel()
        elif choice == "complete":
            self.finish()
        else:
            self.db.update_pomodoro(self.pomodoro_id, state="paused", elapsed_seconds=stored,
                                    run_started_at="", updated_at=self.clock.now())
        return self.state
