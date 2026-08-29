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


def create_sherpa_onnx_recognizer(*, sherpa_onnx_module, model_config: dict, language: str):
    common_kwargs = {
        "tokens": model_config["tokens"],
        "num_threads": 2,
        "sample_rate": 16000,
        "feature_dim": 80,
        "decoding_method": "greedy_search",
        "debug": False,
    }
    model_type = model_config["type"]

    if model_type == "transducer":
        return sherpa_onnx_module.OfflineRecognizer.from_transducer(
            encoder=model_config["encoder"],
            decoder=model_config["decoder"],
            joiner=model_config["joiner"],
            **common_kwargs,
        )
    if model_type == "paraformer":
        return sherpa_onnx_module.OfflineRecognizer.from_paraformer(
            paraformer=model_config["model"],
            **common_kwargs,
        )
    if model_type == "nemo-ctc":
        return sherpa_onnx_module.OfflineRecognizer.from_nemo_ctc(
            model=model_config["model"],
            **common_kwargs,
        )
    if model_type == "wenet-ctc":
        return sherpa_onnx_module.OfflineRecognizer.from_wenet_ctc(
            model=model_config["model"],
            **common_kwargs,
        )
    if model_type == "tdnn-ctc":
        return sherpa_onnx_module.OfflineRecognizer.from_tdnn_ctc(
            model=model_config["model"],
            **common_kwargs,
        )
    if model_type == "whisper":
        return sherpa_onnx_module.OfflineRecognizer.from_whisper(
            encoder=model_config["encoder"],
            decoder=model_config["decoder"],
            tokens=model_config["tokens"],
            num_threads=1,
            decoding_method="greedy_search",
            debug=False,
            language=language or "",
            task="transcribe",
            tail_paddings=-1,
        )

    raise RuntimeError(f"Unsupported Sherpa-ONNX model type: {model_type}")


def transcribe(payload: dict) -> list[dict]:
    try:
        import numpy as np
        import sherpa_onnx
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(
            "sherpa-onnx support requires the 'sherpa-onnx' package to be installed."
        ) from e

    logging.info(
        "Subprocess transcription starting: backend=sherpa-onnx model_type=%s",
        payload["model_config"].get("type"),
    )
    recognizer = create_sherpa_onnx_recognizer(
        sherpa_onnx_module=sherpa_onnx,
        model_config=payload["model_config"],
        language=payload.get("language"),
    )

    audio, sample_rate = sf.read(payload["audio_path"], always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1).astype(np.float32)

    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, audio)
    recognizer.decode_streams([stream])
    result = getattr(stream, "result", None)
    text = str(getattr(result, "text", "") or "").strip()

    if not text:
        return []

    duration = len(audio) / float(sample_rate) if sample_rate else 0.0
    return [{"start": 0.0, "end": float(duration), "text": text}]
