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

import gc
import logging
import os
import platform
from types import SimpleNamespace

import torch
from PyQt6.QtCore import QSettings, QThread, pyqtSignal

from src.transcription_options import get_whisper_model_name, is_sherpa_onnx_model
from src.worker_components import transcription_flow, settings as worker_settings


class TranscriberThread(QThread):
    """Coordinate one audio transcription job from a Qt worker thread.

    The class owns orchestration only: backend selection, progress/status
    signals, optional diarization, result shaping and cleanup. Heavy STT work is
    delegated to subprocess helpers through ``src.worker`` so native libraries
    can crash or release memory without taking the UI process with them.
    """

    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    @staticmethod
    def _worker_api():
        import src.worker as worker_api

        return worker_api

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

        api = self._worker_api()
        if self.is_sherpa_onnx:
            self.device = "cpu"
            self.compute_type = "onnxruntime"
        elif device is None or compute_type is None:
            auto_device, auto_compute = api.get_optimal_device(force_cpu, model_size)
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

    def _persist_working_transcription_settings(self):
        try:
            api = self._worker_api()
            settings = api.QSettings("Hectronic", "Secretario")
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
            api = self._worker_api()
            settings = api.QSettings("Hectronic", "Secretario")
            return worker_settings.get_subprocess_attempt_timeout_seconds(settings)
        except Exception:
            return 120 if platform.system() == "Windows" else 1800

    def run(self):
        try:
            import time

            api = self._worker_api()
            start_time = time.time()
            settings = api.QSettings("Hectronic", "Secretario")

            logging.info(f"Starting transcription for {self.audio_path} (Model: {self.model_size}, Diarization: {self.enable_diarization})")
            api._log_transcription_runtime_context(
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
                serialized_segments = api._run_sherpa_onnx_transcription(
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
                serialized_segments = api._run_openai_whisper_fallback(
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
                api._flush_log_handlers()
                per_attempt_timeout = self._get_subprocess_attempt_timeout_seconds()
                fallback_result = api.worker_engine.run_faster_whisper_with_fallback(
                    audio_path=self.audio_path,
                    model_size=self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    language=self.language,
                    per_attempt_timeout=per_attempt_timeout,
                    status_emit=self.status_update.emit,
                    flush_logs=api._flush_log_handlers,
                    run_transcription=api._run_transcription_in_subprocess,
                    run_openai_fallback=api._run_openai_whisper_fallback,
                )
                serialized_segments = fallback_result["segments"]
                self.model_size = fallback_result["model_size"]
                self.device = fallback_result["device"]
                self.compute_type = fallback_result["compute_type"]
                self.effective_backend = fallback_result["effective_backend"]
                self.force_cpu = self.device == "cpu"

                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
                logging.info("Whisper checkpoint W2: subprocess transcription completed.")
                api._flush_log_handlers()

            self.status_update.emit("Transcribing...")
            for segment in whisper_segments:
                if self.isInterruptionRequested():
                    self.status_update.emit("Cancelled.")
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
                api._get_pyannote_pipeline_class()
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
                        return
                    pipeline = pipeline_cls.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=self.hf_token)
                    if pipeline:
                        should_move_to_gpu, gpu_reason = api._should_use_gpu_for_diarization(
                            force_cpu=self.force_cpu,
                        )
                        if should_move_to_gpu:
                            pipeline = pipeline.to(torch.device("cuda"))
                            logging.info("Pyannote pipeline moved to GPU.")
                        else:
                            logging.info("Pyannote pipeline kept on CPU. Reason: %s", gpu_reason)
                        diarization = pipeline(self.audio_path)
                        logging.info("Diarization completed successfully.")
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

        except Exception as e:
            logging.error(f"Transcription failed: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            if "pipeline" in locals():
                del pipeline
            if "diarization" in locals():
                del diarization

            gc.collect()
            if torch.cuda.is_available():
                try:
                    torch.cuda.synchronize()
                except Exception:
                    pass
                torch.cuda.empty_cache()
