"""Recorder lifecycle isolated from the in-progress recording widget."""

import logging


class RecordingCaptureRuntime:
    """Own recorder configuration, lifecycle calls, and amplitude cleanup."""

    def __init__(self, recorder, on_amplitude):
        self.recorder = recorder
        self.on_amplitude = on_amplitude
        self._amplitude_connected = False
        self.recorder.amplitude_changed.connect(self.on_amplitude)
        self._amplitude_connected = True

    def configure(self, config):
        if config.get("device_index") is not None:
            self.recorder.set_device(config["device_index"])
        if config.get("capture_system_audio"):
            self.recorder.set_capture_machine_audio(True)

    def start(self):
        try:
            if not self.recorder.is_recording:
                self.recorder.start()
            return None
        except Exception as error:
            logging.exception("Failed to start recording in RecordingCaptureRuntime.")
            return error

    def toggle_pause(self):
        if self.recorder.is_paused:
            self.recorder.resume()
            return False
        self.recorder.pause()
        return True

    def stop(self):
        try:
            return self.recorder.stop()
        except Exception:
            logging.exception("Exception while stopping recorder.")
            return None

    def cancel(self, recording_started):
        if not recording_started:
            return
        try:
            self.recorder.stop()
        except Exception:
            logging.exception("Exception while cancelling recorder.")

    def cleanup(self):
        if not self._amplitude_connected:
            return
        try:
            self.recorder.amplitude_changed.disconnect(self.on_amplitude)
        except Exception:
            pass
        self._amplitude_connected = False
