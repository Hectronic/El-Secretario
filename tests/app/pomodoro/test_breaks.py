from src.app.pomodoro.breaks import BreakService
from src.database import DBManager


class Clock:
    elapsed = 0

    def monotonic(self):
        return self.elapsed

    def now(self):
        return "2026-09-25T09:00:00+00:00"


def test_break_is_separate_from_focus_and_hidden_by_default(tmp_path):
    db = DBManager(str(tmp_path / "break.sqlite"))
    clock = Clock()
    service = BreakService(db, clock=clock)
    service.start("short", 300)
    clock.elapsed = 300
    service.tick()
    assert service.state == "completed"
    assert db.fetch_timeline() == []
    assert len(db.fetch_timeline(show_breaks=True)) == 1
    assert db.fetch_timeline(show_breaks=True)[0]["event_type"] == "break"


def test_break_recovery_is_explicit(tmp_path):
    db = DBManager(str(tmp_path / "break.sqlite"))
    first = BreakService(db, clock=Clock())
    first.start("long", 900)
    second = BreakService(db, clock=Clock())
    assert second.recovery_required
    assert db.fetch_timeline(show_breaks=True) == []
    second.confirm_recovery("discard")
    assert db.fetch_active_break() is None
