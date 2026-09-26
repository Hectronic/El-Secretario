from src.app.pomodoro.service import PomodoroService
from src.database import DBManager


class Clock:
    def __init__(self):
        self.elapsed = 0.0
        self.wall = "2026-09-25T09:00:00+00:00"

    def monotonic(self):
        return self.elapsed

    def now(self):
        return self.wall


def test_pause_excludes_time_and_completes_once(tmp_path):
    clock = Clock()
    db = DBManager(str(tmp_path / "focus.sqlite"))
    notices = []
    service = PomodoroService(db, clock=clock, notify=lambda title, body: notices.append((title, body)))
    service.start("Focus", ["Work"], 100)
    clock.elapsed = 40
    service.pause()
    clock.elapsed = 1000
    service.resume()
    clock.elapsed = 1060
    service.tick()
    service.tick()

    assert service.state == "completed"
    assert db.fetch_pomodoro(service.pomodoro_id)["elapsed_seconds"] == 100
    assert len(db.fetch_timeline()) == 1
    assert len(notices) == 1


def test_overdue_recovery_requires_explicit_choice(tmp_path):
    clock = Clock()
    db = DBManager(str(tmp_path / "recovery.sqlite"))
    first = PomodoroService(db, clock=clock)
    first.start("Focus", [], 10)
    clock.wall = "2026-09-25T10:00:00+00:00"
    second = PomodoroService(db, clock=clock)
    assert second.recovery_required
    assert db.fetch_pomodoro(first.pomodoro_id)["state"] == "running"
    assert db.fetch_timeline() == []
    second.confirm_recovery("discard")
    assert db.fetch_timeline() == []


def test_recovery_can_complete_explicitly_and_edits_reach_timeline(tmp_path):
    clock = Clock()
    db = DBManager(str(tmp_path / "complete-recovery.sqlite"))
    first = PomodoroService(db, clock=clock)
    first.start("Old title", ["Draft"], 10)
    first.update_metadata("New title", ["Final"])
    first.checkpoint()

    restarted = PomodoroService(db, clock=clock)
    assert restarted.recovery_required
    assert db.fetch_timeline() == []
    restarted.confirm_recovery("complete")
    event = db.fetch_timeline()[0]
    assert event["title_snapshot"] == "New title"
    assert event["tags_snapshot"] == ["Final"]
    assert db.fetch_pomodoro(restarted.pomodoro_id)["state"] == "completed"
