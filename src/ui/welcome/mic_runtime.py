"""Microphone discovery and test-session orchestration for the welcome screen."""

import os

from src.ui.welcome.capture_state import populate_microphones
from src.ui.welcome.mic_test import calculate_rms, start_mic_test, stop_mic_test, update_vu_meter


class WelcomeMicRuntime:
    def __init__(self, widget):
        self.widget = widget

    def populate_mics(self, *, recorder_getter, keep_current=False):
        populate_microphones(
            self.widget.mic_combo,
            recorder_getter=recorder_getter,
            skip_audio_enum=os.environ.get("EL_SECRETARIO_SKIP_AUDIO_ENUM", "").strip().lower() in {"1", "true", "yes"},
            keep_current=keep_current,
        )

    def rescan(self, *, recorder_getter):
        self.populate_mics(recorder_getter=recorder_getter, keep_current=True)
        detected = max(0, self.widget.mic_combo.count() - 1)
        message = f"Audio re-scan complete: {detected} input device(s) detected." if detected else "Audio re-scan complete: no input devices detected, using default."
        self.widget.status_message_requested.emit(message)

    def start(self, *, sd_module):
        self.widget.test_stream = start_mic_test(
            sd_module=sd_module, device_index=self.widget.mic_combo.currentData(),
            audio_callback=self.audio_callback, vu_meter=self.widget.test_vu_meter,
            status_label=self.widget.test_status_label, test_button=self.widget.test_mic_btn,
            test_timer=self.widget.test_timer,
        )

    def stop(self):
        self.widget.test_stream = stop_mic_test(
            stream=self.widget.test_stream, vu_meter=self.widget.test_vu_meter,
            status_label=self.widget.test_status_label, test_button=self.widget.test_mic_btn,
            test_timer=self.widget.test_timer,
        )

    def toggle(self, *, sd_module):
        self.stop() if self.widget.test_stream is not None else self.start(sd_module=sd_module)

    def audio_callback(self, indata, *_args):
        self.widget.current_amplitude = calculate_rms(indata)

    def update_vu(self):
        update_vu_meter(self.widget.test_vu_meter, self.widget.current_amplitude)
