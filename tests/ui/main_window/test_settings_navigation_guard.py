from types import SimpleNamespace

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QTabWidget, QWidget

from src.ui.main_window.shell_actions import MainWindowShellCoordinator
from src.ui.settings.widget import SettingsWidget


def test_leaving_settings_tab_requires_save_discard_or_stay(qtbot, monkeypatch, tmp_path):
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    monkeypatch.setattr(
        "src.ui.settings.general_panel.QTimer.singleShot",
        lambda *_args, **_kwargs: None,
    )
    settings = QSettings(str(tmp_path / "leave-settings.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("src.ui.settings.widget.QSettings", lambda *_args: settings)
    settings_tab = SettingsWidget()
    other_tab = QWidget()
    tabs = QTabWidget()
    tabs.addTab(settings_tab, "Settings")
    tabs.addTab(other_tab, "Welcome")
    qtbot.addWidget(tabs)

    window = SimpleNamespace(
        central_tabs=tabs,
        refresh_tasks_sidebar=lambda: None,
        _sync_chat_context_section=lambda: None,
    )
    coordinator = MainWindowShellCoordinator(window)
    tabs.currentChanged.connect(coordinator.on_central_tab_changed)

    settings_tab.general_panel.theme_combo.setCurrentText("Dark")
    settings_tab._leave_decision = "stay"
    tabs.setCurrentIndex(1)
    assert tabs.currentIndex() == 0
    assert settings_tab.general_panel.theme_combo.currentText() == "Dark"
    assert settings.value("app_theme", "System") == "System"

    settings_tab._leave_decision = "discard"
    tabs.setCurrentIndex(1)
    assert tabs.currentIndex() == 1
    assert settings.value("app_theme", "System") == "System"

    tabs.setCurrentIndex(0)
    settings_tab.general_panel.theme_combo.setCurrentText("Light")
    settings_tab._leave_decision = "save"
    tabs.setCurrentIndex(1)
    assert tabs.currentIndex() == 1
    assert settings.value("app_theme") == "Light"
