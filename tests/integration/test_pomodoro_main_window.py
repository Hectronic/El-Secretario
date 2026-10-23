from unittest.mock import MagicMock
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QInputDialog, QSystemTrayIcon

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.main_window import MainWindow
from src.ui.pomodoro.widget import PomodoroWidget
from src.ui.timeline.widget import TimelineWidget
from src.ui.welcome.pomodoro_labels import pomodoro_labels
from src.ui.summary_viewer import SummaryViewerWidget


def test_main_window_buttons_open_focus_and_timeline_with_shared_sqlite(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "main.sqlite"))
    notebooks = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    monkeypatch.setattr("src.ui.main_window.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.summary_queue.manager.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.main_window.NotebookDBManager", lambda: notebooks)
    recorder = MagicMock()
    recorder.is_recording = False
    monkeypatch.setattr("src.ui.main_window.Recorder", lambda: recorder)

    def no_rag(self):
        self.window.rag = None

    monkeypatch.setattr("src.ui.main_window.runtime_startup.RuntimeStartupCoordinator.initialize_rag_from_settings", no_rag)
    window = MainWindow()
    qtbot.addWidget(window)
    try:
        window.open_pomodoro_btn.click()
        pomodoro = window.central_tabs.currentWidget()
        assert isinstance(pomodoro, PomodoroWidget)
        pomodoro.title_input.setText("Project planning")
        pomodoro.tags_input.setText("Work")
        pomodoro.start_button.click()
        assert db.fetch_active_pomodoro()["title"] == "Project planning"
        assert window.tag_filter_combo.findText("Work") >= 0

        pomodoro.finish_button.click()
        window.open_timeline_btn.click()
        timeline = window.central_tabs.currentWidget()
        assert isinstance(timeline, TimelineWidget)
        assert timeline.list_widget.count() == 1
        assert "Project planning" in timeline.list_widget.item(0).text()
    finally:
        window._force_quit = True
        window.close()


def test_tray_pomodoro_actions_persist_once_through_main_window(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "tray-main.sqlite"))
    notebooks = NotebookDBManager(str(tmp_path / "tray-notebooks.sqlite"))
    monkeypatch.setattr("src.ui.main_window.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.summary_queue.manager.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.main_window.NotebookDBManager", lambda: notebooks)
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    recorder = MagicMock()
    recorder.is_recording = False
    monkeypatch.setattr("src.ui.main_window.Recorder", lambda: recorder)
    monkeypatch.setattr(
        "src.ui.main_window.runtime_startup.RuntimeStartupCoordinator.initialize_rag_from_settings",
        lambda self: setattr(self.window, "rag", None),
    )
    monkeypatch.setattr(QInputDialog, "getText", lambda *_args, **_kwargs: ("Tray focus", True))
    window = MainWindow()
    qtbot.addWidget(window)
    try:
        window.system_tray_manager.start_pomodoro_action.trigger()
        assert db.fetch_active_pomodoro()["title"] == "Tray focus"

        window.system_tray_manager.finish_pomodoro_action.trigger()
        assert db.fetch_active_pomodoro() is None
        assert len(db.fetch_timeline()) == 1

        window.system_tray_manager.finish_pomodoro_action.trigger()
        assert len(db.fetch_timeline()) == 1
    finally:
        window._force_quit = True
        window.close()


