# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Callable, Optional

from PyQt6.QtWidgets import QCheckBox, QComboBox

from src.transcription_options import (
    DEFAULT_WELCOME_TRANSCRIPTION_MODEL,
    get_saved_transcription_model,
)


def populate_microphones(
    mic_combo: QComboBox,
    *,
    recorder_getter: Callable[[], object],
    skip_audio_enum: bool,
    keep_current: bool = False,
) -> None:
    previous_data = mic_combo.currentData() if keep_current else None
    previous_text = mic_combo.currentText() if keep_current else ""
    if skip_audio_enum:
        mic_combo.clear()
        mic_combo.addItem("Default (Auto)", None)
        return

    recorder = recorder_getter()
    devices = recorder.get_input_devices()
    mic_combo.clear()
    mic_combo.addItem("Default (Auto)", None)
    for idx, name in devices:
        mic_combo.addItem(name, idx)

    if keep_current:
        if previous_data is not None:
            idx_by_data = mic_combo.findData(previous_data)
            if idx_by_data >= 0:
                mic_combo.setCurrentIndex(idx_by_data)
                return
        if previous_text:
            idx_by_text = mic_combo.findText(previous_text)
            if idx_by_text >= 0:
                mic_combo.setCurrentIndex(idx_by_text)


def load_capture_settings(
    settings,
    *,
    mic_combo: QComboBox,
    model_combo: QComboBox,
    lang_combo: QComboBox,
    diarization_check: QCheckBox,
    sys_audio_check: QCheckBox,
    auto_summary_check: QCheckBox,
) -> None:
    saved_mic = settings.value("rec_config/mic", None)
    prefer_index = settings.value("audio_prefer_device_index", False, type=bool)
    if saved_mic is None:
        if prefer_index:
            saved_mic_index = settings.value("default_mic_index", None)
            try:
                index = mic_combo.findData(int(saved_mic_index)) if saved_mic_index is not None else -1
            except (TypeError, ValueError):
                index = -1
            if index >= 0:
                mic_combo.setCurrentIndex(index)
        if mic_combo.currentIndex() <= 0:
            saved_mic_name = settings.value("default_mic_name", "")
            if saved_mic_name:
                index = mic_combo.findText(saved_mic_name)
                if index >= 0:
                    mic_combo.setCurrentIndex(index)
    elif saved_mic:
        index = mic_combo.findData(saved_mic)
        if index >= 0:
            mic_combo.setCurrentIndex(index)

    saved_model = get_saved_transcription_model(
        settings,
        default=DEFAULT_WELCOME_TRANSCRIPTION_MODEL,
    )
    model_combo.setCurrentText(saved_model)

    lang_combo.setCurrentText(settings.value("rec_config/language", "Auto"))
    diarization_check.setChecked(settings.value("rec_config/diarization", False, type=bool))

    saved_sys_audio = settings.value("rec_config/capture_system_audio", None)
    if saved_sys_audio is None:
        saved_sys_audio = settings.value("capture_system_audio", False, type=bool)
    else:
        saved_sys_audio = settings.value("rec_config/capture_system_audio", False, type=bool)
    sys_audio_check.setChecked(saved_sys_audio)

    auto_summary_check.setChecked(
        settings.value("rec_config/auto_summarize_after_transcription", False, type=bool)
    )


def save_capture_settings(
    settings,
    *,
    mic_combo: QComboBox,
    model_combo: QComboBox,
    lang_combo: QComboBox,
    diarization_check: QCheckBox,
    sys_audio_check: QCheckBox,
    auto_summary_check: QCheckBox,
) -> None:
    settings.setValue("rec_config/mic", mic_combo.currentData())
    settings.setValue("rec_config/model", model_combo.currentText())
    settings.setValue("rec_config/language", lang_combo.currentText())
    settings.setValue("rec_config/diarization", diarization_check.isChecked())
    settings.setValue("rec_config/capture_system_audio", sys_audio_check.isChecked())
    settings.setValue("rec_config/auto_summarize_after_transcription", auto_summary_check.isChecked())


def build_recording_config(
    *,
    mic_combo: QComboBox,
    model_combo: QComboBox,
    lang_combo: QComboBox,
    diarization_check: QCheckBox,
    sys_audio_check: QCheckBox,
    auto_summary_check: QCheckBox,
) -> dict:
    lang_map = {"Auto": None, "Spanish": "es", "English": "en"}
    return {
        "device_index": mic_combo.currentData(),
        "model": model_combo.currentText(),
        "language": lang_map.get(lang_combo.currentText()),
        "diarization": diarization_check.isChecked(),
        "capture_system_audio": sys_audio_check.isChecked(),
        "auto_summarize_after_transcription": auto_summary_check.isChecked(),
    }
