
import pytest
from PyQt6.QtCore import QSettings
from src.ui.dialogs import SettingsWidget

@pytest.fixture
def clean_settings():
    """Ensure clean settings before test."""
    settings = QSettings("Hectronic", "Secretario")
    old_hf = settings.value("hf_token")
    old_gemini = settings.value("gemini_key")
    
    yield settings
    
    # Restore or clear
    if old_hf: settings.setValue("hf_token", old_hf)
    else: settings.remove("hf_token")
    
    if old_gemini: settings.setValue("gemini_key", old_gemini)
    else: settings.remove("gemini_key")

def test_settings_load(qtbot, clean_settings):
    """Test that settings are loaded correctly into the widget."""
    clean_settings.setValue("hf_token", "test_hf_token_123")
    clean_settings.setValue("gemini_key", "test_gemini_key_456")
    
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    assert widget.token_input.text() == "test_hf_token_123"
    assert widget.gemini_key_input.text() == "test_gemini_key_456"

def test_settings_save(qtbot, clean_settings):
    """Test that saving works."""
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    widget.token_input.setText("new_hf_token")
    widget.gemini_key_input.setText("new_gemini_key")
    
    # Test setting theme
    widget.theme_combo.setCurrentText("Light")
    
    widget.save_settings()
    
    assert clean_settings.value("hf_token") == "new_hf_token"
    assert clean_settings.value("gemini_key") == "new_gemini_key"
    assert clean_settings.value("app_theme") == "Light"
    assert "saved successfully" in widget.status_label.text()

def test_settings_show_copy_buttons(qtbot, clean_settings):
    """Test Show/Hide and Copy buttons."""
    clean_settings.setValue("hf_token", "secret_token")
    widget = SettingsWidget()
    qtbot.addWidget(widget)
    
    # helper to get buttons from container
    # container is first child of helper return, but we stored it in self.hf_container
    layout = widget.hf_container.layout()
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
