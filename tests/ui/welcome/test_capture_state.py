# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox

from src.ui.welcome.capture_state import (
    build_recording_config,
    load_capture_settings,
    populate_microphones,
    save_capture_settings,
)


_APP = None


def _ensure_app():
    global _APP
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _APP = app
    return app


class _Recorder:
    @staticmethod
    def get_input_devices():
        return [(1, "Mic A"), (2, "Mic B")]


def _combo_with_items():
    combo = QComboBox()
    combo.addItem("Default (Auto)", None)
    combo.addItem("Mic A", 1)
    combo.addItem("Mic B", 2)
    return combo


def test_populate_microphones_skips_enumeration_when_requested():
    _ensure_app()
    combo = QComboBox()

    populate_microphones(combo, recorder_getter=lambda: _Recorder(), skip_audio_enum=True)

    assert combo.count() == 1
    assert combo.itemText(0) == "Default (Auto)"


def test_populate_microphones_restores_previous_selection():
    _ensure_app()
    combo = _combo_with_items()
    combo.setCurrentIndex(2)

    populate_microphones(combo, recorder_getter=lambda: _Recorder(), skip_audio_enum=False, keep_current=True)

    assert combo.currentData() == 2


def test_load_and_save_capture_settings_round_trip(tmp_path):
    _ensure_app()
    settings = QSettings(str(tmp_path / "welcome.ini"), QSettings.Format.IniFormat)

    mic_combo = _combo_with_items()
    model_combo = QComboBox()
    model_combo.addItems(["Whisper Base", "Whisper Small"])
    lang_combo = QComboBox()
    lang_combo.addItems(["Auto", "Spanish", "English"])
    diarization_check = QCheckBox()
    sys_audio_check = QCheckBox()
    auto_summary_check = QCheckBox()

    mic_combo.setCurrentIndex(2)
    model_combo.setCurrentText("Whisper Small")
    lang_combo.setCurrentText("Spanish")
    diarization_check.setChecked(True)
    sys_audio_check.setChecked(True)
    auto_summary_check.setChecked(True)

    save_capture_settings(
        settings,
        mic_combo=mic_combo,
        model_combo=model_combo,
        lang_combo=lang_combo,
        diarization_check=diarization_check,
        sys_audio_check=sys_audio_check,
        auto_summary_check=auto_summary_check,
    )

    mic_combo.setCurrentIndex(0)
    model_combo.setCurrentText("Whisper Base")
    lang_combo.setCurrentText("Auto")
    diarization_check.setChecked(False)
    sys_audio_check.setChecked(False)
    auto_summary_check.setChecked(False)

    load_capture_settings(
        settings,
        mic_combo=mic_combo,
        model_combo=model_combo,
        lang_combo=lang_combo,
        diarization_check=diarization_check,
        sys_audio_check=sys_audio_check,
        auto_summary_check=auto_summary_check,
    )

    assert mic_combo.currentData() == 2
    assert model_combo.currentText() == "Whisper Small"
    assert lang_combo.currentText() == "Spanish"
    assert diarization_check.isChecked() is True
    assert sys_audio_check.isChecked() is True
    assert auto_summary_check.isChecked() is True


def test_build_recording_config_maps_language_codes():
    _ensure_app()
    mic_combo = _combo_with_items()
    model_combo = QComboBox()
    model_combo.addItems(["Whisper Base", "Whisper Small"])
    lang_combo = QComboBox()
    lang_combo.addItems(["Auto", "Spanish", "English"])
    diarization_check = QCheckBox()
    sys_audio_check = QCheckBox()
    auto_summary_check = QCheckBox()

    mic_combo.setCurrentIndex(1)
    model_combo.setCurrentText("Whisper Small")
    lang_combo.setCurrentText("English")
    diarization_check.setChecked(True)

    config = build_recording_config(
        mic_combo=mic_combo,
        model_combo=model_combo,
        lang_combo=lang_combo,
        diarization_check=diarization_check,
        sys_audio_check=sys_audio_check,
        auto_summary_check=auto_summary_check,
    )

    assert config == {
        "device_index": 1,
        "model": "Whisper Small",
        "language": "en",
        "diarization": True,
        "capture_system_audio": False,
        "auto_summarize_after_transcription": False,
    }

