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

from __future__ import annotations

import multiprocessing as mp
import time

from PyQt6.QtCore import QThread

from src.stt_providers.dispatcher import subprocess_transcribe_entry


def run_backend_subprocess(*, backend: str, payload: dict, timeout_seconds: int = 1800):
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()
    payload = {**payload, "backend": backend}
    proc = ctx.Process(target=subprocess_transcribe_entry, args=(payload, result_queue), daemon=False)
    try:
        proc.start()
        start_time = time.monotonic()

        while proc.is_alive():
            current_thread = QThread.currentThread()
            if current_thread is not None and hasattr(current_thread, "isInterruptionRequested"):
                if current_thread.isInterruptionRequested():
                    proc.terminate()
                    proc.join(timeout=5)
                    raise RuntimeError("Transcription cancelled.")

            if start_time is not None and (time.monotonic() - start_time) >= timeout_seconds:
                proc.terminate()
                proc.join(timeout=5)
                raise RuntimeError("Transcription subprocess timed out.")

            proc.join(timeout=1)

        if proc.exitcode != 0:
            raise RuntimeError(
                f"Transcription subprocess crashed with exit code {proc.exitcode} "
                f"(possible native crash in transcription backend)."
            )

        if result_queue.empty():
            raise RuntimeError("Transcription subprocess finished without returning a result.")

        result = result_queue.get()
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "Unknown subprocess transcription error.")

        return result["segments"]
    finally:
        try:
            result_queue.close()
        except Exception:
            pass
        try:
            result_queue.join_thread()
        except Exception:
            pass
        try:
            proc.close()
        except Exception:
            pass


def run_transcription_in_subprocess(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    language: str,
    timeout_seconds: int = 1800,
):
    return run_backend_subprocess(
        backend="faster-whisper",
        payload={
            "audio_path": audio_path,
            "model_size": model_size,
            "device": device,
            "compute_type": compute_type,
            "language": language,
            "beam_size": 5,
        },
        timeout_seconds=timeout_seconds,
    )


def run_openai_whisper_fallback(*, audio_path: str, model_size: str, language: str):
    return run_backend_subprocess(
        backend="openai-whisper",
        payload={
            "audio_path": audio_path,
            "model_size": model_size,
            "language": language,
        },
    )


def run_sherpa_onnx_transcription(*, audio_path: str, language: str, model_dir: str, model_config: dict):
    return run_backend_subprocess(
        backend="sherpa-onnx",
        payload={
            "audio_path": audio_path,
            "language": language,
            "model_dir": model_dir,
            "model_config": model_config,
        },
    )
