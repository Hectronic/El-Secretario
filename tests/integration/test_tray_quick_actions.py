from datetime import datetime, timedelta, timezone
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QSystemTrayIcon

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.main_window import MainWindow
from src.ui.note_widget import NoteWidget
from src.ui.notebook_widget import NotebookWidget
from src.ui.notebooks.transcription_runtime import NotebookTranscriptionStartResult
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.welcome_widget import WelcomeWidget


class _Recorder(QObject):
    amplitude_changed = pyqtSignal(float)
    devices = [(0, "Test microphone")]

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.is_recording = False
        self.is_paused = False
        self.device_index = None
        self.capture_machine_audio = False
        self.starts = 0
        self.stops = 0

    @classmethod
    def get_input_devices(cls):
        return list(cls.devices)

    def set_device(self, index):
        self.device_index = index

    def set_capture_machine_audio(self, enabled):
        self.capture_machine_audio = bool(enabled)

    def start(self):
        self.starts += 1
        self.is_recording = True
        self.is_paused = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.stops += 1
        self.is_recording = False
        self.path.write_bytes(b"audio double")
        return str(self.path)

    def get_duration(self, _path):
        return 1.0


class _CompressionService(QObject):
    compression_finished = pyqtSignal(int, str)
    compression_failed = pyqtSignal(int, str)

    def start_compression(self, *_args):
        pass

    def release_source(self, *_args):
        pass


