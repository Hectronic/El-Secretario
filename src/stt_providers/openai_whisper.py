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

from .common import normalize_openai_whisper_model_name


def _prepare_audio_for_openai_whisper(audio_path: str):
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(audio_path, always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)

    if audio.ndim > 1:
        audio = np.mean(audio, axis=1).astype(np.float32)

    target_sr = 16000
    if int(sample_rate) != target_sr:
        if audio.size == 0:
            return audio
        duration_seconds = len(audio) / float(sample_rate)
        target_len = max(1, int(round(duration_seconds * target_sr)))
        src_x = np.linspace(0.0, duration_seconds, num=len(audio), endpoint=False)
        dst_x = np.linspace(0.0, duration_seconds, num=target_len, endpoint=False)
        audio = np.interp(dst_x, src_x, audio).astype(np.float32)

    return audio


def transcribe(payload: dict) -> list[dict]:
    import whisper

    fallback_model = normalize_openai_whisper_model_name(payload["model_size"])
    logging.info(
        "Subprocess transcription starting: backend=openai-whisper model=%s",
        fallback_model,
    )
    model = whisper.load_model(fallback_model)
    try:
        audio_data = _prepare_audio_for_openai_whisper(payload["audio_path"])
        result = model.transcribe(audio_data, language=payload.get("language"))
    except Exception as audio_prepare_error:
        logging.warning(
            "openai-whisper local audio loading failed (%s). Falling back to ffmpeg path mode.",
            audio_prepare_error,
        )
        try:
            result = model.transcribe(payload["audio_path"], language=payload.get("language"))
        except FileNotFoundError as ffmpeg_missing_error:
            raise RuntimeError(
                "FFmpeg is not installed or not available in PATH. "
                "Install FFmpeg system-wide (for example C:\\ffmpeg\\bin in PATH) "
                "and retry transcription."
            ) from ffmpeg_missing_error

    segments = result.get("segments") or []
    return [
        {
            "start": float(s.get("start", 0.0)),
            "end": float(s.get("end", 0.0)),
            "text": str(s.get("text", "")),
        }
        for s in segments
    ]
