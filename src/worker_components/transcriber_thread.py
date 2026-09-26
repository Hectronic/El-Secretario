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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import platform
import tempfile
from types import SimpleNamespace

import torch
from PyQt6.QtCore import QSettings, QThread, pyqtSignal

from src.audio import trim_audio_segment
from src.resource_cleanup import release_local_inference_resources
from src.transcription_options import get_whisper_model_name, is_sherpa_onnx_model
from src.worker_components import device_selection as worker_device_selection
from src.worker_components import engine as worker_engine
from src.worker_components.error_messages import transcription_error_message
from src.worker_components import sherpa as worker_sherpa
from src.worker_components import runtime as worker_runtime
from src.worker_components import settings as worker_settings
from src.worker_components import subprocess_runner
from src.worker_components import transcription_flow
from src.worker_components.lifecycle import TerminalOutcomeEmitter, TerminalStatus
from src.worker_components.subprocess_runner import TranscriptionCancelledError, TranscriptionTimeoutError


def _run_transcription_in_subprocess(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    language: str,
    timeout_seconds: int = 1800,
):
    return subprocess_runner.run_transcription_in_subprocess(
        audio_path=audio_path,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        language=language,
        timeout_seconds=timeout_seconds,
    )


def _run_openai_whisper_fallback(*, audio_path: str, model_size: str, language: str):
    return subprocess_runner.run_openai_whisper_fallback(
        audio_path=audio_path,
        model_size=model_size,
        language=language,
    )


def _run_sherpa_onnx_transcription(*, audio_path: str, language: str, settings, status_callback=None) -> list[dict]:
    model_dir, model_config = worker_sherpa.ensure_sherpa_onnx_model_ready(
        settings,
        status_callback=status_callback,
    )
    return subprocess_runner.run_sherpa_onnx_transcription(
        audio_path=audio_path,
        language=language,
        model_dir=model_dir,
        model_config=model_config,
    )


def _get_pyannote_pipeline_class():
    return worker_runtime.get_pyannote_pipeline_class()


def _flush_log_handlers():
    return worker_runtime.flush_log_handlers()


def _log_transcription_runtime_context(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    force_cpu: bool,
    enable_diarization: bool,
    language: str,
):
    return worker_runtime.log_transcription_runtime_context(
        audio_path=audio_path,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        force_cpu=force_cpu,
        enable_diarization=enable_diarization,
        language=language,
    )


def _should_use_gpu_for_diarization(
    *,
    force_cpu: bool,
):
    return worker_runtime.should_use_gpu_for_diarization(
        force_cpu=force_cpu,
    )


def _is_cuda_runtime_failure(error: Exception) -> bool:
    out_of_memory = getattr(torch.cuda, "OutOfMemoryError", None)
    if out_of_memory and isinstance(error, out_of_memory):
        return True
    message = str(error).lower()
    return isinstance(error, RuntimeError) and any(
        marker in message for marker in ("cuda", "cudnn", "cublas", "out of memory", "device-side")
    )


