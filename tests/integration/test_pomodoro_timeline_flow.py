from pathlib import Path
from datetime import datetime, timezone

from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtWidgets import QComboBox, QMainWindow, QTabWidget

from src.app.pomodoro.service import PomodoroService
from src.app.scheduling.scheduler import MeetingScheduler
from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.pomodoro.widget import PomodoroWidget
from src.ui.timeline.widget import TimelineWidget
from src.ui.main_window.productivity import ProductivityCoordinator
from src.ui.main_window.sidebar_sync import SidebarSyncCoordinator
from src.ui.chat.add_context_dialog import AddContextDialog
from src.ui.chat.context_builder import build_chat_context_text, build_chat_session_contexts
from src.ui.welcome.pomodoro_labels import pomodoro_labels
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
    widget.secondary_group.setChecked(True)
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


def test_timer_first_view_starts_with_valid_default_title_and_collapsed_details(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "timer-first.sqlite"))
    service = PomodoroService(db, clock=Clock())
    widget = PomodoroWidget(service, db, recorder=Recorder(tmp_path / "timer-first.wav"),
                            audio_dir=tmp_path / "audio")
    qtbot.addWidget(widget)
    assert widget.secondary_group.isChecked() is False
    assert widget.title_input.isHidden() or not widget.title_input.isVisibleTo(widget)
    widget.secondary_group.setChecked(True)
    assert widget.title_input.isVisibleTo(widget)
    widget.secondary_group.setChecked(False)
    assert widget.title_input.text() == pomodoro_labels()["quick_focus"]
    widget.start_button.click()
    assert service.state == "running"
    assert db.fetch_active_pomodoro()["title"] == pomodoro_labels()["quick_focus"]


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


def test_activity_timeline_composes_summary_references_with_pomodoros(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "activity.sqlite"))
    db.save_daily_summary("2026-09-25", "Daily content", "Work")
    weekly_id = db.save_weekly_summary("2026-09-27", "Weekly content", "Work")
    now = datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc)
    db.create_template({
        "title": "Planning meeting", "tags": ["Work"], "timezone": "Europe/Madrid",
        "local_start_time": "10:00", "expected_duration_seconds": 3600,
        "reminder_lead_seconds": 600, "recurrence_kind": "daily",
        "recurrence_payload": {"version": 1}, "starts_on": "2026-09-25", "occurrence_limit": 1,
    }, now=now)
    scheduler = MeetingScheduler(db.meetings, clock=lambda: now)
    occurrence_id = scheduler.materialize(now=now)[0]
    scheduler.start(occurrence_id, now=now)
    service = PomodoroService(db, clock=Clock())
    service.start("Focus item", "Work", 60)
    service.finish()
    timeline = TimelineWidget(db)
    qtbot.addWidget(timeline)
    timeline.set_global_filters(None, None, "Work")
    assert timeline.list_widget.count() == 4
    entries = [timeline.list_widget.item(i) for i in range(timeline.list_widget.count())]
    event_types = [entry.data(Qt.ItemDataRole.UserRole)[0] for entry in entries]
    assert event_types == ["weekly_summary", "daily_summary", "meeting_occurrence", "pomodoro"]
    selected = next(entry for entry in entries if entry.data(Qt.ItemDataRole.UserRole)[0] == "weekly_summary")
    source_id = selected.data(Qt.ItemDataRole.UserRole)[1]
    assert db.fetch_weekly_summary_by_id(source_id)["id"] == weekly_id
    db.save_weekly_summary("2026-09-27", "Updated weekly content", "Work")
    timeline.refresh()
    assert timeline.list_widget.count() == 4


def test_general_activity_search_finds_pomodoro_notes_and_summaries(tmp_path):
    db = DBManager(str(tmp_path / "search-activity.sqlite"))
    service = PomodoroService(db, clock=Clock())
    service.start("Design sprint", "Roadmap", 60)
    db.create_productivity_note("text", "Sprint notes", ["Roadmap"], body="Review milestones",
                                pomodoro_id=service.pomodoro_id, captured_at="2026-09-25T10:00:00+00:00")
    db.save_daily_summary("2026-09-25", "Roadmap delivery recap")
    found = db.search_activity_sources("Roadmap")
    assert {row["event_type"] for row in found} == {"pomodoro", "text_note", "daily_summary"}
    note = next(row for row in found if row["event_type"] == "text_note")
    assert "Review milestones" in note["text"]


