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
    # Keep backend persistence identical for all transcription paths.
    settings.setValue("transcription_backend", effective_backend)
    settings.setValue("whisper_model", model_size)
    settings.setValue("rec_config/model", model_size)
    settings.setValue("force_cpu", device == "cpu" or force_cpu)
    if effective_backend == "faster-whisper":
        settings.setValue("compute_type", compute_type or "auto")
    settings.sync()


def get_subprocess_attempt_timeout_seconds(settings) -> int:
    default_timeout = 120 if platform.system() == "Windows" else 1800
    try:
        configured = settings.value(
            "transcription_attempt_timeout_seconds",
            default_timeout,
            type=int,
        )
        return max(30, int(configured))
    except Exception:
        return default_timeout

