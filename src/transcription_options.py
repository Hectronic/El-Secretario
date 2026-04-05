"""Shared transcription option helpers."""

from __future__ import annotations

from typing import Iterable


WHISPER_TRANSCRIPTION_MODELS = (
    "tiny",
    "base",
    "small",
    "medium",
    "large-v3",
)
SHERPA_ONNX_OPTION = "sherpa-onnx"
TRANSCRIPTION_MODEL_OPTIONS = WHISPER_TRANSCRIPTION_MODELS + (SHERPA_ONNX_OPTION,)

DEFAULT_TRANSCRIPTION_MODEL = "base"
DEFAULT_WELCOME_TRANSCRIPTION_MODEL = "large-v3"

SHERPA_MODEL_TYPE_OPTIONS = (
    "auto",
    "transducer",
    "paraformer",
    "nemo-ctc",
    "wenet-ctc",
    "tdnn-ctc",
    "whisper",
)


def get_transcription_model_options() -> list[str]:
    return list(TRANSCRIPTION_MODEL_OPTIONS)


def get_sherpa_model_type_options() -> list[str]:
    return list(SHERPA_MODEL_TYPE_OPTIONS)


def normalize_transcription_model(
    model_name: str | None,
    *,
    default: str = DEFAULT_TRANSCRIPTION_MODEL,
) -> str:
    candidate = str(model_name or "").strip()
    if candidate in TRANSCRIPTION_MODEL_OPTIONS:
        return candidate
    return default


def is_sherpa_onnx_model(model_name: str | None) -> bool:
    return normalize_transcription_model(model_name) == SHERPA_ONNX_OPTION


def get_saved_transcription_model(
    settings,
    *,
    default: str = DEFAULT_TRANSCRIPTION_MODEL,
) -> str:
    saved_model = settings.value("rec_config/model", None)
    if saved_model is None:
        saved_model = settings.value("whisper_model", default)
    return normalize_transcription_model(saved_model, default=default)


def normalize_sherpa_model_type(model_type: str | None) -> str:
    candidate = str(model_type or "").strip().lower()
    if candidate in SHERPA_MODEL_TYPE_OPTIONS:
        return candidate
    return "auto"


def format_transcription_model_tooltip(options: Iterable[str]) -> str:
    return "Available transcription options: " + ", ".join(options)
