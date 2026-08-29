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

import logging
import os
import platform

from .common import serialize_segments


def transcribe(payload: dict) -> list[dict]:
    from faster_whisper import WhisperModel

    if platform.system() == "Windows":
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        if payload["device"] == "cpu":
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
            if payload["compute_type"] == "float32":
                payload["compute_type"] = "int8_float32"

    cpu_threads = 1 if (platform.system() == "Windows" and payload["device"] == "cpu") else 4
    logging.info(
        "Subprocess transcription starting: backend=faster-whisper model=%s device=%s compute_type=%s cpu_threads=%s",
        payload["model_size"],
        payload["device"],
        payload["compute_type"],
        cpu_threads,
    )
    model = WhisperModel(
        payload["model_size"],
        device=payload["device"],
        compute_type=payload["compute_type"],
        cpu_threads=cpu_threads,
    )
    segments, _info = model.transcribe(
        payload["audio_path"],
        beam_size=payload.get("beam_size", 5),
        language=payload.get("language"),
    )
    return serialize_segments(segments)
