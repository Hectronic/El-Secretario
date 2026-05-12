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

"""Tests for the audio settings panel."""

from PyQt6.QtCore import QSettings

from src.ui.settings.audio_panel import AudioSettingsPanel


def test_audio_panel_defaults_and_save(qtbot, monkeypatch, tmp_path):
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    settings = QSettings(str(tmp_path / "audio_panel.ini"), QSettings.Format.IniFormat)

    panel = AudioSettingsPanel(settings)
    qtbot.addWidget(panel)

    assert panel.mic_combo.count() == 1
    assert panel.mic_combo.currentText() == "System Default"
    assert panel.sys_audio_check.isChecked() is False
    assert panel.whisper_combo.currentText()
    assert panel.sherpa_model_dir_input.text() == "models/sherpa-onnx"
    assert panel.sherpa_model_type_combo.currentText() == "auto"
    assert panel.sherpa_auto_download_check.isChecked() is True
    assert "github.com/k2-fsa/sherpa-onnx/releases" in panel.sherpa_model_url_input.text()
    assert panel.force_cpu_check.isChecked() is False
    assert panel.compute_combo.currentText() == "auto"
    assert panel.backend_combo.currentText() == "auto"
    assert panel.rag_auto_index_check.isChecked() is True
    assert panel.rescan_before_capture_check.isChecked() is True
    assert panel.prefer_index_check.isChecked() is False

    panel.sys_audio_check.setChecked(True)
    panel.whisper_combo.setCurrentIndex(0)
    panel.sherpa_model_dir_input.setText("/tmp/sherpa-model")
    panel.sherpa_model_type_combo.setCurrentText("paraformer")
    panel.sherpa_auto_download_check.setChecked(False)
    panel.sherpa_model_url_input.setText("https://example.com/custom-sherpa.tar.bz2")
    panel.force_cpu_check.setChecked(True)
    panel.compute_combo.setCurrentText("int8")
    panel.backend_combo.setCurrentText("openai-whisper")
    panel.rag_auto_index_check.setChecked(False)
    panel.rescan_before_capture_check.setChecked(False)
    panel.prefer_index_check.setChecked(True)

    panel.save()

    assert settings.value("capture_system_audio", False, type=bool) is True
    assert settings.value("whisper_model") == panel.whisper_combo.currentText()
    assert settings.value("sherpa_onnx_model_dir") == "/tmp/sherpa-model"
    assert settings.value("sherpa_onnx_model_type") == "paraformer"
    assert settings.value("sherpa_onnx_auto_download", True, type=bool) is False
    assert settings.value("sherpa_onnx_model_url") == "https://example.com/custom-sherpa.tar.bz2"
    assert settings.value("force_cpu", False, type=bool) is True
    assert settings.value("compute_type") == "int8"
    assert settings.value("transcription_backend") == "openai-whisper"
    assert settings.value("auto_index_rag", True, type=bool) is False
    assert settings.value("audio_rescan_before_capture", True, type=bool) is False
    assert settings.value("audio_prefer_device_index", False, type=bool) is True


def test_audio_panel_rescan_updates_status(qtbot, monkeypatch, tmp_path):
    monkeypatch.setenv("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
    settings = QSettings(str(tmp_path / "audio_panel_rescan.ini"), QSettings.Format.IniFormat)

    panel = AudioSettingsPanel(settings)
    qtbot.addWidget(panel)

    panel._on_rescan_mics_clicked()

    assert panel.mic_status_label.text() == "No input devices found (using System Default)."
