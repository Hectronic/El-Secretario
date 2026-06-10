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
# along with this program.  See <https://www.gnu.org/licenses/>.

from unittest.mock import MagicMock

from src.ui.recording.transcription_flow import (
    build_direct_transcription_config,
    language_code_from_label,
    emit_error_trace,
    emit_finished_trace,
    emit_status_trace,
    normalize_compute_type,
    persist_direct_transcription_result,
    probe_audio_duration,
    start_direct_transcription,
)


class FakeSettings:
    def __init__(self):
        self.values = {
            "hf_token": "hf_x",
            "force_cpu": True,
            "compute_type": "auto",
            "transcription_backend": "faster-whisper",
        }

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        if type is bool:
            return bool(value)
        return value


class FakeSoundFile:
    def __init__(self, _path):
        self.samplerate = 1000

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __len__(self):
        return 2500


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class FakeButton:
    def __init__(self):
        self.enabled_values = []

    def setEnabled(self, value):
        self.enabled_values.append(value)


class FakeThread:
    def __init__(self, audio_path, **kwargs):
        self.audio_path = audio_path
        self.kwargs = kwargs
        self.finished = Signal()
        self.progress = Signal()
        self.status_update = Signal()
        self.error = Signal()
        self.started = False

    def start(self):
        self.started = True


class FakeWidget:
    def __init__(self):
        self.status_changed = Signal()
        self.progress_changed = Signal()
        self.retranscribe_btn = FakeButton()
        self.statuses = []
        self.progresses = []
        self.finished_results = []
        self.errors = []
        self.status_updates = []
        self.clear_calls = 0
        self.status_changed.connect(self.statuses.append)
        self.progress_changed.connect(self.progresses.append)

    def on_transcription_finished(self, result):
        self.finished_results.append(result)

    def _on_transcriber_status_update(self, message):
        self.status_updates.append(message)

    def on_transcription_error(self, err):
        self.errors.append(err)

    def _clear_transcriber_thread_ref(self, *_args):
        self.clear_calls += 1


def test_language_and_compute_type_normalization():
    assert language_code_from_label("Auto") is None
    assert language_code_from_label("Spanish") == "es"
    assert language_code_from_label("English") == "en"
    assert language_code_from_label("Other") is None
    assert normalize_compute_type("auto") is None
    assert normalize_compute_type("int8") == "int8"


def test_build_direct_transcription_config_preserves_runtime_preferences():
    config = build_direct_transcription_config(
        settings=FakeSettings(),
        audio_path="audio.wav",
        model_size="base",
        language_label="Spanish",
        enable_diarization=True,
        sound_file_cls=FakeSoundFile,
    )

    assert config.worker_kwargs() == {
        "model_size": "base",
        "compute_type": None,
        "language": "es",
        "hf_token": "hf_x",
        "enable_diarization": True,
        "total_duration": 2.5,
        "force_cpu": True,
        "backend_preference": "faster-whisper",
    }


def test_probe_audio_duration_returns_zero_on_failure():
    class BrokenSoundFile:
        def __init__(self, _path):
            raise RuntimeError("bad audio")

    assert probe_audio_duration("missing.wav", BrokenSoundFile) == 0


def test_start_direct_transcription_preflight_error_does_not_create_thread():
    widget = FakeWidget()
    message_box = MagicMock()

    thread = start_direct_transcription(
        widget,
        "audio.wav",
        settings=FakeSettings(),
        model_size="sherpa-onnx",
        language_label="Auto",
        enable_diarization=False,
        thread_cls=FakeThread,
        preflight_check=lambda _model, _settings: "missing model",
        sound_file_cls=FakeSoundFile,
        message_box=message_box,
    )

    assert thread is None
    assert widget.statuses == ["Processing transcription...", "Failed."]
    assert widget.progresses == [0, -2]
    assert widget.retranscribe_btn.enabled_values == [False, True]
    message_box.critical.assert_called_once_with(widget, "Transcription Error", "missing model")


def test_start_direct_transcription_creates_wires_and_starts_thread():
    widget = FakeWidget()

    thread = start_direct_transcription(
        widget,
        "audio.wav",
        settings=FakeSettings(),
        model_size="base",
        language_label="English",
        enable_diarization=True,
        thread_cls=FakeThread,
        preflight_check=lambda _model, _settings: None,
        sound_file_cls=FakeSoundFile,
    )

    assert thread.started is True
    assert thread.audio_path == "audio.wav"
    assert thread.kwargs["language"] == "en"
    assert thread.kwargs["total_duration"] == 2.5
    assert widget.statuses == ["Processing transcription..."]
    assert widget.progresses == [0]

    thread.progress.emit(35)
    thread.status_update.emit("Chunk 1")
    thread.finished.emit({"text": "done"})
    thread.error.emit("bad")

    assert widget.progresses == [0, 35]
    assert widget.status_updates == ["Chunk 1"]
    assert widget.finished_results == [{"text": "done"}]
    assert widget.errors == ["bad"]
    assert widget.clear_calls == 2


def _result_payload():
    return {
        "text": "Transcript",
        "model_name": "base",
        "audio_duration": 12.5,
        "audio_size_bytes": 4096,
        "transcription_time": 1.25,
        "is_diarized": True,
        "backend": "faster-whisper",
        "device": "cuda",
        "compute_type": "float16",
    }


def test_finished_error_and_status_traces_use_recording_payload():
    queue = MagicMock()

    emit_finished_trace(queue, 9, _result_payload())
    emit_error_trace(queue, 9, "boom")
    emit_status_trace(queue, 9, "Loading model")

    assert queue.add_external_trace.call_args_list[0].args[0] == (
        "Direct transcription finished: backend=faster-whisper, model=base, device=cuda, compute=float16"
    )
    assert queue.add_external_trace.call_args_list[0].args[1] == {
        "type": "transcription",
        "record_id": 9,
        "source": "recording",
    }
    assert queue.add_external_trace.call_args_list[0].kwargs == {"event": "finished"}
    assert queue.add_external_trace.call_args_list[1].args[0] == "Direct transcription failed: boom"
    assert queue.add_external_trace.call_args_list[1].kwargs == {"event": "failed"}
    assert queue.add_external_trace.call_args_list[2].args[0] == "Loading model"
    assert queue.add_external_trace.call_args_list[2].kwargs == {"event": "trace"}


def test_persist_direct_transcription_result_updates_existing_record_and_logs_metrics():
    db = MagicMock()

    record_id = persist_direct_transcription_result(db, 7, "call.wav", _result_payload())

    assert record_id == 7
    db.log_transcription.assert_called_once_with(
        model_name="base",
        audio_duration=12.5,
        audio_size_bytes=4096,
        transcription_time_seconds=1.25,
        record_id=7,
    )
    db.update_transcription.assert_called_once_with(
        7,
        "Transcript",
        is_diarized=True,
        transcription_model="base",
    )
    db.update_duration.assert_called_once_with(7, 12.5)
    db.save.assert_not_called()


def test_persist_direct_transcription_result_saves_new_record_then_logs_metrics():
    db = MagicMock()
    db.save.return_value = 11

    record_id = persist_direct_transcription_result(db, None, "call.wav", _result_payload())

    assert record_id == 11
    db.save.assert_called_once_with(
        "call.wav",
        "Transcript",
        12.5,
        is_diarized=True,
        transcription_model="base",
    )
    db.log_transcription.assert_called_once_with(
        model_name="base",
        audio_duration=12.5,
        audio_size_bytes=4096,
        transcription_time_seconds=1.25,
        record_id=11,
    )
    db.update_transcription.assert_not_called()
    db.update_duration.assert_not_called()
