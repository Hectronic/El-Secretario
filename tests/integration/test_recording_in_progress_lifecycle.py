from PyQt6.QtCore import QObject, QSettings, pyqtSignal

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


class _TrayPort:
    def __init__(self):
        self.stop_callback = None
        self.pause_callback = None
        self.cancel_callback = None
        self.durations = []
        self.paused = []
        self.notifications = []
        self.cleaned = False

    def start(self, stop_callback, pause_callback, cancel_callback):
        self.stop_callback = stop_callback
        self.pause_callback = pause_callback
        self.cancel_callback = cancel_callback
        return True

    def update_duration(self, seconds):
        self.durations.append(seconds)

    def set_paused(self, paused):
        self.paused.append(paused)

    def notify(self, title, message):
        self.notifications.append((title, message))
        return True

    def cleanup(self):
        self.cleaned = True


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


def test_tray_stop_action_uses_capture_completion_once_and_cleans_up(qtbot, monkeypatch):
    monkeypatch.setattr("src.ui.recording_in_progress.widget.DBManager", _TagDatabase)
    recorder = _Recorder()
    tray = _TrayPort()
    widget = RecordingInProgressWidget(recorder=recorder, tray_port=tray)
    qtbot.addWidget(widget)

    widget.update_timer()
    assert tray.durations == [1]
    with qtbot.waitSignal(widget.finished, timeout=1000) as emitted:
        tray.stop_callback()

    assert emitted.args[0] == "capture.wav"
    assert recorder.stop_calls == 1
    assert tray.cleaned is True


def test_tray_pause_resume_and_cancel_use_existing_capture_lifecycle(qtbot, monkeypatch):
    monkeypatch.setattr("src.ui.recording_in_progress.widget.DBManager", _TagDatabase)
    recorder = _Recorder()
    tray = _TrayPort()
    widget = RecordingInProgressWidget(recorder=recorder, tray_port=tray)
    qtbot.addWidget(widget)

    tray.pause_callback()
    assert recorder.is_paused is True
    assert tray.paused == [True]
    tray.pause_callback()
    assert recorder.is_paused is False
    assert tray.paused == [True, False]

    with qtbot.waitSignal(widget.cancelled, timeout=1000):
        tray.cancel_callback()

    assert recorder.stop_calls == 1
    assert tray.cleaned is True
    tray.cancel_callback()
    assert recorder.stop_calls == 1


def test_silence_warning_recovers_on_activity_without_default_auto_stop(qtbot, monkeypatch):
    monkeypatch.setattr("src.ui.recording_in_progress.widget.DBManager", _TagDatabase)
    settings = QSettings("Hectronic", "Secretario")
    settings.setValue("recording_guardian/silence_warning_seconds", 1)
    settings.setValue("recording_guardian/auto_stop_after_silence", False)
    tray = _TrayPort()
    recorder = _Recorder()
    widget = RecordingInProgressWidget(recorder=recorder, tray_port=tray)
    qtbot.addWidget(widget)

    widget.update_timer()
    recorder.amplitude_changed.emit(0.2)
    widget.update_timer()

    assert [title for title, _ in tray.notifications] == ["No audio detected", "No audio detected"]
    assert recorder.stop_calls == 0
    widget.cancel_recording()
    assert tray.cleaned is True
    settings.remove("recording_guardian/silence_warning_seconds")
    settings.remove("recording_guardian/auto_stop_after_silence")
