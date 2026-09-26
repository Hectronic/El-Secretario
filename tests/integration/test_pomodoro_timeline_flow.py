from pathlib import Path

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtWidgets import QComboBox, QMainWindow, QTabWidget

from src.app.pomodoro.service import PomodoroService
from src.database import DBManager
from src.ui.pomodoro.widget import PomodoroWidget
from src.ui.timeline.widget import TimelineWidget
from src.ui.main_window.productivity import ProductivityCoordinator
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator
from types import SimpleNamespace


class Clock:
    elapsed = 0.0

    def monotonic(self):
        return self.elapsed

    def now(self):
        return "2026-09-25T09:00:00+00:00"


class Recorder:
    def __init__(self, path):
        self.path = path
        self.is_recording = False

    def start(self):
        self.is_recording = True

    def stop(self):
        self.is_recording = False
        self.path.write_bytes(b"audio-double")
        return str(self.path)

    def get_duration(self, _path):
        return 12


def test_focus_notes_and_timeline_cross_real_sqlite_qt_boundaries(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "app.sqlite"))
    clock = Clock()
    # Keep note timestamps in the same controlled time domain as the focus
    # session, so date filtering does not depend on the machine's current day.
    monkeypatch.setattr("src.persistence.productivity.now_iso", clock.now)
    service = PomodoroService(db, clock=clock, notify=lambda *_args: (_ for _ in ()).throw(RuntimeError("no tray")))
    widget = PomodoroWidget(service, db, recorder=Recorder(tmp_path / "capture.wav"),
                            audio_dir=tmp_path / "audio")
    qtbot.addWidget(widget)
    changed = []
    widget.activity_changed.connect(lambda: changed.append(True))
    widget.title_input.setText("Deep work")
    widget.tags_input.setText("Work")
    widget.start_button.click()
    assert service.state == "running"

    widget.note_title.setText("Outline")
    widget.note_body.setPlainText("Draft the outline")
    widget.save_note_button.click()
    widget.note_title.setText("Idea aloud")
    widget.audio_button.click()
    widget.audio_button.click()
    assert widget.audio.active is False
    assert widget._audio_transcription is None

    clock.elapsed = 1500
    service.tick()
    widget.refresh()
    assert service.state == "completed"
    assert "Completed" in widget.time_label.text()
    assert len(changed) == 3
    assert {note["kind"] for note in db.fetch_productivity_notes(service.pomodoro_id)} == {"text", "audio"}

    timeline = TimelineWidget(db)
    qtbot.addWidget(timeline)
    timeline.set_global_filters(None, QDate(2026, 9, 25), "Work")
    assert timeline.list_widget.count() == 3
    sources = []
    timeline.source_requested.connect(lambda kind, source_id: sources.append((kind, source_id)))
    timeline._open_item(timeline.list_widget.item(0))
    assert sources[0][0] in {"pomodoro", "text_note", "audio_note"}
    timeline.set_global_filters(None, QDate(2026, 9, 24), "Work")
    assert timeline.list_widget.count() == 0


def test_timeline_week_and_note_tag_filters(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "week.sqlite"))
    db.create_productivity_note("text", "A", ["Ideas"], body="a",
                                captured_at="2026-09-22T10:00:00+00:00")
    db.create_productivity_note("text", "B", ["Other"], body="b",
                                captured_at="2026-09-30T10:00:00+00:00")
    timeline = TimelineWidget(db)
    qtbot.addWidget(timeline)
    timeline.set_global_filters(QDate(2026, 9, 21), None, "Ideas")
    assert timeline.list_widget.count() == 1
    assert "A" in timeline.list_widget.item(0).text()


