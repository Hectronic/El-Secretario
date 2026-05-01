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
import platform


def is_subprocess_native_crash(error: RuntimeError) -> bool:
    message = str(error).lower()
    return "subprocess crashed with exit code" in message


def is_subprocess_timeout(error: RuntimeError) -> bool:
    return "subprocess timed out" in str(error).lower()


def subprocess_fallback_profiles(device: str, compute_type: str, *, is_windows: bool):
    candidates = []
    if device == "cuda":
        candidates.extend(
            [
                ("cpu", "int8_float32"),
                ("cpu", "float32"),
                ("cpu", "int8"),
            ]
        )
    elif is_windows:
        candidates.extend(
            [
                ("cpu", "float32"),
                ("cpu", "int8_float32"),
                ("cpu", "int8"),
            ]
        )

    unique = []
    for cand in candidates:
        if cand == (device, compute_type):
            continue
        if cand not in unique:
            unique.append(cand)
    return unique


def windows_model_fallback_order(model_size: str):
    candidates = [model_size]
    if model_size == "large-v3":
        candidates.extend(["medium", "base"])
    elif model_size == "large":
        candidates.extend(["medium", "base"])
    elif model_size == "medium":
        candidates.append("base")
    return candidates


def run_faster_whisper_with_fallback(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    language: str,
    per_attempt_timeout: int,
    status_emit,
    flush_logs,
    run_transcription,
    run_openai_fallback,
):
    # Keep retry/fallback policy centralized so TranscriberThread stays smaller.
    is_windows = platform.system() == "Windows"
    base_device = device
    base_compute_type = compute_type
    attempt_models = windows_model_fallback_order(model_size) if is_windows else [model_size]

    serialized_segments = None
    last_error = None
    final_model_size = model_size
    final_device = device
    final_compute_type = compute_type
    effective_backend = "faster-whisper"
    total_models = len(attempt_models)

    for model_idx, attempt_model_size in enumerate(attempt_models):
        final_model_size = attempt_model_size
        attempt_profiles = [(base_device, base_compute_type)]
        if base_device == "cuda" or (is_windows and base_device == "cpu"):
            attempt_profiles.extend(
                subprocess_fallback_profiles(base_device, base_compute_type, is_windows=is_windows)
            )
        total_profiles = len(attempt_profiles)

        for attempt_idx, (attempt_device, attempt_compute_type) in enumerate(attempt_profiles):
            final_device = attempt_device
            final_compute_type = attempt_compute_type
            status_emit(
                f"Attempt {attempt_idx + 1}/{total_profiles}, model {model_idx + 1}/{total_models}: "
                f"backend=faster-whisper model={final_model_size} device={final_device} compute={final_compute_type}"
            )
            try:
                serialized_segments = run_transcription(
                    audio_path=audio_path,
                    model_size=final_model_size,
                    device=final_device,
                    compute_type=final_compute_type,
                    language=language,
                    timeout_seconds=per_attempt_timeout,
                )
                break
            except RuntimeError as e:
                last_error = e
                has_next_profile = attempt_idx < (len(attempt_profiles) - 1)
                has_next_model = model_idx < (len(attempt_models) - 1)
                native_crash = is_subprocess_native_crash(e)
                timeout_error = is_subprocess_timeout(e)
                should_retry_profile = has_next_profile and (
                    final_device == "cuda" or (is_windows and (native_crash or timeout_error))
                )
                if should_retry_profile:
                    logging.warning(
                        "Whisper subprocess failed on profile model=%s device=%s compute_type=%s. Retrying with safer profile. Error: %s",
                        final_model_size,
                        final_device,
                        final_compute_type,
                        e,
                    )
                    status_emit(
                        f"Retrying after crash: model={final_model_size}, device={final_device}, compute={final_compute_type}"
                    )
                    flush_logs()
                    continue

                if has_next_model and is_windows and (native_crash or timeout_error):
                    next_model = attempt_models[model_idx + 1]
                    logging.warning(
                        "Whisper kept failing on model=%s. Retrying with smaller model=%s.",
                        final_model_size,
                        next_model,
                    )
                    status_emit(f"Switching model after repeated crashes: {final_model_size} -> {next_model}")
                    flush_logs()
                    break

                if is_windows and (native_crash or timeout_error):
                    break

                raise

        if serialized_segments is not None:
            break

    if serialized_segments is None and last_error is not None:
        if is_windows and is_subprocess_native_crash(last_error):
            logging.warning(
                "All faster-whisper subprocess attempts crashed natively. "
                "Trying compatibility fallback with openai-whisper."
            )
            status_emit("faster-whisper unstable. Trying openai-whisper compatibility fallback...")
            flush_logs()
            serialized_segments = run_openai_fallback(
                audio_path=audio_path,
                model_size=final_model_size,
                language=language,
            )
            effective_backend = "openai-whisper"
        else:
            raise last_error

    return {
        "segments": serialized_segments,
        "model_size": final_model_size,
        "device": final_device,
        "compute_type": final_compute_type,
        "effective_backend": effective_backend,
    }