class TranscriberThread(QThread):
    """Coordinate one audio transcription job from a Qt worker thread.

    The class owns orchestration only: backend selection, progress/status
    signals, optional diarization, result shaping and cleanup. Heavy STT work is
    delegated to subprocess helpers in ``src.worker_components`` so native libraries
    can crash or release memory without taking the UI process with them.
    """

    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)
    terminal = pyqtSignal(dict)

    def __init__(self, audio_path, model_size="base", device=None, compute_type=None, language=None, hf_token=None, enable_diarization=False, total_duration=0, force_cpu=False, backend_preference="auto"):
        """Create a transcription job.

        ``model_size`` is the UI-level option and may map to a provider-specific
        model. ``backend_preference`` accepts ``auto`` or a concrete backend
        name, but Sherpa-ONNX always forces CPU/ONNXRuntime settings.
        """
        super().__init__()
        self.audio_path = audio_path
        self.ui_model_name = model_size
        self.model_size = get_whisper_model_name(model_size)
        self.configured_force_cpu = bool(force_cpu)
        self.force_cpu = force_cpu
        self.backend_preference = backend_preference or "auto"
        self.effective_backend = "faster-whisper"
        self.is_sherpa_onnx = is_sherpa_onnx_model(model_size)

        if self.is_sherpa_onnx:
            self.device = "cpu"
            self.compute_type = "onnxruntime"
        elif device is None or compute_type is None:
            auto_device, auto_compute = worker_device_selection.get_optimal_device(force_cpu, model_size)
            self.device = device if device else auto_device
            self.compute_type = compute_type if compute_type else auto_compute
        else:
            self.device = device
            self.compute_type = compute_type

        if platform.system() == "Windows" and not self.is_sherpa_onnx:
            if self.device == "cpu":
                self.compute_type = "int8_float32"
            elif self.device == "cuda" and self.compute_type == "int8":
                self.compute_type = "float16"

        self.language = language
        self.hf_token = hf_token
        self.enable_diarization = enable_diarization
        self.total_duration = total_duration
        self._terminal = TerminalOutcomeEmitter()

    def _emit_terminal(self, status, *, user_message="", retryable=False, preserved_work=True):
        outcome = self._terminal.complete(
            status, user_message=user_message, retryable=retryable, preserved_work=preserved_work
        )
        if outcome is not None:
            self.terminal.emit(outcome.payload())

    def _persist_working_transcription_settings(self):
        try:
            settings = QSettings("Hectronic", "Secretario")
            worker_settings.persist_working_transcription_settings(
                settings,
                effective_backend=self.effective_backend,
                model_size=self.model_size,
                device=self.device,
                force_cpu=self.configured_force_cpu,
                compute_type=self.compute_type,
            )
        except Exception as e:
            logging.warning("Could not persist working transcription settings: %s", e)

    def _get_subprocess_attempt_timeout_seconds(self) -> int:
        try:
            settings = QSettings("Hectronic", "Secretario")
            return worker_settings.get_subprocess_attempt_timeout_for_duration_seconds(
                settings,
                total_duration_seconds=self.total_duration,
            )
        except Exception:
            return 120 if platform.system() == "Windows" else 600

    def _get_subprocess_attempt_timeout_seconds_for_duration(self, duration_seconds: float) -> int:
        try:
            settings = QSettings("Hectronic", "Secretario")
            return worker_settings.get_subprocess_attempt_timeout_for_duration_seconds(
                settings,
                total_duration_seconds=duration_seconds,
            )
        except Exception:
            return 120 if platform.system() == "Windows" else 600

    def _transcribe_faster_whisper_once(self, *, audio_path: str, duration_seconds: float):
        per_attempt_timeout = self._get_subprocess_attempt_timeout_seconds_for_duration(duration_seconds)
        fallback_result = worker_engine.run_faster_whisper_with_fallback(
            audio_path=audio_path,
            model_size=self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            language=self.language,
            per_attempt_timeout=per_attempt_timeout,
            status_emit=self.status_update.emit,
            flush_logs=_flush_log_handlers,
            run_transcription=_run_transcription_in_subprocess,
            run_openai_fallback=_run_openai_whisper_fallback,
        )
        self.model_size = fallback_result["model_size"]
        self.device = fallback_result["device"]
        self.compute_type = fallback_result["compute_type"]
        self.effective_backend = fallback_result["effective_backend"]
        self.force_cpu = self.device == "cpu"
        return fallback_result["segments"]

    def _transcribe_faster_whisper_chunked(self, *, chunk_cfg: dict):
        total_duration = float(self.total_duration or 0.0)
        chunk_size = float(chunk_cfg["chunk_size_seconds"])
        overlap = float(chunk_cfg["overlap_seconds"])
        step = max(1.0, chunk_size - overlap)

        self.status_update.emit(
            f"Long recording detected ({int(total_duration)}s). Transcribing in chunks of {int(chunk_size)}s..."
        )
        merged_segments = []
        chunk_start = 0.0
        chunk_index = 0

        with tempfile.TemporaryDirectory(prefix="secretario_stt_chunk_") as tmp_dir:
            while chunk_start < total_duration:
                if self.isInterruptionRequested():
                    self.status_update.emit("Cancelled.")
                    return []
                chunk_end = min(total_duration, chunk_start + chunk_size)
                chunk_duration = max(0.0, chunk_end - chunk_start)
                if chunk_duration <= 0:
                    break

                chunk_index += 1
                self.status_update.emit(
                    f"Chunk {chunk_index}: {int(chunk_start)}s-{int(chunk_end)}s ({int(chunk_duration)}s)"
                )
                chunk_file = os.path.join(tmp_dir, f"chunk_{chunk_index:04d}.wav")
                trim_audio_segment(self.audio_path, chunk_start, chunk_end, chunk_file)

                chunk_segments = self._transcribe_faster_whisper_once(
                    audio_path=chunk_file,
                    duration_seconds=chunk_duration,
                )
                for seg in chunk_segments:
                    start = float(seg.get("start", 0.0)) + chunk_start
                    end = float(seg.get("end", start)) + chunk_start
                    merged_segments.append({**seg, "start": start, "end": end})

                chunk_start += step

        merged_segments.sort(key=lambda s: float(s.get("start", 0.0)))
        return merged_segments

    def run(self):
        try:
            import time

            start_time = time.time()
            settings = QSettings("Hectronic", "Secretario")

            logging.info(f"Starting transcription for {self.audio_path} (Model: {self.model_size}, Diarization: {self.enable_diarization})")
            _log_transcription_runtime_context(
                audio_path=self.audio_path,
                model_size=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                force_cpu=self.force_cpu,
                enable_diarization=self.enable_diarization,
                language=self.language,
            )

            serialized_segments = None
            if self.is_sherpa_onnx:
                self.status_update.emit("Loading sherpa-onnx model...")
                self.progress.emit(-1)
                self.effective_backend = "sherpa-onnx"
                self.status_update.emit("Transcribing...")
                serialized_segments = _run_sherpa_onnx_transcription(
                    audio_path=self.audio_path,
                    language=self.language,
                    settings=settings,
                    status_callback=self.status_update.emit,
                )
                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
            elif self.backend_preference == "openai-whisper":
                self.status_update.emit("Loading model...")
                self.progress.emit(-1)
                self.effective_backend = "openai-whisper"
                self.status_update.emit("Transcribing...")
                serialized_segments = _run_openai_whisper_fallback(
                    audio_path=self.audio_path,
                    model_size=self.model_size,
                    language=self.language,
                )
                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
            else:
                self.status_update.emit("Loading model...")
                self.progress.emit(-1)
                self.effective_backend = "faster-whisper"
                logging.info(
                    "Whisper checkpoint W1: subprocess isolation enabled (backend=%s model=%s device=%s compute_type=%s)",
                    self.effective_backend,
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                _flush_log_handlers()
                chunk_cfg = worker_settings.get_transcription_chunking_config(settings)
                should_chunk = (
                    chunk_cfg.get("enabled", True)
                    and self.total_duration > 0
                    and float(self.total_duration) >= float(chunk_cfg.get("threshold_seconds", 1800))
                )
                if should_chunk:
                    serialized_segments = self._transcribe_faster_whisper_chunked(chunk_cfg=chunk_cfg)
                else:
                    serialized_segments = self._transcribe_faster_whisper_once(
                        audio_path=self.audio_path,
                        duration_seconds=float(self.total_duration or 0.0),
                    )
                if self.isInterruptionRequested():
                    self.status_update.emit("Cancelled.")
                    self._emit_terminal(TerminalStatus.CANCELLED, user_message="Transcription cancelled.", retryable=True)
                    return

                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
                logging.info("Whisper checkpoint W2: subprocess transcription completed.")
                _flush_log_handlers()

            self.status_update.emit("Transcribing...")
            for segment in whisper_segments:
                if self.isInterruptionRequested():
                    self.status_update.emit("Cancelled.")
                    self._emit_terminal(TerminalStatus.CANCELLED, user_message="Transcription cancelled.", retryable=True)
                    return
                if self.total_duration > 0:
                    prog = transcription_flow.compute_segment_progress(
                        segment.end,
                        self.total_duration,
                        self.enable_diarization,
                    )
                    self.progress.emit(min(prog, 100))

            diarization = None
            pipeline_cls = (
                _get_pyannote_pipeline_class()
                if (self.enable_diarization and self.hf_token)
                else None
            )
            if self.enable_diarization and self.hf_token and pipeline_cls:
                self.status_update.emit("Diarizing (this may take a while)...")
                logging.info("Starting diarization...")
                self.progress.emit(80)
                try:
                    if self.isInterruptionRequested():
                        self.status_update.emit("Cancelled.")
                        self._emit_terminal(TerminalStatus.CANCELLED, user_message="Transcription cancelled.", retryable=True)
                        return
                    last_diarization_progress = [80]
                    last_diarization_stage = [None]
                    last_stage_percent = {}
                    diarization_stage_ranges = {
                        "segmentation": (80, 84, "segmentation"),
                        "speaker_counting": (84, 85, "speaker counting"),
                        "embeddings": (85, 89, "embeddings"),
                        "discrete_diarization": (89, 90, "reconstructing diarization"),
                    }

                    def report_diarization_progress(step_name, _artifact, **progress_info):
                        stage = str(step_name).lower()
                        lower, upper, label = diarization_stage_ranges.get(
                            stage, (last_diarization_progress[0], 90, stage.replace("_", " "))
                        )
                        total = progress_info.get("total")
                        completed = progress_info.get("completed")
                        if stage == "embeddings" and total is None and completed is None:
                            label = "speaker clustering"
                        stage_identity = (stage, label)
                        stage_changed = stage_identity != last_diarization_stage[0]

                        if total and completed is not None:
                            ratio = min(1.0, max(0.0, float(completed) / float(total)))
                            current = min(upper, lower + int((upper - lower) * ratio))
                            percent = int(ratio * 100)
                            if current > last_diarization_progress[0]:
                                last_diarization_progress[0] = current
                                self.progress.emit(current)
                            if stage_changed or last_stage_percent.get(stage) != percent:
                                self.status_update.emit(
                                    f"Diarizing: {label} ({int(completed)}/{int(total)})"
                                )
                            last_stage_percent[stage] = percent
                        else:
                            # pyannote reports stage boundaries without counters
                            # (speaker counting and clustering can still take time).
                            if stage_changed:
                                current = min(upper, max(lower, last_diarization_progress[0]))
                                if current > last_diarization_progress[0]:
                                    last_diarization_progress[0] = current
                                    self.progress.emit(current)
                                self.status_update.emit(f"Diarizing: {label}...")

                        last_diarization_stage[0] = stage_identity

                    should_move_to_gpu, gpu_reason = _should_use_gpu_for_diarization(
                        force_cpu=self.force_cpu,
                    )

                    def load_diarization_pipeline(use_gpu: bool):
                        loaded = pipeline_cls.from_pretrained(
                            "pyannote/speaker-diarization-3.1",
                            use_auth_token=self.hf_token,
                        )
                        if loaded:
                            loaded = loaded.to(torch.device("cuda" if use_gpu else "cpu"))
                            segmentation_step = worker_runtime.configure_long_audio_diarization_stride(
                                loaded,
                                duration_seconds=self.total_duration,
                            )
                            if segmentation_step is not None:
                                logging.info(
                                    "Long-audio pyannote segmentation stride set to %.2fs per window (ratio=0.25).",
                                    segmentation_step,
                                )
                        return loaded

                    try:
                        pipeline = load_diarization_pipeline(should_move_to_gpu)
                    except Exception as gpu_load_error:
                        if not should_move_to_gpu or not _is_cuda_runtime_failure(gpu_load_error):
                            raise
                        logging.warning("Could not load pyannote on CUDA; retrying on CPU: %s", gpu_load_error)
                        self.status_update.emit("GPU diarization could not start; retrying on CPU...")
                        try:
                            torch.cuda.empty_cache()
                        except Exception:
                            pass
                        pipeline = load_diarization_pipeline(False)
                        should_move_to_gpu = False
                        gpu_reason = f"CUDA initialization failed; CPU fallback: {gpu_load_error}"
                    if pipeline:
                        logging.info(
                            "Pyannote pipeline device=%s. Reason: %s",
                            "cuda" if should_move_to_gpu else "cpu",
                            gpu_reason,
                        )
                        free_vram_gb = None
                        if should_move_to_gpu:
                            try:
                                free_bytes, _total_bytes = torch.cuda.mem_get_info()
                                free_vram_gb = free_bytes / (1024 ** 3)
                            except Exception as memory_error:
                                logging.warning("Could not read free VRAM for pyannote batch sizing: %s", memory_error)
                        segmentation_batch, embedding_batch = worker_runtime.diarization_batch_sizes(
                            use_gpu=should_move_to_gpu,
                            free_vram_gb=free_vram_gb,
                        )
                        try:
                            pipeline.segmentation_batch_size = segmentation_batch
                            pipeline.embedding_batch_size = embedding_batch
                        except Exception as batch_error:
                            logging.warning("Could not configure pyannote inference batches: %s", batch_error)
                        logging.info(
                            "Pyannote inference batches: segmentation=%s embedding=%s free_vram_gb=%s",
                            segmentation_batch,
                            embedding_batch,
                            f"{free_vram_gb:.2f}" if free_vram_gb is not None else "unknown",
                        )

                    diarization_started_at = time.time()
                    try:
                        diarization = pipeline(self.audio_path, hook=report_diarization_progress)
                    except Exception as gpu_error:
                        if not should_move_to_gpu or not _is_cuda_runtime_failure(gpu_error):
                            raise
                        logging.warning(
                            "CUDA diarization failed; retrying pyannote on CPU: %s",
                            gpu_error,
                            exc_info=True,
                        )
                        self.status_update.emit("GPU diarization failed; retrying on CPU...")
                        del pipeline
                        try:
                            torch.cuda.empty_cache()
                        except Exception:
                            pass
                        pipeline = load_diarization_pipeline(False)
                        if pipeline:
                            pipeline.segmentation_batch_size = 1
                            pipeline.embedding_batch_size = 1
                            diarization = pipeline(self.audio_path, hook=report_diarization_progress)
                    logging.info(
                        "Diarization completed successfully in %.2fs.",
                        time.time() - diarization_started_at,
                    )
                except Exception as e:
                    logging.error(f"Diarization failed: {e}", exc_info=True)
            elif self.enable_diarization and self.hf_token and not pipeline_cls:
                logging.warning("Diarization requested but pyannote.audio is unavailable.")

            self.status_update.emit("Merging results...")
            if self.enable_diarization:
                self.progress.emit(90)

            for segment in whisper_segments:
                if self.isInterruptionRequested():
                    self.status_update.emit("Cancelled.")
                    return
            transcription = transcription_flow.merge_segments_text(whisper_segments, diarization)

            end_time = time.time()
            transcription_time = end_time - start_time

            result = {
                "text": transcription.strip(),
                "model_name": self.model_size,
                "backend": self.effective_backend,
                "device": self.device,
                "compute_type": self.compute_type,
                "transcription_time": transcription_time,
                "audio_duration": self.total_duration,
                "audio_size_bytes": os.path.getsize(self.audio_path),
                "is_diarized": self.enable_diarization,
            }

            self._persist_working_transcription_settings()

            logging.info(f"Transcription finished in {transcription_time:.2f}s")
            self.progress.emit(100)
            self.status_update.emit("Finished.")
            self.finished.emit(result)

            self._emit_terminal(TerminalStatus.SUCCEEDED)

        except TranscriptionCancelledError:
            self.status_update.emit("Cancelled.")
            self._emit_terminal(TerminalStatus.CANCELLED, user_message="Transcription cancelled.", retryable=True)
        except TranscriptionTimeoutError as error:
            message = transcription_error_message(error)
            logging.error("Transcription timed out: %s", error, exc_info=True)
            self.error.emit(message)
            self._emit_terminal(TerminalStatus.TIMED_OUT, user_message=message, retryable=True)
        except Exception as e:
            logging.error(f"Transcription failed: {e}", exc_info=True)
            message = transcription_error_message(e)
            self.error.emit(message)
            self._emit_terminal(TerminalStatus.FAILED, user_message=message, retryable=True)
        finally:
            if "pipeline" in locals():
                del pipeline
            if "diarization" in locals():
                del diarization

            release_local_inference_resources()