def test_window_coordinator_keeps_timer_after_tab_closes_and_reports_completion(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "window.sqlite"))
    window = QMainWindow()
    qtbot.addWidget(window)
    window.db = db
    window.central_tabs = QTabWidget(window)
    window.setCentralWidget(window.central_tabs)
    window.tag_filter_combo = QComboBox()
    window.tag_filter_combo.addItems(["All", "Work"])
    window.current_week_monday = None
    window.current_date_filter = None
    window.recorder = type("RecorderState", (), {"is_recording": False})()
    statuses = []
    window.handle_status_message = statuses.append
    window.system_tray_manager = None
    coordinator = ProductivityCoordinator(window)
    clock = Clock()
    coordinator.service.clock = clock
    widget = coordinator.open_pomodoro()
    widget.title_input.setText("Window work")
    widget.tags_input.setText("Work")
    widget.start_button.click()
    window.central_tabs.removeTab(window.central_tabs.indexOf(widget))
    widget.cleanup()
    widget.deleteLater()
    clock.elapsed = 1500
    coordinator._tick()

    assert db.fetch_pomodoro(coordinator.service.pomodoro_id)["state"] == "completed"
    assert statuses == ["Pomodoro complete: Window work"]
    window.tag_filter_combo.setCurrentText("Work")
    timeline = coordinator.open_timeline()
    assert timeline.list_widget.count() == 1
    coordinator.cleanup()


def test_cancelling_audio_note_does_not_cancel_focus(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "cancel-audio.sqlite"))
    service = PomodoroService(db, clock=Clock())
    widget = PomodoroWidget(service, db, recorder=Recorder(tmp_path / "discard.wav"),
                            audio_dir=tmp_path / "audio")
    qtbot.addWidget(widget)
    widget.title_input.setText("Focus")
    widget.start_button.click()
    widget.note_title.setText("Discard me")
    widget.audio_button.click()
    assert widget.cancel_audio_button.isEnabled()
    widget.cancel_audio_button.click()

    assert service.state == "running"
    assert db.fetch_productivity_notes(service.pomodoro_id) == []
    assert not (tmp_path / "discard.wav").exists()
    widget.cleanup()


def test_sidebar_sync_updates_open_timeline_with_real_qt_and_sqlite(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "filter-sync.sqlite"))
    db.create_productivity_note("text", "Workday", ["Work"], body="Done",
                                captured_at="2026-09-25T10:00:00+00:00")
    window = QMainWindow()
    qtbot.addWidget(window)
    window.central_tabs = QTabWidget(window)
    window.setCentralWidget(window.central_tabs)
    window.tag_filter_combo = QComboBox()
    window.tag_filter_combo.addItems(["All", "Work"])
    window.current_week_monday = None
    window.current_date_filter = "2026-09-24"
    window.floating_chat_hosts = []
    timeline = TimelineWidget(db)
    window.central_tabs.addTab(timeline, "Timeline")
    coordinator = SidebarSyncCoordinator(window)
    coordinator.sync_active_tabs()
    assert timeline.list_widget.count() == 0
    window.current_date_filter = "2026-09-25"
    window.tag_filter_combo.setCurrentText("Work")
    coordinator.sync_active_tabs()
    assert timeline.list_widget.count() == 1


def test_opt_in_audio_transcription_updates_saved_note(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "transcription.sqlite"))
    started_paths = []

    class TranscriptionDouble:
        def start(self, path, on_finished, _on_error):
            started_paths.append(path)
            QTimer.singleShot(0, lambda: on_finished({"text": "Spoken idea"}))
            return SimpleNamespace(preflight_error=None)

        def cleanup(self):
            pass

    monkeypatch.setattr("src.ui.notebooks.transcription_runtime.NotebookTranscriptionRuntime", TranscriptionDouble)
    widget = PomodoroWidget(PomodoroService(db, clock=Clock()), db,
                            recorder=Recorder(tmp_path / "voice.wav"), audio_dir=tmp_path / "audio")
    qtbot.addWidget(widget)
    widget.note_title.setText("Voice note")
    widget.transcribe_audio.setChecked(True)
    widget.audio_button.click()
    widget.audio_button.click()
    event = db.fetch_timeline()[0]
    assert started_paths == [db.fetch_productivity_note(event["source_id"])["audio_ref"]]
    qtbot.waitUntil(lambda: db.fetch_productivity_note(event["source_id"])["transcription"] == "Spoken idea")
    widget.cleanup()
