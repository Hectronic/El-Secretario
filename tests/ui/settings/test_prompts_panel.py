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

"""Tests for the prompts settings panel."""

from PyQt6.QtCore import QSettings

from src.ui.settings.prompts_defaults import DEFAULT_PROMPTS
from src.ui.settings.prompts_panel import PromptsSettingsPanel


def test_prompts_panel_loads_defaults(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "prompts_panel.ini"), QSettings.Format.IniFormat)

    panel = PromptsSettingsPanel(settings)
    qtbot.addWidget(panel)

    assert "{text}" in panel.prompt_editors["summary"].toPlainText()
    assert panel.prompt_editors["summary"].toPlainText() == DEFAULT_PROMPTS["summary"]
    assert panel.prompt_editors["clean"].toPlainText() == DEFAULT_PROMPTS["clean"]
    assert panel.prompt_editors["daily_summary"].toPlainText() == DEFAULT_PROMPTS["daily_summary"]
    assert panel.prompt_editors["weekly_summary"].toPlainText() == DEFAULT_PROMPTS["weekly_summary"]
    assert panel.prompt_editors["task_extraction"].toPlainText() == DEFAULT_PROMPTS["task_extraction"]


def test_prompts_panel_reset_and_save(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "prompts_panel_save.ini"), QSettings.Format.IniFormat)

    panel = PromptsSettingsPanel(settings)
    qtbot.addWidget(panel)

    panel.prompt_editors["summary"].setPlainText("Custom summary prompt")
    panel.prompt_editors["clean"].setPlainText("Custom clean prompt")
    panel._reset_to_defaults()
    assert panel.prompt_editors["summary"].toPlainText() == DEFAULT_PROMPTS["summary"]

    panel.prompt_editors["weekly_summary"].setPlainText("Weekly custom")
    panel.save()

    assert settings.value("prompt_summary") == DEFAULT_PROMPTS["summary"]
    assert settings.value("prompt_clean") == DEFAULT_PROMPTS["clean"]
    assert settings.value("prompt_weekly_summary") == "Weekly custom"
