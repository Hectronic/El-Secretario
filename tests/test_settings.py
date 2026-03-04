
import pytest
import shutil
import tempfile
from PyQt6.QtCore import QSettings
from src.ui.dialogs import SettingsWidget

@pytest.fixture
def clean_settings(monkeypatch):
    """Ensure clean settings before test."""
    temp_dir = tempfile.mkdtemp(prefix="secretario_settings_")
    settings_file = f"{temp_dir}/settings.ini"
    settings = QSettings(settings_file, QSettings.Format.IniFormat)
    monkeypatch.setattr("src.ui.dialogs.QSettings", lambda *args, **kwargs: settings)
    old_hf = settings.value("hf_token")
    old_gemini = settings.value("gemini_key")
    old_theme = settings.value("app_theme")
    old_startup_weekly = settings.value("startup_enqueue_last_weekly_summary")
    old_startup_daily = settings.value("startup_enqueue_previous_daily_summary")
    old_transcription_backend = settings.value("transcription_backend")
    old_auto_index_rag = settings.value("auto_index_rag")
    
    yield settings
    
    # Restore or clear
    if old_hf: settings.setValue("hf_token", old_hf)
    else: settings.remove("hf_token")
    
    if old_gemini: settings.setValue("gemini_key", old_gemini)
    else: settings.remove("gemini_key")
    
    if old_theme: settings.setValue("app_theme", old_theme)
    else: settings.remove("app_theme")

    if old_startup_weekly is not None:
        settings.setValue("startup_enqueue_last_weekly_summary", old_startup_weekly)
    else:
        settings.remove("startup_enqueue_last_weekly_summary")

    if old_startup_daily is not None:
        settings.setValue("startup_enqueue_previous_daily_summary", old_startup_daily)
    else:
        settings.remove("startup_enqueue_previous_daily_summary")

    if old_transcription_backend is not None:
        settings.setValue("transcription_backend", old_transcription_backend)
    else:
        settings.remove("transcription_backend")

    if old_auto_index_rag is not None:
        settings.setValue("auto_index_rag", old_auto_index_rag)
    else:
        settings.remove("auto_index_rag")

    settings.sync()
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_settings_load(qtbot, clean_settings):
    """Test that settings are loaded correctly into the widget."""
    clean_settings.setValue("hf_token", "test_hf_token_123")
    clean_settings.setValue("gemini_key", "test_gemini_key_456")
    clean_settings.setValue("startup_enqueue_last_weekly_summary", True)
    clean_settings.setValue("startup_enqueue_previous_daily_summary", True)
    
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    # Access through general_panel
    assert widget.general_panel.token_input.text() == "test_hf_token_123"
    assert widget.general_panel.gemini_key_input.text() == "test_gemini_key_456"
    assert widget.general_panel.startup_last_weekly_check.isChecked()
    assert widget.general_panel.startup_prev_daily_check.isChecked()

def test_settings_save(qtbot, clean_settings):
    """Test that saving works."""
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    widget.general_panel.token_input.setText("new_hf_token")
    widget.general_panel.gemini_key_input.setText("new_gemini_key")
    
    # Test setting theme
    widget.general_panel.theme_combo.setCurrentText("Light")
    widget.general_panel.startup_last_weekly_check.setChecked(True)
    widget.general_panel.startup_prev_daily_check.setChecked(True)
    
    widget.save_settings()
    
    assert clean_settings.value("hf_token") == "new_hf_token"
    assert clean_settings.value("gemini_key") == "new_gemini_key"
    assert clean_settings.value("app_theme") == "Light"
    assert clean_settings.value("startup_enqueue_last_weekly_summary", False, type=bool) is True
    assert clean_settings.value("startup_enqueue_previous_daily_summary", False, type=bool) is True
    assert "saved successfully" in widget.status_label.text()

def test_settings_show_copy_buttons(qtbot, clean_settings):
    """Test Show/Hide and Copy buttons."""
    clean_settings.setValue("hf_token", "secret_token")
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    # Access through general_panel
    layout = widget.general_panel.hf_container.layout()
    # layout items: 0: line_edit, 1: show_btn, 2: copy_btn
    
    line_edit = layout.itemAt(0).widget()
    show_btn = layout.itemAt(1).widget()
    copy_btn = layout.itemAt(2).widget()
    
    # Check initial state (Password)
    from PyQt6.QtWidgets import QLineEdit, QApplication
    from PyQt6.QtCore import Qt
    
    assert line_edit.echoMode() == QLineEdit.EchoMode.Password
    assert "secret_token" == line_edit.text()
    
    # Test Show
    qtbot.mouseClick(show_btn, Qt.MouseButton.LeftButton)
    assert line_edit.echoMode() == QLineEdit.EchoMode.Normal
    
    # Test Hide
    qtbot.mouseClick(show_btn, Qt.MouseButton.LeftButton)
    assert line_edit.echoMode() == QLineEdit.EchoMode.Password
    
    # Test Copy
    # We clear clipboard first
    clipboard = QApplication.clipboard()
    clipboard.clear()
    
    qtbot.mouseClick(copy_btn, Qt.MouseButton.LeftButton)
    assert clipboard.text() == "secret_token"


def test_prompts_panel_defaults(qtbot, clean_settings):
    """Test that prompts panel loads default prompts."""
    # Clear any saved prompts
    clean_settings.remove("prompt_summary")
    clean_settings.remove("prompt_clean")
    clean_settings.remove("prompt_weekly_summary")
    
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    # Check that default prompts are loaded
    assert "{text}" in widget.prompts_panel.prompt_editors["summary"].toPlainText()
    assert "{text}" in widget.prompts_panel.prompt_editors["clean"].toPlainText()
    assert "{text}" in widget.prompts_panel.prompt_editors["weekly_summary"].toPlainText()


def test_prompts_panel_save(qtbot, clean_settings):
    """Test saving custom prompts."""
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    # Set a custom prompt
    custom_prompt = "Custom summary prompt: {text}"
    widget.prompts_panel.prompt_editors["summary"].setPlainText(custom_prompt)
    
    widget.save_settings()
    
    assert clean_settings.value("prompt_summary") == custom_prompt
    
    # Clean up
    clean_settings.remove("prompt_summary")


def test_audio_panel_defaults_and_save(qtbot, clean_settings):
    clean_settings.remove("transcription_backend")
    clean_settings.remove("auto_index_rag")
    clean_settings.remove("audio_rescan_before_capture")
    clean_settings.remove("audio_prefer_device_index")

    widget = SettingsWidget()
    qtbot.addWidget(widget)

    assert widget.audio_panel.backend_combo.currentText() == "auto"
    assert widget.audio_panel.rag_auto_index_check.isChecked() is True
    assert widget.audio_panel.rescan_before_capture_check.isChecked() is True
    assert widget.audio_panel.prefer_index_check.isChecked() is False

    widget.audio_panel.backend_combo.setCurrentText("openai-whisper")
    widget.audio_panel.rag_auto_index_check.setChecked(False)
    widget.audio_panel.rescan_before_capture_check.setChecked(False)
    widget.audio_panel.prefer_index_check.setChecked(True)
    widget.save_settings()

    assert clean_settings.value("transcription_backend") == "openai-whisper"
    assert clean_settings.value("auto_index_rag", True, type=bool) is False
    assert clean_settings.value("audio_rescan_before_capture", True, type=bool) is False
    assert clean_settings.value("audio_prefer_device_index", False, type=bool) is True
