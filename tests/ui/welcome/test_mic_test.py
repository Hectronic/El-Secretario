# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QProgressBar

from src.ui.welcome.mic_test import (
    STOP_BUTTON_STYLE,
    TEST_BUTTON_STYLE,
    VU_STYLE_HIGH,
    VU_STYLE_LOW,
    VU_STYLE_MEDIUM,
    calculate_rms,
    start_mic_test,
    stop_mic_test,
    update_vu_meter,
    vu_value,
)


_APP = None


def _ensure_app():
    global _APP
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _APP = app
    return app


class _Timer:
    def __init__(self):
        self.started_with = None
        self.stopped = False

    def start(self, interval):
        self.started_with = interval

    def stop(self):
        self.stopped = True


class _Stream:
    def __init__(self, *, fail_stop=False):
        self.started = False
        self.stopped = False
        self.closed = False
        self.fail_stop = fail_stop

    def start(self):
        self.started = True

    def stop(self):
        if self.fail_stop:
            raise RuntimeError("stop failed")
        self.stopped = True

    def close(self):
        self.closed = True


class _SoundDevice:
    def __init__(self, fail_rates=(), stream=None):
        self.fail_rates = set(fail_rates)
        self.stream = stream or _Stream()
        self.calls = []

    def InputStream(self, samplerate, channels, callback, device):
        self.calls.append(
            {
                "samplerate": samplerate,
                "channels": channels,
                "callback": callback,
                "device": device,
            }
        )
        if samplerate in self.fail_rates:
            raise RuntimeError("rate failed")
        return self.stream


def _widgets():
    _ensure_app()
    return QProgressBar(), QLabel(), QPushButton(), _Timer()


def test_start_mic_test_starts_first_working_stream():
    vu_meter, status_label, button, timer = _widgets()
    sd_module = _SoundDevice()
    callback = object()

    stream = start_mic_test(
        sd_module=sd_module,
        device_index=7,
        audio_callback=callback,
        vu_meter=vu_meter,
        status_label=status_label,
        test_button=button,
        test_timer=timer,
        sample_rates=(16000,),
    )

    assert stream is sd_module.stream
    assert stream.started is True
    assert sd_module.calls[0]["device"] == 7
    assert sd_module.calls[0]["callback"] is callback
    assert timer.started_with == 50
    assert button.text() == "⏹ Stop"
    assert button.styleSheet() == STOP_BUTTON_STYLE
    assert status_label.text() == "Testing at 16000 Hz - Speak into the mic..."


def test_start_mic_test_tries_later_sample_rates_after_failure():
    vu_meter, status_label, button, timer = _widgets()
    sd_module = _SoundDevice(fail_rates={16000})

    stream = start_mic_test(
        sd_module=sd_module,
        device_index=None,
        audio_callback=lambda *_args: None,
        vu_meter=vu_meter,
        status_label=status_label,
        test_button=button,
        test_timer=timer,
        sample_rates=(16000, 44100),
    )

    assert stream is sd_module.stream
    assert [call["samplerate"] for call in sd_module.calls] == [16000, 44100]
    assert status_label.text() == "Testing at 44100 Hz - Speak into the mic..."


def test_start_mic_test_reports_error_when_all_rates_fail():
    vu_meter, status_label, button, timer = _widgets()
    sd_module = _SoundDevice(fail_rates={16000, 44100})

    stream = start_mic_test(
        sd_module=sd_module,
        device_index=None,
        audio_callback=lambda *_args: None,
        vu_meter=vu_meter,
        status_label=status_label,
        test_button=button,
        test_timer=timer,
        sample_rates=(16000, 44100),
    )

    assert stream is None
    assert status_label.text() == "Error: Could not open audio device"
    assert "color: #f44336" in status_label.styleSheet()


def test_stop_mic_test_resets_ui_and_tolerates_stream_errors():
    vu_meter, status_label, button, timer = _widgets()
    stream = _Stream(fail_stop=True)
    vu_meter.setValue(77)
    status_label.show()

    result = stop_mic_test(
        stream=stream,
        vu_meter=vu_meter,
        status_label=status_label,
        test_button=button,
        test_timer=timer,
    )

    assert result is None
    assert timer.stopped is True
    assert vu_meter.value() == 0
    assert button.text() == "🎤 Test"
    assert button.styleSheet() == TEST_BUTTON_STYLE


def test_calculate_rms_and_vu_values():
    rms = calculate_rms(np.array([[0.3], [0.4]], dtype=float))

    assert rms == np.sqrt((0.09 + 0.16) / 2)
    assert vu_value(0.02) == 20
    assert vu_value(0.2) == 100


def test_update_vu_meter_applies_level_styles():
    vu_meter, _status_label, _button, _timer = _widgets()

    assert update_vu_meter(vu_meter, 0.02) == 20
    assert vu_meter.styleSheet() == VU_STYLE_LOW

    assert update_vu_meter(vu_meter, 0.04) == 40
    assert vu_meter.styleSheet() == VU_STYLE_MEDIUM

    assert update_vu_meter(vu_meter, 0.08) == 80
    assert vu_meter.styleSheet() == VU_STYLE_HIGH

