from unittest.mock import MagicMock

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.main_window import MainWindow
from src.ui.pomodoro.widget import PomodoroWidget
from src.ui.timeline.widget import TimelineWidget


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
