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

"""Tests for the RAG settings panel."""

from PyQt6.QtCore import QSettings

from src.ui.settings.rag_panel import RAGSettingsPanel


def test_rag_panel_defaults_and_save(qtbot, tmp_path):
    settings = QSettings(str(tmp_path / "rag_panel.ini"), QSettings.Format.IniFormat)

    panel = RAGSettingsPanel(settings)
    qtbot.addWidget(panel)

    assert panel.rag_enabled_check.isChecked() is True
    assert panel.persist_dir_input.text() == "chroma_db"
    assert panel.safe_delete_check.isChecked() is True
    assert panel.subprocess_upsert_check.isChecked() is True
    assert panel.subprocess_query_check.isChecked() is True

    panel.rag_enabled_check.setChecked(False)
    panel.persist_dir_input.setText("custom_db")
    panel.safe_delete_check.setChecked(False)
    panel.subprocess_upsert_check.setChecked(False)
    panel.subprocess_query_check.setChecked(False)

    cfg = panel.get_rag_config()
    assert cfg == {
        "enabled": False,
        "persist_directory": "custom_db",
        "safe_delete_mode": False,
        "subprocess_upsert_mode": False,
        "subprocess_query_mode": False,
    }

    panel.save()

    assert settings.value("rag_enabled", True, type=bool) is False
    assert settings.value("rag_persist_directory") == "custom_db"
    assert settings.value("rag_safe_delete_mode", True, type=bool) is False
    assert settings.value("rag_subprocess_upsert_mode", True, type=bool) is False
    assert settings.value("rag_subprocess_query_mode", True, type=bool) is False