def _window(qtbot, tmp_path, monkeypatch, *, devices=None, tray_available=True):
    db = DBManager(str(tmp_path / "main.sqlite"))
    notebooks = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    available_devices = [(0, "Test microphone")] if devices is None else devices
    recorder_type = type("TestRecorder", (_Recorder,), {"devices": available_devices})
    recorder = recorder_type(tmp_path / "capture.wav")
    monkeypatch.setattr("src.ui.main_window.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.summary_queue.manager.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.main_window.NotebookDBManager", lambda: notebooks)
    monkeypatch.setattr("src.ui.main_window.Recorder", lambda: recorder)
    monkeypatch.setattr("src.ui.welcome_widget.Recorder", recorder_type)
    monkeypatch.setattr(
        QSystemTrayIcon, "isSystemTrayAvailable", lambda: tray_available
    )
    monkeypatch.setattr(
        "src.ui.main_window.runtime_startup.RuntimeStartupCoordinator.initialize_rag_from_settings",
        lambda self: setattr(self.window, "rag", None),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    return window, db, notebooks, recorder


def _close(window):
    window._force_quit = True
    window.close()


def test_tray_start_recording_preflights_and_declined_cancel_keeps_capture(qtbot, tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    window, _db, _notebooks, recorder = _window(qtbot, tmp_path, monkeypatch)
    try:
        window.system_tray_manager.start_recording_action.trigger()

        active = window.tray_actions._current_recording()
        assert isinstance(active, RecordingInProgressWidget)
        assert active.recording_started
        assert recorder.starts == 1
        assert window.system_tray_manager._is_recording
        assert window.system_tray_manager.pause_recording_action.isVisible()

        monkeypatch.setattr(
            "src.ui.main_window.tray_actions.QMessageBox.question",
            lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
        )
        assert window.tray_actions.dispatch("cancel_recording") is False
        assert recorder.is_recording is True
        assert recorder.stops == 0

        monkeypatch.setattr(
            "src.ui.main_window.tray_actions.QMessageBox.question",
            lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
        )
        assert window.tray_actions.dispatch("cancel_recording") is True
        assert recorder.is_recording is False
        assert recorder.stops == 1
    finally:
        _close(window)


def test_tray_stop_saves_recording_once_through_main_coordinator(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.ui.main_window.recording_tabs.AudioCompressionService", _CompressionService
    )
    # Replace only the external transcription launch. The Qt completion signal,
    # recording coordinator, and SQLite persistence remain real.
    monkeypatch.setattr(
        "src.ui.recording_widget.RecordingWidget.start_transcription_with_config",
        lambda *_args, **_kwargs: None,
    )
    window, db, _notebooks, recorder = _window(qtbot, tmp_path, monkeypatch)
    try:
        window.system_tray_manager.start_recording_action.trigger()
        active = window.tray_actions._current_recording()
        active.title_input.setText("Tray saved capture")

        window.system_tray_manager.stop_recording_action.trigger()

        records = db.fetch_all()
        assert len(records) == 1
        assert records[0]["title"] == "Tray saved capture"
        assert recorder.stops == 1
        assert recorder.is_recording is False
        assert window.tray_actions.stop_recording() is False
        assert len(db.fetch_all()) == 1
    finally:
        _close(window)


def test_tray_start_without_microphone_shows_recoverable_setup(qtbot, tmp_path, monkeypatch):
    window, _db, _notebooks, recorder = _window(qtbot, tmp_path, monkeypatch, devices=[])
    try:
        window.welcome_widget.sys_audio_check.setChecked(False)
        window.system_tray_manager.start_recording_action.trigger()

        assert recorder.starts == 0
        assert recorder.is_recording is False
        assert isinstance(window.central_tabs.currentWidget(), WelcomeWidget)
        assert "No microphone is available" in window.task_status_label.text()
    finally:
        _close(window)


def test_main_ui_keeps_capture_controls_when_system_tray_is_unavailable(qtbot, tmp_path, monkeypatch):
    window, _db, _notebooks, recorder = _window(
        qtbot, tmp_path, monkeypatch, tray_available=False
    )
    try:
        welcome = window.welcome_widget
        assert window.system_tray_manager._menu is None
        assert window.system_tray_manager._tray_icon is None
        assert not welcome.rec_btn.isHidden()
        assert not welcome.new_note_top_btn.isHidden()
        assert not welcome.settings_btn.isHidden()

        welcome.rec_btn.click()
        assert recorder.starts == 1
        assert window.tray_actions._current_recording().recording_started
    finally:
        _close(window)


def test_tray_quick_text_note_uses_note_widget_and_main_sqlite(qtbot, tmp_path, monkeypatch):
    window, db, _notebooks, _recorder = _window(qtbot, tmp_path, monkeypatch)
    try:
        window.system_tray_manager.new_text_note_action.trigger()
        note = window.central_tabs.currentWidget()
        assert isinstance(note, NoteWidget)
        assert note.title_input.text() == "Quick note"
        assert note.tabs.isTabVisible(1) is False
        assert note.summarize_btn.isHidden()

        note.title_input.setText("Decision log")
        note.content_editor.setPlainText("Keep the existing capture coordinator.")
        note.save_note()
        saved = db.fetch_all()
        assert len(saved) == 1
        assert saved[0]["type"] == "note"
        assert saved[0]["title"] == "Decision log"
    finally:
        _close(window)


def test_tray_audio_note_uses_notebook_capture_and_persistence(qtbot, tmp_path, monkeypatch):
    class NoTranscriptionRuntime:
        def start(self, *_args):
            return NotebookTranscriptionStartResult(
                started=False, preflight_error="Transcription omitted in this hardware-edge test."
            )

        def cleanup(self):
            pass

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "src.ui.notebook_widget.NotebookTranscriptionRuntime", NoTranscriptionRuntime
    )
    monkeypatch.setattr("src.ui.notebook_widget.QMessageBox.critical", lambda *_args: None)
    window, _db, notebooks, recorder = _window(qtbot, tmp_path, monkeypatch)
    notebook_id = notebooks.create_notebook("Research")
    try:
        window.system_tray_manager.new_audio_note_action.trigger()

        widget = window.central_tabs.currentWidget()
        assert isinstance(widget, NotebookWidget)
        assert widget.notebook_id == notebook_id
        assert recorder.is_recording is True
        assert window.system_tray_manager._is_recording is True
        assert window.tray_actions._active_audio_note()[1] is widget

        assert window.tray_actions.stop_recording() is True
        entries = notebooks.get_entries(notebook_id)
        assert len(entries) == 1
        assert entries[0]["type"] == "audio"
        assert Path(entries[0]["file_path"]).exists()
        assert recorder.is_recording is False
        assert window.system_tray_manager._is_recording is False
    finally:
        _close(window)


def test_tray_meeting_actions_share_persistent_occurrence_and_prepared_capture(qtbot, tmp_path, monkeypatch):
    window, db, _notebooks, recorder = _window(qtbot, tmp_path, monkeypatch)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        template_ids = []
        for title, minute in (("Release planning", now.minute + 15), ("Operations sync", now.minute + 30)):
            day_offset, minute_of_day = divmod(now.hour * 60 + minute, 24 * 60)
            hour, minute_of_day = divmod(minute_of_day, 60)
            start_time = f"{hour:02d}:{minute_of_day:02d}"
            template_ids.append(db.create_template({
                "title": title,
                "tags": ["Work", "Release"] if title == "Release planning" else ["Operations"],
                "timezone": "UTC",
                "local_start_time": start_time,
                "expected_duration_seconds": 1800,
                "reminder_lead_seconds": 3600,
                "recurrence_kind": "daily",
                "recurrence_payload": {"version": 1},
                "starts_on": (now.date() + timedelta(days=day_offset)).isoformat(),
            }, now=now))
        window.productivity.meeting_scheduler.materialize(now=now)
        window.productivity.meeting_scheduler.tick(now=now)
        notified = [
            item for template_id in template_ids
            for item in db.meetings.list_occurrences(template_id=template_id, states=("notified",))
        ]
        assert len(notified) == 2

        first = next(item for item in notified if item["title"] == "Release planning")
        second = next(item for item in notified if item["title"] == "Operations sync")
        first_id = int(first["id"])
        second_id = int(second["id"])
        assert window.tray_actions.start_meeting(first_id) is True
        active = window.tray_actions._current_recording()
        assert isinstance(active, RecordingInProgressWidget)
        assert active.recording_started
        assert active.config["meeting_occurrence_id"] == first_id
        assert active.title_input.text() == "Release planning"
        assert active.tags_input.text() == "Work, Release"
        assert "Recording · Release planning" in window.system_tray_manager.recording_status_action.text()
        assert db.meetings.get_occurrence(first_id)["state"] == "started"
        assert recorder.starts == 1

        assert window.tray_actions.snooze_meeting(second_id) is True
        assert db.meetings.get_occurrence(second_id)["state"] == "snoozed"
        assert window.tray_actions.dismiss_meeting(second_id) is True
        assert db.meetings.get_occurrence(second_id)["state"] == "dismissed"
    finally:
        _close(window)


def test_tray_meeting_without_microphone_keeps_occurrence_recoverable(qtbot, tmp_path, monkeypatch):
    window, db, _notebooks, recorder = _window(qtbot, tmp_path, monkeypatch, devices=[])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    try:
        template_id = db.create_template(
            {
                "title": "Planning",
                "tags": ["Work"],
                "timezone": "UTC",
                "local_start_time": "00:01",
                "expected_duration_seconds": 1800,
                "reminder_lead_seconds": 0,
                "recurrence_kind": "daily",
                "recurrence_payload": {"version": 1},
                "starts_on": (now - timedelta(days=2)).date().isoformat(),
            },
            now=now - timedelta(days=2),
        )
        window.productivity.meeting_scheduler.materialize(now=now)
        occurrence = db.meetings.list_occurrences(template_id=template_id, states=("missed",))[0]

        assert window.tray_actions.start_meeting(int(occurrence["id"])) is False
        assert db.meetings.get_occurrence(occurrence["id"])["state"] == "missed"
        assert recorder.starts == 0
        assert "No microphone is available" in window.task_status_label.text()
    finally:
        _close(window)
