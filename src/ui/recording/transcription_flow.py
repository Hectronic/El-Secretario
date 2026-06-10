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

from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtWidgets import QMessageBox


LANGUAGE_CODES = {"Auto": None, "Spanish": "es", "English": "en"}


@dataclass(frozen=True)
class DirectTranscriptionConfig:
    model_size: str
    language_code: Optional[str]
    hf_token: str
    enable_diarization: bool
    force_cpu: bool
    compute_type: Optional[str]
    backend_preference: str
    total_duration: float

    def worker_kwargs(self):
        return {
            "model_size": self.model_size,
            "compute_type": self.compute_type,
            "language": self.language_code,
            "hf_token": self.hf_token,
            "enable_diarization": self.enable_diarization,
            "total_duration": self.total_duration,
            "force_cpu": self.force_cpu,
            "backend_preference": self.backend_preference,
        }


def language_code_from_label(label):
    return LANGUAGE_CODES.get(label)


def normalize_compute_type(value):
    return None if value == "auto" else value


def probe_audio_duration(audio_path, sound_file_cls):
    try:
        with sound_file_cls(audio_path) as audio_file:
            return len(audio_file) / audio_file.samplerate
    except Exception:
        return 0


def build_direct_transcription_config(
    *,
    settings,
    audio_path,
    model_size,
    language_label,
    enable_diarization,
    sound_file_cls,
):
    return DirectTranscriptionConfig(
        model_size=model_size,
        language_code=language_code_from_label(language_label),
        hf_token=settings.value("hf_token", ""),
        enable_diarization=enable_diarization,
        force_cpu=settings.value("force_cpu", False, type=bool),
        compute_type=normalize_compute_type(settings.value("compute_type", "auto")),
        backend_preference=settings.value("transcription_backend", "auto"),
        total_duration=probe_audio_duration(audio_path, sound_file_cls),
    )


def create_transcriber_thread(thread_cls, audio_path, config: DirectTranscriptionConfig):
    return thread_cls(audio_path, **config.worker_kwargs())


def wire_transcriber_thread(widget, thread):
    thread.finished.connect(widget.on_transcription_finished)
    thread.progress.connect(widget.progress_changed.emit)
    thread.status_update.connect(widget._on_transcriber_status_update)
    thread.error.connect(widget.on_transcription_error)
    thread.finished.connect(widget._clear_transcriber_thread_ref)
    thread.error.connect(widget._clear_transcriber_thread_ref)


def start_direct_transcription(
    widget,
    audio_path,
    *,
    settings,
    model_size,
    language_label,
    enable_diarization,
    thread_cls,
    preflight_check: Callable,
    sound_file_cls,
    message_box=QMessageBox,
):
    widget.status_changed.emit("Processing transcription...")
    widget.progress_changed.emit(0)
    widget.retranscribe_btn.setEnabled(False)

    preflight_error = preflight_check(model_size, settings)
    if preflight_error:
        widget.status_changed.emit("Failed.")
        widget.progress_changed.emit(-2)
        widget.retranscribe_btn.setEnabled(True)
        message_box.critical(widget, "Transcription Error", preflight_error)
        return None

    config = build_direct_transcription_config(
        settings=settings,
        audio_path=audio_path,
        model_size=model_size,
        language_label=language_label,
        enable_diarization=enable_diarization,
        sound_file_cls=sound_file_cls,
    )
    thread = create_transcriber_thread(thread_cls, audio_path, config)
    wire_transcriber_thread(widget, thread)
    thread.start()
    return thread


def emit_finished_trace(summary_task_queue, record_id, result):
    if not summary_task_queue or not hasattr(summary_task_queue, "add_external_trace"):
        return
    backend = result.get("backend", "unknown")
    model_name = result.get("model_name", "unknown")
    device = result.get("device", "unknown")
    compute_type = result.get("compute_type", "unknown")
    summary_task_queue.add_external_trace(
        f"Direct transcription finished: backend={backend}, model={model_name}, device={device}, compute={compute_type}",
        {"type": "transcription", "record_id": record_id or -1, "source": "recording"},
        event="finished",
    )


def emit_error_trace(summary_task_queue, record_id, err):
    if not summary_task_queue or not hasattr(summary_task_queue, "add_external_trace"):
        return
    summary_task_queue.add_external_trace(
        f"Direct transcription failed: {err}",
        {"type": "transcription", "record_id": record_id or -1, "source": "recording"},
        event="failed",
    )


def emit_status_trace(summary_task_queue, record_id, message):
    if not summary_task_queue or not hasattr(summary_task_queue, "add_external_trace"):
        return
    summary_task_queue.add_external_trace(
        message,
        {"type": "transcription", "record_id": record_id or -1, "source": "recording"},
        event="trace",
    )


def log_transcription_metrics(db, record_id, result):
    db.log_transcription(
        model_name=result["model_name"],
        audio_duration=result["audio_duration"],
        audio_size_bytes=result["audio_size_bytes"],
        transcription_time_seconds=result["transcription_time"],
        record_id=record_id,
    )


def persist_direct_transcription_result(db, current_record_id, filename, result):
    text = result["text"]
    duration = result["audio_duration"]
    is_diarized = result.get("is_diarized", False)
    model_name = result.get("model_name")

    if current_record_id:
        log_transcription_metrics(db, current_record_id, result)
        db.update_transcription(
            current_record_id,
            text,
            is_diarized=is_diarized,
            transcription_model=model_name,
        )
        db.update_duration(current_record_id, duration)
        return current_record_id

    new_record_id = db.save(
        filename,
        text,
        duration,
        is_diarized=is_diarized,
        transcription_model=model_name,
    )
    log_transcription_metrics(db, new_record_id, result)
    return new_record_id
