from PyQt6.QtCore import QSettings
from PyQt6.QtTest import QSignalSpy
from unittest.mock import MagicMock

from src.app.pomodoro.service import PomodoroService
from src.database import DBManager
from src.ui.recording.transcription_flow import build_direct_transcription_config
from src.ui.pomodoro.widget import PomodoroWidget
from src.ui.settings.widget import SettingsWidget


class _SoundFile:
    samplerate = 10

    def __init__(self, _path):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __len__(self):
        return 100


def test_saved_stt_preferences_reach_next_job_and_rag_signal_uses_persisted_config(
    qtbot, monkeypatch, tmp_path
):
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    monkeypatch.setattr(
        "src.ui.settings.general_panel.QTimer.singleShot",
        lambda *_args, **_kwargs: None,
    )
    settings = QSettings(str(tmp_path / "settings-integration.ini"), QSettings.Format.IniFormat)
    settings.setValue("transcription_backend", "auto")
    settings.setValue("compute_type", "auto")
    settings.setValue("force_cpu", False)
    settings.setValue("app_theme", "System")
    settings.setValue("rag_persist_directory", "old-vectors")
    settings.setValue("pomodoro/focus_minutes", 25)
    monkeypatch.setattr("src.ui.settings.widget.QSettings", lambda *_args: settings)

    widget = SettingsWidget()
    qtbot.addWidget(widget)
    widget.audio_panel.backend_combo.setCurrentText("openai-whisper")
    widget.audio_panel.compute_combo.setCurrentText("float16")
    widget.audio_panel.force_cpu_check.setChecked(True)
    widget.productivity_panel.focus_minutes.setValue(40)
    assert widget.save_settings() is True

    runtime = build_direct_transcription_config(
        settings=settings,
        audio_path="meeting.wav",
        model_size="base",
        language_label="English",
        enable_diarization=True,
        sound_file_cls=_SoundFile,
    )
    assert runtime.backend_preference == "openai-whisper"
    assert runtime.compute_type == "float16"
    assert runtime.force_cpu is True
    assert runtime.language_code == "en"
    assert runtime.total_duration == 10

    productivity_db = DBManager(str(tmp_path / "settings-productivity.sqlite"))
    pomodoro_service = PomodoroService(productivity_db)
    pomodoro = PomodoroWidget(
        pomodoro_service,
        productivity_db,
        settings=settings,
        recorder=MagicMock(),
    )
    qtbot.addWidget(pomodoro)
    pomodoro.title_input.setText("Settings configured focus")
    pomodoro.start_button.click()
    assert pomodoro_service.state == "running"
    assert productivity_db.fetch_active_pomodoro()["planned_seconds"] == 40 * 60
    assert pomodoro.focus_minutes.isEnabled() is False
    pomodoro.cleanup()

    # Explicit RAG maintenance uses persisted RAG values only and emits the
    # existing real Qt signal; unrelated staged appearance edits stay staged.
    widget.rag_panel.persist_dir_input.setText("new-vectors")
    widget.general_panel.theme_combo.setCurrentText("Dark")
    initialize_spy = QSignalSpy(widget.rag_initialize_requested)
    widget._initialize_rag()
    assert len(initialize_spy) == 1
    assert initialize_spy[0][0] == {
        "enabled": True,
        "persist_directory": "new-vectors",
        "safe_delete_mode": True,
        "subprocess_upsert_mode": True,
        "subprocess_query_mode": True,
    }
    assert settings.value("rag_persist_directory") == "new-vectors"
    assert settings.value("app_theme") == "System"
    assert widget.has_unsaved_changes()