def test_local_general_search_finds_existing_record_and_meeting_content(tmp_path):
    db = DBManager(str(tmp_path / "meeting-search.sqlite"))
    db.save("", "stakeholders approved scope", 0, title="Review", recording_notes="Budget confirmed")
    now = datetime(2026, 9, 25, 7, 0, tzinfo=timezone.utc)
    db.create_template({
        "title": "Planning meeting", "tags": ["Roadmap"], "timezone": "Europe/Madrid",
        "local_start_time": "10:00", "expected_duration_seconds": 3600,
        "reminder_lead_seconds": 600, "recurrence_kind": "daily",
        "recurrence_payload": {"version": 1}, "starts_on": "2026-09-25", "occurrence_limit": 1,
    }, now=now)
    MeetingScheduler(db.meetings, clock=lambda: now).materialize(now=now)
    assert any(row["event_type"] == "record" and "stakeholders" in row["text"]
               for row in db.search_activity_sources("stakeholders"))
    assert any(row["event_type"] == "meeting_occurrence"
               for row in db.search_activity_sources("Roadmap"))


def test_explicit_chat_picker_to_sqlite_pomodoro_context(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat-pomodoro.sqlite"))
    service = PomodoroService(db, clock=Clock())
    service.start("Design review", "Planning", 60)
    pomodoro_id = service.pomodoro_id
    db.create_productivity_note("text", "Decisions", ["Planning"], body="Approve milestones",
                                pomodoro_id=pomodoro_id, captured_at="2026-09-25T09:15:00+00:00")
    service.finish()
    notebook_db = NotebookDBManager(str(tmp_path / "chat-notebooks.sqlite"))
    dialog = AddContextDialog(db, notebook_db)
    qtbot.addWidget(dialog)
    dialog.tabs.setCurrentWidget(dialog.pomodoro_list)
    dialog.pomodoro_list.setCurrentRow(0)
    dialog.on_accept()
    selected_id = dialog.selected_context["value"]

    class Panel:
        current_week_monday = None
        current_date_filter = None
        def get_active_notebooks(self): return []
        def get_active_tags(self): return []

    class RagDouble:
        def search(self, *_args, **_kwargs): return []

    context = build_chat_context_text(db, notebook_db, RagDouble(), "question", Panel(), set(),
                                      forced_pomodoro_ids={selected_id})
    assert "Design review" in context
    assert "2026-09-25" in context
    assert "Planning" in context
    assert "Approve milestones" in context
    assert {"type": "pomodoro", "value": selected_id} in build_chat_session_contexts(Panel(), set(), {selected_id})


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
    widget.secondary_group.setChecked(True)
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
    widget.secondary_group.setChecked(True)
    widget.note_title.setText("Voice note")
    widget.transcribe_audio.setChecked(True)
    widget.audio_button.click()
    widget.audio_button.click()
    event = db.fetch_timeline()[0]
    assert started_paths == [db.fetch_productivity_note(event["source_id"])["audio_ref"]]
    qtbot.waitUntil(lambda: db.fetch_productivity_note(event["source_id"])["transcription"] == "Spoken idea")
    widget.cleanup()


def test_selected_pomodoro_preserves_chat_tag_filters(qtbot, tmp_path):
    from src.ui.context_manager_panel import ContextManagerPanel

    db = DBManager(str(tmp_path / "tag-context.sqlite"))
    notebooks = NotebookDBManager(str(tmp_path / "tag-notebooks.sqlite"))
    selected = db.save_note("Selected operations", "Keep operations context")
    other = db.save_note("Other planning", "Exclude planning record")
    db.update_tags(selected, "Operations")
    db.update_tags(other, "Planning")
    service = PomodoroService(db, clock=Clock())
    service.start("Explicit focus", "Planning", 60)
    panel = ContextManagerPanel(db, notebooks)
    qtbot.addWidget(panel)
    panel.apply_state({"active_global_tags": ["Operations"]})
    context = build_chat_context_text(db, notebooks, None, "question", panel, set(),
                                      forced_pomodoro_ids={service.pomodoro_id})
    assert "Explicit focus" in context
    assert "Keep operations context" in context
    assert "Exclude planning record" not in context
