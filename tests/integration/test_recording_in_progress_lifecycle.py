from PyQt6.QtCore import QObject, pyqtSignal

from src.database import DBManager
from src.ui.recording_in_progress_widget import RecordingInProgressWidget


class _TagDatabase:
    def get_all_tags(self):
        return ["planning"]


class _Recorder(QObject):
    amplitude_changed = pyqtSignal(float)

    def __init__(self, stop_result="capture.wav"):
        super().__init__()
        self.is_recording = False
        self.is_paused = False
        self.stop_result = stop_result
        self.stop_calls = 0

    def set_device(self, _value):
        pass

    def set_capture_machine_audio(self, _value):
        pass

    def start(self):
        self.is_recording = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.stop_calls += 1
        self.is_recording = False
        return self.stop_result


def test_active_recording_emits_normalized_completion_payload_and_cleans_signal(qtbot, monkeypatch):
    monkeypatch.setattr("src.ui.recording_in_progress.widget.DBManager", _TagDatabase)
    recorder = _Recorder()
    widget = RecordingInProgressWidget(
        recorder=recorder,
        config={"device_index": 1, "capture_system_audio": True},
    )
    qtbot.addWidget(widget)
    widget.title_input.setText("  Sprint planning  ")
    widget.tags_input.setText("planning")
    widget.notes_input.setPlainText("  Align owners. ")
    widget.task_input.setText("Ship summary")
    widget.add_quick_task()

    with qtbot.waitSignal(widget.finished, timeout=1000) as emitted:
        widget.finish_recording()

    file_path, payload = emitted.args
    assert file_path == "capture.wav"
    assert payload["title"] == "Sprint planning"
    assert payload["recording_notes"] == "Align owners."
    assert payload["pending_tasks"] == ["Ship summary"]
    assert recorder.stop_calls == 1
    assert widget.recording_started is False
    widget.vu_meter.setValue(0)
    recorder.amplitude_changed.emit(0.9)
    assert widget.vu_meter.value() == 0


def test_active_recording_cancel_stops_capture_and_emits_cancelled(qtbot, monkeypatch):
    monkeypatch.setattr("src.ui.recording_in_progress.widget.DBManager", _TagDatabase)
    recorder = _Recorder()
    widget = RecordingInProgressWidget(recorder=recorder)
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.cancelled, timeout=1000):
        widget.cancel_recording()

    assert recorder.stop_calls == 1
    assert widget.recording_started is False


def test_active_recording_uses_injected_sqlite_tags_and_emits_completion(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "capture.sqlite"))
    record_id = db.save("earlier.wav", "", 1.0, "Earlier")
    db.update_tags(record_id, "planning")
    recorder = _Recorder()
    widget = RecordingInProgressWidget(recorder=recorder, persistence=db)
    qtbot.addWidget(widget)

    assert widget.db is db
    assert widget.tags_input.all_tags == ["planning"]
    with qtbot.waitSignal(widget.finished, timeout=1000) as emitted:
        widget.finish_recording()

    assert emitted.args[0] == "capture.wav"
