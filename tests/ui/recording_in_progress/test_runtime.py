from PyQt6.QtCore import QObject, pyqtSignal

from src.ui.recording_in_progress.runtime import RecordingCaptureRuntime


class _Recorder(QObject):
    amplitude_changed = pyqtSignal(float)

    def __init__(self, stop_result="capture.wav"):
        super().__init__()
        self.is_recording = False
        self.is_paused = False
        self.stop_result = stop_result
        self.device = None
        self.system_audio = False
        self.stop_calls = 0

    def set_device(self, value):
        self.device = value

    def set_capture_machine_audio(self, value):
        self.system_audio = value

    def start(self):
        self.is_recording = True

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.stop_calls += 1
        self.is_recording = False
        return self.stop_result


def test_runtime_configures_and_drives_recorder_lifecycle():
    recorder = _Recorder()
    amplitudes = []
    runtime = RecordingCaptureRuntime(recorder, amplitudes.append)

    runtime.configure({"device_index": 4, "capture_system_audio": True})
    assert runtime.start() is None
    assert runtime.toggle_pause() is True
    assert runtime.toggle_pause() is False
    assert runtime.stop() == "capture.wav"
    recorder.amplitude_changed.emit(0.4)
    runtime.cleanup()
    recorder.amplitude_changed.emit(0.8)

    assert recorder.device == 4
    assert recorder.system_audio is True
    assert recorder.stop_calls == 1
    assert amplitudes == [0.4]


def test_runtime_cancel_only_stops_active_recording():
    recorder = _Recorder()
    runtime = RecordingCaptureRuntime(recorder, lambda _value: None)

    runtime.cancel(False)
    runtime.cancel(True)

    assert recorder.stop_calls == 1
