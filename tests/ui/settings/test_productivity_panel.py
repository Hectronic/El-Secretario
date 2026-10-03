from PyQt6.QtCore import QSettings

from src.ui.settings.productivity_panel import ProductivitySettingsPanel


def test_productivity_settings_panel_loads_and_stages_all_pomodoro_preferences(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "productivity.ini"), QSettings.Format.IniFormat)
    settings.setValue("pomodoro/focus_minutes", 40)
    settings.setValue("pomodoro/short_break_minutes", 8)
    settings.setValue("pomodoro/long_break_minutes", 18)
    settings.setValue("pomodoro/tray_notifications", False)
    panel = ProductivitySettingsPanel(settings)
    qtbot.addWidget(panel)

    assert panel.focus_minutes.value() == 40
    assert panel.short_break_minutes.value() == 8
    assert panel.long_break_minutes.value() == 18
    assert panel.tray_notifications.isChecked() is False

    panel.focus_minutes.setValue(30)
    panel.save()
    assert settings.value("pomodoro/focus_minutes", type=int) == 30
