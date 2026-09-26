"""Qt lifecycle adapter for the Qt-independent meeting scheduler."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class MeetingSchedulerRuntime(QObject):
    reminder_due = pyqtSignal(dict)
    catch_up_available = pyqtSignal(dict)
    scheduler_error = pyqtSignal(str)

    def __init__(self, scheduler, parent=None, *, interval_ms=15_000):
        super().__init__(parent)
        self.scheduler = scheduler
        self.timer = QTimer(self)
        self.timer.setInterval(max(1000, int(interval_ms)))
        self.timer.timeout.connect(self.poll)

    def start(self, *, poll_immediately=True):
        self.timer.start()
        if poll_immediately:
            QTimer.singleShot(0, self.poll)

    def poll(self, *, now=None):
        try:
            result = self.scheduler.tick(now=now)
        except Exception as error:
            self.scheduler_error.emit(str(error))
            return
        for occurrence in result["reminders"]:
            self.reminder_due.emit(occurrence)
        if result.get("catch_up"):
            self.catch_up_available.emit(result["catch_up"])

    def stop(self):
        self.timer.stop()
