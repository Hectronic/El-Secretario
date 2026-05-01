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

"""Compatibility facade for background worker classes and helpers.

The implementation lives in ``src.worker_components`` and ``src.stt_providers``.
This module keeps the historical import paths stable for UI code and older tests
while routing all real work to the smaller, focused modules.
"""

from PyQt6.QtCore import QSettings
import os
import platform
import logging
import torch
from src.worker_components import sherpa as worker_sherpa
from src.worker_components import engine as worker_engine
from src.worker_components import runtime as worker_runtime
from src.worker_components.threads import SearchThread, ChatThread
from src.worker_components import subprocess_runner

# Common resilience flag for Windows to avoid native crashes when multiple 
# libraries (torch, onnx, ctranslate2) bring conflicting OpenMP DLLs.
if platform.system() == "Windows":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

def _find_existing_file(directory: str, patterns: list[str]) -> str:
    return worker_sherpa.find_existing_file(directory, patterns)


def _default_sherpa_model_dir() -> str:
    return worker_sherpa.default_sherpa_model_dir()


def _default_sherpa_model_url() -> str:
    return worker_sherpa.default_sherpa_model_url()


def _iter_sherpa_candidate_dirs(model_dir: str):
    yield from worker_sherpa.iter_sherpa_candidate_dirs(model_dir)


def _resolve_existing_sherpa_model_dir(model_dir: str, model_type: str) -> tuple[str, dict] | tuple[None, None]:
    return worker_sherpa.resolve_existing_sherpa_model_dir(model_dir, model_type)


def _safe_extract_tarball(archive_path: str, destination_dir: str) -> None:
    return worker_sherpa.safe_extract_tarball(archive_path, destination_dir)


def _download_sherpa_onnx_model(url: str, destination_dir: str, status_callback=None) -> None:
    return worker_sherpa.download_sherpa_onnx_model(
        url,
        destination_dir,
        status_callback=status_callback,
    )


def _ensure_sherpa_onnx_model_ready(settings, status_callback=None) -> tuple[str, dict]:
    return worker_sherpa.ensure_sherpa_onnx_model_ready(
        settings,
        status_callback=status_callback,
    )


def _resolve_sherpa_onnx_model_config(model_dir: str, model_type: str) -> dict:
    return worker_sherpa.resolve_sherpa_onnx_model_config(model_dir, model_type)


def _run_backend_subprocess(*, backend: str, payload: dict, timeout_seconds: int = 1800):
    return subprocess_runner.run_backend_subprocess(
        backend=backend,
        payload=payload,
        timeout_seconds=timeout_seconds,
    )


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
    model_dir, model_config = _ensure_sherpa_onnx_model_ready(settings, status_callback=status_callback)
    return subprocess_runner.run_sherpa_onnx_transcription(
        audio_path=audio_path,
        language=language,
        model_dir=model_dir,
        model_config=model_config,
    )


def _is_subprocess_native_crash(error: RuntimeError) -> bool:
    return worker_engine.is_subprocess_native_crash(error)


def _is_subprocess_timeout(error: RuntimeError) -> bool:
    return worker_engine.is_subprocess_timeout(error)


def _subprocess_fallback_profiles(device: str, compute_type: str, *, is_windows: bool):
    return worker_engine.subprocess_fallback_profiles(device, compute_type, is_windows=is_windows)


def _windows_model_fallback_order(model_size: str):
    return worker_engine.windows_model_fallback_order(model_size)


def get_transcription_preflight_error(model_size: str, settings) -> str | None:
    return worker_sherpa.get_transcription_preflight_error(model_size, settings)


def get_optimal_device(force_cpu: bool = False, model_size: str = "base"):
    """
    Determine optimal device and compute type for transcription.
    
    Uses int8 quantization on GPU for better memory efficiency (especially
    important for GPUs with limited VRAM like RTX 3060 with 6GB).
    
    Returns:
        tuple: (device, compute_type) - e.g., ("cuda", "int8") or ("cpu", "int8")
    """
    is_windows = platform.system() == "Windows"

    if not force_cpu and torch.cuda.is_available():
        # On Windows keep float16 default for CUDA.
        if is_windows:
            return ("cuda", "float16")

        # Get available GPU memory
        try:
            gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            # For large models on GPUs with <= 8GB, use int8 for memory efficiency
            # int8 is generally recommended for inference anyway (faster + less memory)
            if model_size in ("large-v3", "large", "medium") and gpu_mem_gb <= 8:
                return ("cuda", "int8")
            # For smaller models or larger GPUs, float16 is fine
            if gpu_mem_gb > 8:
                return ("cuda", "float16")
        except Exception:
            pass
        # Default: use int8 for safety on most consumer GPUs
        return ("cuda", "int8")
    # On Windows, prefer float32 on CPU to avoid rare int8 runtime crashes.
    if is_windows:
        return ("cpu", "float32")
    return ("cpu", "int8")


def _pkg_version(name: str) -> str:
    return worker_runtime.pkg_version(name)


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


from src.worker_components.transcriber_thread import TranscriberThread  # noqa: E402
