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
from importlib.metadata import PackageNotFoundError, version

import torch

_PYANNOTE_PIPELINE_CLS = None
_PYANNOTE_IMPORT_ATTEMPTED = False


def pkg_version(name: str) -> str:
    """Return a package version string that is safe to call from diagnostics."""
    try:
        return version(name)
    except PackageNotFoundError:
        return "<not-installed>"
    except Exception:
        return "<unknown>"


def get_pyannote_pipeline_class():
    """Import and cache pyannote's Pipeline class lazily.

    Diarization is optional and heavy to import. Caching both successful and
    failed attempts keeps repeated transcriptions from retrying a known-missing
    dependency.
    """
    global _PYANNOTE_PIPELINE_CLS, _PYANNOTE_IMPORT_ATTEMPTED
    if _PYANNOTE_IMPORT_ATTEMPTED:
        return _PYANNOTE_PIPELINE_CLS

    _PYANNOTE_IMPORT_ATTEMPTED = True
    try:
        from pyannote.audio import Pipeline as ImportedPipeline

        _PYANNOTE_PIPELINE_CLS = ImportedPipeline
    except Exception as e:
        logging.warning("pyannote.audio is not available for diarization: %s", e)
        _PYANNOTE_PIPELINE_CLS = None

    return _PYANNOTE_PIPELINE_CLS


def flush_log_handlers():
    """Force pending log output to disk before native subprocess boundaries."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        try:
            handler.flush()
        except Exception:
            pass


def log_transcription_runtime_context(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    force_cpu: bool,
    enable_diarization: bool,
    language: str,
):
    """Log device/backend context once per transcription attempt."""
    cuda_available = False
    cuda_device_count = 0
    cuda_device_name = "<none>"
    cuda_total_mem_gb = None
    cuda_error = None

    try:
        cuda_available = bool(torch.cuda.is_available())
        if cuda_available:
            cuda_device_count = int(torch.cuda.device_count())
            if cuda_device_count > 0:
                cuda_device_name = torch.cuda.get_device_name(0)
                cuda_total_mem_gb = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2
                )
    except Exception as e:
        cuda_error = str(e)

    logging.info(
        "Transcription runtime context: platform=%s release=%s python=%s torch=%s faster_whisper=%s ctranslate2=%s",
        platform.system(),
        platform.release(),
        platform.python_version(),
        torch.__version__,
        pkg_version("faster-whisper"),
        pkg_version("ctranslate2"),
    )
    logging.info(
        "Transcription execution params: audio=%s model=%s device=%s compute_type=%s language=%s diarization=%s force_cpu=%s",
        audio_path,
        model_size,
        device,
        compute_type,
        language,
        enable_diarization,
        force_cpu,
    )
    logging.info(
        "CUDA context: available=%s device_count=%s device0=%s vram_gb=%s cuda_error=%s",
        cuda_available,
        cuda_device_count,
        cuda_device_name,
        cuda_total_mem_gb,
        cuda_error,
    )
    logging.info(
        "Env flags: EL_SECRETARIO_WINDOWS_CUDA=%s CUDA_VISIBLE_DEVICES=%s",
        os.environ.get("EL_SECRETARIO_WINDOWS_CUDA", "<unset>"),
        os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"),
    )
    flush_log_handlers()


def should_use_gpu_for_diarization(
    *,
    force_cpu: bool,
) -> tuple[bool, str]:
    """Prefer CUDA for diarization unless CPU was explicitly requested.

    Free VRAM is used later to choose conservative pyannote batch sizes. A low
    reading alone does not silently force CPU; a real CUDA runtime failure is
    handled by the worker's CPU retry path.
    """
    if force_cpu:
        return (False, "force_cpu is enabled")

    try:
        cuda_available = bool(torch.cuda.is_available())
    except Exception as e:
        return (False, f"Could not check CUDA availability: {e}")
    if not cuda_available:
        return (False, "CUDA is not available")
    try:
        if torch.cuda.device_count() <= 0:
            return (False, "No CUDA device detected")
    except Exception as e:
        return (True, f"CUDA is available but device inspection failed; attempting GPU: {e}")
    try:
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        free_gb = free_bytes / (1024 ** 3)
        total_gb = total_bytes / (1024 ** 3)
        free_ratio = free_bytes / total_bytes if total_bytes else 0.0
        return (True, f"CUDA available; attempting diarization on GPU ({free_gb:.2f}/{total_gb:.2f} GB free, {free_ratio:.2%})")
    except Exception as e:
        # If CUDA is present but memory inspection failed, let the actual model
        # allocation decide. Batch-size selection remains conservative.
        logging.warning("Could not inspect CUDA memory before diarization: %s", e)
        return (True, "CUDA is available; VRAM could not be inspected, using conservative batches")


def diarization_batch_sizes(*, use_gpu: bool, free_vram_gb: float | None = None) -> tuple[int, int]:
    """Choose pyannote 3.1 inference batches without overcommitting GPU memory.

    pyannote 3.1 defaults both stages to batch size one. Larger batches improve
    GPU throughput; CPU stays conservative and GPU batch sizes scale with the
    memory left after loading the pipeline.
    """
    if not use_gpu or free_vram_gb is None:
        return (1, 1)
    free_vram_gb = max(0.0, float(free_vram_gb))
    if free_vram_gb >= 8.0:
        return (8, 8)
    if free_vram_gb >= 5.0:
        return (4, 4)
    if free_vram_gb >= 2.5:
        return (2, 2)
    return (1, 1)
