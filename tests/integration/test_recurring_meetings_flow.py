from datetime import datetime, timezone

from PyQt6.QtCore import QObject, pyqtSignal

from src.app.scheduling.scheduler import MeetingScheduler
from src.database import DBManager
from src.ui.meetings.reminder_dialog import MeetingReminderDialog
from src.ui.meetings.scheduler_runtime import MeetingSchedulerRuntime
from src.ui.recording_in_progress_widget import RecordingInProgressWidget


class FakeRecorder(QObject):
    amplitude_changed = pyqtSignal(float)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.is_recording = False
        self.is_paused = False
        self.device_index = None
        self.capture_machine_audio = False

    def set_device(self, index):
        self.device_index = index

    def set_capture_machine_audio(self, enabled):
        self.capture_machine_audio = bool(enabled)

    def start(self):
        self.is_recording = True

    def stop(self):
        self.is_recording = False
        self.path.write_bytes(b"fake-wave-data")
        return str(self.path)

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False


def test_persisted_template_reminder_starts_capture_and_saves_occurrence_provenance(qtbot, tmp_path):
    now = datetime(2026, 9, 25, 7, 45, tzinfo=timezone.utc)
    db = DBManager(str(tmp_path / "scheduled-meeting.sqlite"))
    template_id = db.create_template({
        "title": "Release planning",
        "tags": ["Work", "Release"],
        "timezone": "Europe/Madrid",
        "local_start_time": "10:00",
        "expected_duration_seconds": 5400,
        "reminder_lead_seconds": 900,
        "recurrence_kind": "daily",
        "recurrence_payload": {"version": 1},
        "starts_on": "2026-09-25",
    }, now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)
    runtime = MeetingSchedulerRuntime(scheduler, interval_ms=60_000)
    reminders = []
    runtime.reminder_due.connect(reminders.append)
    runtime.poll(now=now)
    runtime.poll(now=now)
    assert len(reminders) == 1
    occurrence = reminders[0]
    assert occurrence["recurring_meeting_id"] == template_id
    assert occurrence["state"] == "notified"

    recorder = FakeRecorder(tmp_path / "release-planning.wav")
    capture = {}

    def start_from_user_action(occurrence_id):
        started = scheduler.start(occurrence_id, now=now)
        config = {
            "meeting_occurrence_id": occurrence_id,
            "title": started["title"],
            "tags": ", ".join(started["tags"]),
            "model": "base",
        }
        widget = RecordingInProgressWidget(recorder=recorder, config=config, persistence=db)
        capture["widget"] = widget

        def save_record(path, finished_config):
            record_id = db.save(
                path, "", 0, title=finished_config["title"],
                meeting_occurrence_id=finished_config["meeting_occurrence_id"],
                meeting_tags=finished_config["tags"],
            )
            db.update_tags(record_id, finished_config["tags"])
            capture["record_id"] = record_id

        widget.finished.connect(save_record)

    card = MeetingReminderDialog(occurrence)
    qtbot.addWidget(card)
    card.start_requested.connect(start_from_user_action)
    card.start_button.click()

    widget = capture["widget"]
    assert widget.recording_started is True
    assert widget.title_input.text() == "Release planning"
    assert widget.tags_input.text() == "Work, Release"
    widget.finish_recording()

    saved = db.fetch_record(capture["record_id"])
    linked = db.meetings.get_occurrence(occurrence["id"])
    assert saved["title"] == "Release planning"
    assert saved["tags"] == "Work, Release"
    assert saved["meeting_occurrence_id"] == occurrence["id"]
    assert linked["state"] == "completed"
    assert linked["recording_id"] == capture["record_id"]
    runtime.stop()
