"""Break timer, separate from completed focus accounting."""

from __future__ import annotations

from .service import SystemClock


class BreakService:
    def __init__(self, persistence, *, clock=None):
        self.db = persistence
        self.clock = clock or SystemClock()
        self._session = self.db.fetch_active_break()
        self.break_id = self._session["id"] if self._session else None
        self.state = self._session["state"] if self._session else "idle"
        self.recovery_required = bool(self._session)
        self._elapsed_before_run = float(self._session["elapsed_seconds"]) if self._session else 0.0
        self._run_anchor = None

    @property
    def planned_seconds(self):
        return self._session["planned_seconds"] if self._session else 0

    @property
    def kind(self):
        return self._session["kind"] if self._session else None

    @property
    def elapsed_seconds(self):
        if self.state == "running" and self._run_anchor is not None:
            return max(0, self._elapsed_before_run + self.clock.monotonic() - self._run_anchor)
        return max(0, self._elapsed_before_run)

    @property
    def remaining_seconds(self):
        return max(0, self.planned_seconds - self.elapsed_seconds)

    def start(self, kind, planned_seconds):
        if self.recovery_required or self.state in ("running", "paused"):
            raise RuntimeError("Resolve the active break first")
        if self.db.fetch_active_pomodoro():
            raise RuntimeError("Finish the active Pomodoro before starting a break")
        self.break_id = self.db.create_break(kind, planned_seconds, self.clock.now())
        self._session = self.db.fetch_break(self.break_id)
        self._elapsed_before_run = 0.0
        self._run_anchor = self.clock.monotonic()
        self.state = "running"

    def pause(self):
        if self.state != "running" or self.recovery_required:
            return False
        self._elapsed_before_run = min(self.elapsed_seconds, self.planned_seconds)
        self._run_anchor = None
        self.state = "paused"
        self.db.update_break(self.break_id, state="paused", elapsed_seconds=self._elapsed_before_run,
                             run_started_at="", updated_at=self.clock.now())
        return True

    def resume(self):
        if self.state != "paused" or self.recovery_required:
            return False
        self._run_anchor = self.clock.monotonic()
        self.state = "running"
        self.db.update_break(self.break_id, state="running", elapsed_seconds=self._elapsed_before_run,
                             run_started_at=self.clock.now(), updated_at=self.clock.now())
        return True

    def finish(self):
        if self.state not in ("running", "paused") or self.recovery_required:
            return False
        actual = min(self.elapsed_seconds, self.planned_seconds)
        changed = self.db.end_break(self.break_id, self.clock.now(), actual, completed=True)
        self._elapsed_before_run = actual
        self._run_anchor = None
        self.state = "completed"
        return changed

    def cancel(self):
        if self.state not in ("running", "paused") or self.recovery_required:
            return False
        changed = self.db.end_break(self.break_id, self.clock.now(), self.elapsed_seconds, completed=False)
        self._run_anchor = None
        self.state = "cancelled"
        return changed

    def tick(self):
        if self.state == "running" and not self.recovery_required and self.remaining_seconds <= 0:
            return self.finish()
        return False

    def checkpoint(self):
        if self.state == "running" and not self.recovery_required:
            self.db.update_break(self.break_id, state="running", elapsed_seconds=min(self.elapsed_seconds, self.planned_seconds),
                                 run_started_at=self.clock.now(), updated_at=self.clock.now())

    def confirm_recovery(self, choice):
        if not self.recovery_required or choice not in ("resume", "discard"):
            raise ValueError("Choose resume or discard")
        self.recovery_required = False
        self.state = "paused"
        self.db.update_break(self.break_id, state="paused", elapsed_seconds=self._elapsed_before_run,
                             run_started_at="", updated_at=self.clock.now())
        if choice == "discard":
            self.cancel()