def test_welcome_quick_start_uses_shared_service_and_reopens_active_timer(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "welcome-pomodoro.sqlite"))
    notebooks = NotebookDBManager(str(tmp_path / "welcome-notebooks.sqlite"))
    monkeypatch.setattr("src.ui.main_window.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.summary_queue.manager.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.main_window.NotebookDBManager", lambda: notebooks)
    recorder = MagicMock()
    recorder.is_recording = False
    monkeypatch.setattr("src.ui.main_window.Recorder", lambda: recorder)
    monkeypatch.setattr("src.ui.main_window.runtime_startup.RuntimeStartupCoordinator.initialize_rag_from_settings", lambda self: setattr(self.window, "rag", None))
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait(50)
    try:
        window.productivity.settings = MagicMock()
        window.productivity.settings.value.return_value = 40
        welcome = window.welcome_widget
        assert welcome.pomodoro_btn.isVisible()
        labels = pomodoro_labels()
        assert welcome.pomodoro_btn.accessibleName() == labels["start"]
        welcome._apply_layout_density(400)
        assert welcome.pomodoro_btn.isVisible()
        welcome.pomodoro_btn.setFocus()
        qtbot.keyClick(welcome.pomodoro_btn, Qt.Key.Key_Space)
        active = db.fetch_active_pomodoro()
        assert active["title"] == labels["quick_focus"]
        assert active["planned_seconds"] == 40 * 60
        widget = window.central_tabs.currentWidget()
        assert isinstance(widget, PomodoroWidget)
        assert widget.title_input.text() == labels["quick_focus"]
        assert welcome.pomodoro_btn.text().startswith(labels["open"])
        active_id = active["id"]
        welcome.pomodoro_btn.click()
        assert db.fetch_active_pomodoro()["id"] == active_id
        assert len(db.fetch_timeline()) == 0
        widget.pause_button.click()
        assert window.productivity.service.state == "paused"
        qtbot.waitUntil(lambda: labels["paused"] in welcome.pomodoro_btn.text())
        welcome.pomodoro_btn.click()
        assert window.productivity.service.state == "paused"
        assert db.fetch_active_pomodoro()["id"] == active_id
        widget.finish_button.click()
        widget.secondary_group.setChecked(True)
        widget.short_break_button.click()
        break_id = window.productivity.break_service.break_id
        assert db.fetch_active_break()["id"] == break_id
        widget.secondary_group.setChecked(False)
        welcome.pomodoro_btn.click()
        assert widget.secondary_group.isChecked()
        assert db.fetch_active_pomodoro() is None
        assert db.fetch_active_break()["id"] == break_id
    finally:
        window._force_quit = True
        window.close()


def test_welcome_quick_start_failure_keeps_service_idle_and_shows_feedback(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "welcome-failure.sqlite"))
    notebooks = NotebookDBManager(str(tmp_path / "welcome-failure-notebooks.sqlite"))
    monkeypatch.setattr("src.ui.main_window.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.summary_queue.manager.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.main_window.NotebookDBManager", lambda: notebooks)
    recorder = MagicMock()
    recorder.is_recording = False
    monkeypatch.setattr("src.ui.main_window.Recorder", lambda: recorder)
    monkeypatch.setattr("src.ui.main_window.runtime_startup.RuntimeStartupCoordinator.initialize_rag_from_settings", lambda self: setattr(self.window, "rag", None))
    window = MainWindow()
    qtbot.addWidget(window)
    try:
        def fail_start(*_args, **_kwargs):
            raise RuntimeError("database unavailable")
        window.productivity.service.start = fail_start
        window.welcome_widget.pomodoro_btn.click()
        assert window.productivity.service.state == "idle"
        assert "database unavailable" in window.central_tabs.currentWidget().status_label.text()
    finally:
        window._force_quit = True
        window.close()


def test_summary_timeline_reference_opens_existing_summary_owner(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "summary-source.sqlite"))
    db.save_daily_summary("2026-09-25", "Keep this saved summary", "Work")
    summary = db.get_daily_summary_details("2026-09-25", "Work")
    notebooks = NotebookDBManager(str(tmp_path / "summary-source-notebooks.sqlite"))
    monkeypatch.setattr("src.ui.main_window.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.summary_queue.manager.DBManager", lambda: db)
    monkeypatch.setattr("src.ui.main_window.NotebookDBManager", lambda: notebooks)
    recorder = MagicMock()
    recorder.is_recording = False
    monkeypatch.setattr("src.ui.main_window.Recorder", lambda: recorder)
    monkeypatch.setattr("src.ui.main_window.runtime_startup.RuntimeStartupCoordinator.initialize_rag_from_settings", lambda self: setattr(self.window, "rag", None))
    window = MainWindow()
    qtbot.addWidget(window)
    try:
        timeline = window.open_timeline_tab()
        item = next(timeline.list_widget.item(i) for i in range(timeline.list_widget.count())
                    if timeline.list_widget.item(i).data(Qt.ItemDataRole.UserRole)[0] == "daily_summary")
        timeline._open_item(item)
        owner = window.central_tabs.currentWidget()
        assert isinstance(owner, SummaryViewerWidget)
        assert owner.summary_data["id"] == summary["id"]
        assert owner.summary_data["summary"] == "Keep this saved summary"
    finally:
        window._force_quit = True
        window.close()
