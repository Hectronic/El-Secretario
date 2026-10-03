"""Characterize existing settings keys before reshaping the Settings window."""

from PyQt6.QtCore import QSettings

from src.transcription_options import DEFAULT_TRANSCRIPTION_MODEL
from src.ui.settings.prompts_defaults import DEFAULT_PROMPTS
from src.ui.settings.widget import SettingsWidget


def test_legacy_settings_round_trip_preserves_values_and_unrelated_keys(
    qtbot, monkeypatch, tmp_path
):
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    monkeypatch.setattr(
        "src.ui.settings.general_panel.QTimer.singleShot",
        lambda *_args, **_kwargs: None,
    )
    settings = QSettings(str(tmp_path / "legacy-settings.ini"), QSettings.Format.IniFormat)
    legacy_values = {
        "hf_token": "hf-secret-value",
        "ai_provider": "gemini",
        "gemini_key": "gemini-secret-value",
        "gemini_model": "gemini-3-preview",
        "ollama_host": "http://localhost:11434",
        "ollama_model": "llama3",
        "app_theme": "System",
        "system_language": "English",
        "startup_enqueue_last_weekly_summary": True,
        "startup_enqueue_previous_daily_summary": False,
        "enable_local_api": False,
        "enable_mcp_server": True,
        "enable_auto_update": True,
        "pomodoro/focus_minutes": 40,
        "pomodoro/short_break_minutes": 7,
        "pomodoro/long_break_minutes": 20,
        "pomodoro/tray_notifications": False,
        "default_mic_name": "",
        "default_mic_index": None,
        "capture_system_audio": True,
        "recording_guardian/duration_reminder_seconds": 1800,
        "recording_guardian/duration_reminders_enabled": False,
        "recording_guardian/silence_warning_seconds": 1200,
        "recording_guardian/silence_warnings_enabled": True,
        "recording_guardian/tray_notifications_enabled": False,
        "recording_guardian/auto_stop_after_silence": True,
        "whisper_model": DEFAULT_TRANSCRIPTION_MODEL,
        "sherpa_onnx_model_dir": "models/sherpa-onnx",
        "sherpa_onnx_model_type": "auto",
        "sherpa_onnx_auto_download": False,
        "sherpa_onnx_model_url": "https://example.com/model.tar.bz2",
        "force_cpu": False,
        "compute_type": "float16",
        "transcription_backend": "faster-whisper",
        "auto_index_rag": False,
        "audio_rescan_before_capture": False,
        "audio_prefer_device_index": True,
        "rag_enabled": False,
        "rag_persist_directory": "legacy-vectors",
        "rag_safe_delete_mode": False,
        "rag_subprocess_upsert_mode": False,
        "rag_subprocess_query_mode": True,
        "prompt_summary": "Legacy summary {text}",
        "prompt_clean": DEFAULT_PROMPTS["clean"],
        "prompt_daily_summary": DEFAULT_PROMPTS["daily_summary"],
        "prompt_weekly_summary": DEFAULT_PROMPTS["weekly_summary"],
        "prompt_task_extraction": DEFAULT_PROMPTS["task_extraction"],
        "feature/owned/by/another/module": "preserve-me",
    }
    for key, value in legacy_values.items():
        settings.setValue(key, value)
    settings.sync()
    monkeypatch.setattr("src.ui.settings.widget.QSettings", lambda *_args: settings)

    widget = SettingsWidget()
    qtbot.addWidget(widget)

    assert widget.general_panel.token_input.text() == "hf-secret-value"
    assert widget.general_panel.gemini_key_input.text() == "gemini-secret-value"
    assert widget.general_panel.gemini_model_combo.currentText() == "gemini-3-preview"
    assert widget.general_panel.lang_input.text() == "English"
    assert widget.audio_panel.compute_combo.currentText() == "float16"
    assert widget.audio_panel.backend_combo.currentText() == "faster-whisper"
    assert widget.audio_panel.force_cpu_check.isChecked() is False
    assert widget.rag_panel.persist_dir_input.text() == "legacy-vectors"
    assert widget.prompts_panel.prompt_editors["summary"].toPlainText() == "Legacy summary {text}"

    widget.save_settings()

    for key, expected in legacy_values.items():
        assert settings.value(key) == expected, key
