from unittest.mock import MagicMock

from src.ui.welcome.capture_runtime import WelcomeCaptureRuntime


def test_capture_request_rescans_and_emits_current_configuration(monkeypatch):
    widget = MagicMock()
    widget.settings.value.return_value = True
    widget.test_stream = None
    runtime = WelcomeCaptureRuntime(widget)
    monkeypatch.setattr(runtime, "get_recording_config", lambda: {"model": "base"})

    runtime.request_capture(widget.new_recording_requested)

    widget.populate_mics.assert_called_once_with(keep_current=True)
    widget.new_recording_requested.emit.assert_called_once_with({"model": "base"})
