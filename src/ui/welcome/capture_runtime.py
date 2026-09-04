"""Persisted capture configuration and capture-entry actions for WelcomeWidget."""

from src.ui.welcome.capture_state import (
    build_recording_config,
    load_capture_settings,
    save_capture_settings,
)


class WelcomeCaptureRuntime:
    def __init__(self, widget):
        self.widget = widget

    def load_saved_config(self):
        load_capture_settings(self.widget.settings, **self._controls())

    def connect_config_signals(self):
        widget = self.widget
        for control, signal_name in (
            (widget.mic_combo, "currentIndexChanged"),
            (widget.model_combo, "currentIndexChanged"),
            (widget.lang_combo, "currentIndexChanged"),
            (widget.diarization_check, "toggled"),
            (widget.sys_audio_check, "toggled"),
            (widget.auto_summary_check, "toggled"),
        ):
            getattr(control, signal_name).connect(self.save_config)

    def save_config(self):
        save_capture_settings(self.widget.settings, **self._controls())
        self.widget.status_message_requested.emit("Recording configuration saved.")

    def get_recording_config(self):
        if self.widget.test_stream is not None:
            self.widget.stop_mic_test()
        return build_recording_config(**self._controls())

    def request_capture(self, signal):
        if self.widget.settings.value("audio_rescan_before_capture", True, type=bool):
            self.widget.populate_mics(keep_current=True)
        signal.emit(self.get_recording_config())

    def _controls(self):
        widget = self.widget
        return {
            "mic_combo": widget.mic_combo,
            "model_combo": widget.model_combo,
            "lang_combo": widget.lang_combo,
            "diarization_check": widget.diarization_check,
            "sys_audio_check": widget.sys_audio_check,
            "auto_summary_check": widget.auto_summary_check,
        }
