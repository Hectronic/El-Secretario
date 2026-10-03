from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox, QPushButton

from src.ui.settings.catalog import CATEGORIES
from src.ui.settings.store import clear_pending_restart_status
from src.ui.settings.widget import SettingsWidget


def _widget(monkeypatch, tmp_path, name="settings.ini"):
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    monkeypatch.setattr(
        "src.ui.settings.general_panel.QTimer.singleShot",
        lambda *_args, **_kwargs: None,
    )
    settings = QSettings(str(tmp_path / name), QSettings.Format.IniFormat)
    monkeypatch.setattr("src.ui.settings.widget.QSettings", lambda *_args: settings)
    return SettingsWidget(), settings


def _search(widget, text):
    widget.search_input.setText(text)
    assert widget.search_results.count() > 0
    for index in range(widget.search_results.count()):
        item = widget.search_results.item(index)
        if item.data(256):  # Qt.UserRole
            return item
    raise AssertionError(f"No search result for {text!r}")


def test_search_opens_category_focuses_control_and_restores_unsaved_state(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    widget.general_panel.theme_combo.setCurrentText("Dark")
    assert widget.has_unsaved_changes()

    microphone = _search(widget, "microphone")
    widget._open_search_result(microphone)
    assert widget._search_override == "Recording & devices"
    assert widget.category_list.currentItem().text() == "Recording & devices"
    assert widget.audio_panel.mic_combo.isVisible()
    assert widget.focusWidget() is widget.audio_panel.mic_combo
    assert settings.value("app_theme", "System") == "System"

    widget.search_input.clear()
    assert widget._category == "Appearance & language"
    assert widget.general_panel.theme_combo.currentText() == "Dark"
    assert widget.has_unsaved_changes()


def test_basic_advanced_disclosure_and_search_can_reveal_advanced_control(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    qtbot.addWidget(widget)
    widget.show()
    widget.category_list.setCurrentRow(CATEGORIES.index("Transcription & speakers"))
    force_cpu = next(field for field in widget.catalog if field.key == "force_cpu")
    assert force_cpu.wrapper.isHidden()
    assert widget.advanced_toggle.isChecked() is False

    result = _search(widget, "CUDA")
    widget._open_search_result(result)
    assert widget.advanced_toggle.isChecked() is True
    assert force_cpu.wrapper.isVisible()
    assert settings.value("settings/advanced_mode", False, type=bool) is True

    widget.advanced_toggle.setChecked(False)
    assert force_cpu.wrapper.isHidden()


def test_invalid_setting_does_not_block_valid_setting_or_overwrite_saved_value(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    settings.setValue("ollama_host", "http://localhost:11434")
    settings.setValue("app_theme", "System")
    qtbot.addWidget(widget)

    widget.general_panel.ollama_host_input.setText("not-a-url")
    widget.general_panel.theme_combo.setCurrentText("Light")
    assert widget.save_settings() is False

    assert settings.value("app_theme") == "Light"
    assert settings.value("ollama_host") == "http://localhost:11434"
    assert "Interface theme" in widget.status_label.text()
    assert "Ollama server" in widget.status_label.text()
    assert widget.has_unsaved_changes()


def test_invalid_ollama_model_does_not_save_provider_but_saves_theme(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    settings.setValue("ai_provider", "gemini")
    settings.setValue("ollama_model", "llama3")
    settings.setValue("app_theme", "System")
    widget.discard_settings()
    qtbot.addWidget(widget)

    widget.general_panel.provider_combo.setCurrentIndex(1)
    ollama = next(field for field in widget.catalog if field.key == "ollama_model")
    ollama.reset()
    widget.general_panel.theme_combo.setCurrentText("Light")
    assert widget.save_settings() is False

    assert settings.value("app_theme") == "Light"
    assert settings.value("ai_provider") == "gemini"
    assert settings.value("ollama_model") == "llama3"
    assert "Ollama model" in widget.status_label.text()


def test_discard_and_scoped_category_reset_preserve_other_categories(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    settings.setValue("app_theme", "Dark")
    settings.setValue("gemini_key", "keep-this-secret")
    settings.setValue("capture_system_audio", True)
    widget.discard_settings()
    qtbot.addWidget(widget)
    widget.show()

    assert not widget.has_unsaved_changes(), widget._changes()
    widget.category_list.setCurrentRow(CATEGORIES.index("Recording & devices"))
    monkeypatch.setattr(
        "src.ui.settings.widget.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )
    widget._reset_category()
    assert widget.audio_panel.sys_audio_check.isChecked() is False
    assert settings.value("capture_system_audio", False, type=bool) is True
    assert widget.save_settings() is True
    assert settings.value("capture_system_audio", True, type=bool) is False
    assert settings.value("app_theme") == "Dark"
    assert settings.value("gemini_key") == "keep-this-secret"

    widget.audio_panel.sys_audio_check.setChecked(True)
    widget.general_panel.theme_combo.setCurrentText("Light")
    widget.discard_settings()
    assert widget.audio_panel.sys_audio_check.isChecked() is False
    assert widget.general_panel.theme_combo.currentText() == "Dark"
    assert settings.value("capture_system_audio", True, type=bool) is False
    assert settings.value("app_theme") == "Dark"


def test_per_setting_reset_is_staged_and_dirty_navigation_can_stay(qtbot, monkeypatch, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("ollama_host", "https://custom.example:11434")
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    monkeypatch.setattr("src.ui.settings.general_panel.QTimer.singleShot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("src.ui.settings.widget.QSettings", lambda *_args: settings)
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    widget.show()

    result = _search(widget, "Ollama server")
    widget._open_search_result(result)
    field = next(item for item in widget.catalog if item.key == "ollama_host")
    reset = field.wrapper.findChild(QPushButton, "resetSetting_ollama_host")
    assert reset is not None
    reset.click()
    assert widget.general_panel.ollama_host_input.text() == "http://localhost:11434"
    assert settings.value("ollama_host") == "https://custom.example:11434"
    assert widget.has_unsaved_changes()

    widget.search_input.clear()
    widget._leave_decision = "stay"
    widget.category_list.setCurrentRow(CATEGORIES.index("Recording & devices"))
    assert widget._category == "Appearance & language"
    assert widget.general_panel.ollama_host_input.text() == "http://localhost:11434"


def test_restart_required_status_persists_until_a_new_process_opens_settings(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    qtbot.addWidget(widget)
    widget.general_panel.enable_update_check.setChecked(False)
    widget.save_settings()
    assert settings.value("enable_auto_update", True, type=bool) is False
    assert "saved False" in widget.restart_status_label.text()
    assert "active until restart True" in widget.restart_status_label.text()

    reopened = SettingsWidget()
    qtbot.addWidget(reopened)
    assert "Check for updates on startup" in reopened.restart_status_label.text()

    import os

    settings.setValue("settings/pending_restart_pid", os.getpid() + 1)
    after_restart = SettingsWidget()
    qtbot.addWidget(after_restart)
    assert after_restart.restart_status_label.text() == ""
    assert settings.value("settings/pending_restart_keys") is None


def test_startup_clears_pending_restart_status_after_settings_become_active(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    widget.general_panel.enable_update_check.setChecked(False)
    widget.save_settings()
    assert widget.restart_status_label.text()

    clear_pending_restart_status(settings)
    reopened = SettingsWidget()
    qtbot.addWidget(reopened)
    assert reopened.restart_status_label.text() == ""
    assert settings.value("enable_auto_update", True, type=bool) is False


def test_catalog_maps_every_existing_settings_key_once(qtbot, monkeypatch, tmp_path):
    widget, _settings = _widget(monkeypatch, tmp_path)
    qtbot.addWidget(widget)
    expected = {
        "app_theme", "system_language", "default_mic_name", "default_mic_index",
        "capture_system_audio", "recording_guardian/duration_reminder_seconds",
        "recording_guardian/duration_reminders_enabled", "recording_guardian/silence_warning_seconds",
        "recording_guardian/silence_warnings_enabled", "recording_guardian/tray_notifications_enabled",
        "recording_guardian/auto_stop_after_silence", "audio_rescan_before_capture",
        "audio_prefer_device_index", "whisper_model", "sherpa_onnx_model_dir",
        "sherpa_onnx_model_type", "sherpa_onnx_auto_download", "sherpa_onnx_model_url",
        "hf_token", "force_cpu", "compute_type", "transcription_backend", "ai_provider",
        "gemini_key", "gemini_model", "ollama_host", "ollama_model", "prompt_summary",
        "prompt_clean", "prompt_daily_summary", "prompt_weekly_summary", "prompt_task_extraction",
        "auto_index_rag", "rag_enabled", "rag_persist_directory", "rag_safe_delete_mode",
        "rag_subprocess_upsert_mode", "rag_subprocess_query_mode",
        "startup_enqueue_last_weekly_summary", "startup_enqueue_previous_daily_summary",
        "enable_auto_update", "pomodoro/focus_minutes", "pomodoro/short_break_minutes",
        "pomodoro/long_break_minutes", "pomodoro/tray_notifications", "enable_local_api",
        "enable_mcp_server",
    }
    keys = [key for field in widget.catalog for key in field.keys]
    assert len(keys) == len(set(keys))
    assert set(keys) == expected


def test_contextual_deep_link_opens_advanced_control_and_secret_never_enters_search(qtbot, monkeypatch, tmp_path):
    widget, settings = _widget(monkeypatch, tmp_path)
    settings.setValue("hf_token", "TOP-SECRET-VALUE")
    widget.discard_settings()
    qtbot.addWidget(widget)
    widget.show()

    assert widget.open_setting("force_cpu") is True
    force_cpu = next(field for field in widget.catalog if field.key == "force_cpu")
    assert widget._category == "Transcription & speakers"
    assert widget.advanced_toggle.isChecked()
    assert force_cpu.wrapper.isVisible()

    widget.search_input.setText("TOP-SECRET-VALUE")
    assert widget.search_results.count() == 1
    assert widget.search_results.item(0).data(256) is None
    assert "TOP-SECRET-VALUE" not in widget.status_label.text()


def test_narrow_settings_view_keeps_controls_in_vertical_scroll_area(qtbot, monkeypatch, tmp_path):
    widget, _settings = _widget(monkeypatch, tmp_path)
    qtbot.addWidget(widget)
    widget.resize(620, 480)
    widget.show()
    widget.category_list.setCurrentRow(CATEGORIES.index("Transcription & speakers"))
    qtbot.wait(20)

    assert widget.surface_scroll.horizontalScrollBarPolicy().name == "ScrollBarAlwaysOff"
    assert widget.surface_scroll.viewport().width() > 0
