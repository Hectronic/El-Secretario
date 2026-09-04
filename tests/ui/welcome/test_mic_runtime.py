from unittest.mock import MagicMock

from src.ui.welcome.mic_runtime import WelcomeMicRuntime


def test_rescan_reports_detected_microphones(monkeypatch):
    widget = MagicMock()
    widget.mic_combo.count.return_value = 3
    runtime = WelcomeMicRuntime(widget)
    populate = MagicMock()
    monkeypatch.setattr(runtime, "populate_mics", populate)

    runtime.rescan(recorder_getter=MagicMock())

    populate.assert_called_once()
    widget.status_message_requested.emit.assert_called_once_with(
        "Audio re-scan complete: 2 input device(s) detected."
    )


def test_audio_callback_and_vu_update_share_runtime_amplitude(monkeypatch):
    widget = MagicMock()
    runtime = WelcomeMicRuntime(widget)
    monkeypatch.setattr("src.ui.welcome.mic_runtime.calculate_rms", lambda _data: 0.42)
    update = MagicMock()
    monkeypatch.setattr("src.ui.welcome.mic_runtime.update_vu_meter", update)

    runtime.audio_callback(object())
    runtime.update_vu()

    assert widget.current_amplitude == 0.42
    update.assert_called_once_with(widget.test_vu_meter, 0.42)
