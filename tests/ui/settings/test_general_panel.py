# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from PyQt6.QtCore import QSettings

from src.ui.secret_field_widget import SecretFieldWidget
from src.ui.settings.general_panel import GeneralSettingsPanel


def _panel(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    panel = GeneralSettingsPanel(settings)
    return panel, settings


def test_general_panel_loads_and_exposes_secret_fields(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("hf_token", "secret-hf")
    settings.setValue("gemini_key", "secret-gemini")
    settings.setValue("ai_provider", "ollama")
    settings.setValue("ollama_model", "llama3")
    settings.sync()

    panel = GeneralSettingsPanel(settings)
    qtbot.addWidget(panel)

    assert isinstance(panel.hf_container, SecretFieldWidget)
    assert isinstance(panel.gemini_container, SecretFieldWidget)
    assert panel.token_input.text() == "secret-hf"
    assert panel.gemini_key_input.text() == "secret-gemini"
    assert panel.provider_combo.currentText() == "Ollama (Local)"
    assert panel.ollama_widget.isHidden() is False


def test_general_panel_save_persists_settings(qtbot, tmp_path):
    panel, settings = _panel(tmp_path)
    qtbot.addWidget(panel)

    panel.token_input.setText("new-hf")
    panel.gemini_key_input.setText("new-gemini")
    panel.gemini_model_combo.setCurrentText("gemini-3-preview")
    panel.provider_combo.setCurrentIndex(1)
    panel.ollama_host_input.setText("http://localhost:11500")
    panel.ollama_model_combo.addItem("mistral")
    panel.ollama_model_combo.setCurrentText("mistral")
    panel.theme_combo.setCurrentText("Dark")
    panel.lang_input.setText("English")
    panel.startup_last_weekly_check.setChecked(True)
    panel.startup_prev_daily_check.setChecked(True)

    panel.save()

    assert settings.value("hf_token") == "new-hf"
    assert settings.value("gemini_key") == "new-gemini"
    assert settings.value("gemini_model") == "gemini-3-preview"
    assert settings.value("ai_provider") == "ollama"
    assert settings.value("ollama_host") == "http://localhost:11500"
    assert settings.value("ollama_model") == "mistral"
    assert settings.value("app_theme") == "Dark"
    assert settings.value("system_language") == "English"
    assert settings.value("startup_enqueue_last_weekly_summary", False, type=bool) is True
    assert settings.value("startup_enqueue_previous_daily_summary", False, type=bool) is True


def test_general_panel_toggles_provider_sections(qtbot, tmp_path, monkeypatch):
    panel, _settings = _panel(tmp_path)
    qtbot.addWidget(panel)
    monkeypatch.setattr("src.ui.settings.general_panel.QTimer.singleShot", lambda *_args, **_kwargs: None)

    panel.provider_combo.setCurrentIndex(1)
    panel._on_provider_changed()

    assert panel.gemini_widget.isHidden() is True
    assert panel.ollama_widget.isHidden() is False
