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

import platform


def persist_working_transcription_settings(settings, *, effective_backend: str, model_size: str, device: str, force_cpu: bool, compute_type: str | None) -> None:
    """Persist the last effective runtime without rewriting user preferences.

    The UI preference keys are saved only by settings/configuration widgets. A
    runtime fallback to CPU, a concrete auto-selected compute type, or an
    effective backend must not become the user's next configured preference.
    """
    settings.setValue("last_transcription_backend", effective_backend)
    settings.setValue("last_transcription_model", model_size)
    settings.setValue("last_transcription_device", device)
    settings.setValue("last_transcription_force_cpu", bool(force_cpu))
    settings.setValue("last_transcription_compute_type", compute_type or "auto")
    settings.sync()


def get_subprocess_attempt_timeout_seconds(settings) -> int:
    default_timeout = 120 if platform.system() == "Windows" else 600
    try:
        configured = settings.value(
            "transcription_attempt_timeout_seconds",
            default_timeout,
            type=int,
        )
        return max(30, int(configured))
    except Exception:
        return default_timeout


def get_subprocess_attempt_timeout_for_duration_seconds(
    settings,
    *,
    total_duration_seconds: float | int | None,
) -> int:
    """Return per-attempt subprocess timeout scaled for long recordings.

    The configured timeout remains the baseline. For long recordings we add
    duration-based slack to avoid false timeouts while keeping an upper cap so
    truly stuck subprocesses still terminate.
    """
    baseline = get_subprocess_attempt_timeout_seconds(settings)
    try:
        duration = float(total_duration_seconds or 0.0)
    except Exception:
        duration = 0.0

    if duration <= 0.0:
        return baseline

    # Scale with audio length while keeping a strict upper bound.
    scaled = int(round((duration * 1.2) + 300.0))
    return max(30, min(5400, max(baseline, scaled)))


def get_transcription_chunking_config(settings) -> dict:
    """Return chunking config for long recordings."""
    enabled = bool(settings.value("transcription_chunking_enabled", True, type=bool))
    threshold = max(300, int(settings.value("transcription_chunk_threshold_seconds", 1800, type=int)))
    chunk_size = max(180, int(settings.value("transcription_chunk_size_seconds", 1200, type=int)))
    overlap = max(0, int(settings.value("transcription_chunk_overlap_seconds", 15, type=int)))

    # Ensure forward progress when iterating chunks.
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 10)

    return {
        "enabled": enabled,
        "threshold_seconds": threshold,
        "chunk_size_seconds": chunk_size,
        "overlap_seconds": overlap,
    }
