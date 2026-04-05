from src.transcription_options import (
    SHERPA_ONNX_OPTION,
    get_sherpa_model_type_options,
    get_transcription_model_options,
    is_sherpa_onnx_model,
    normalize_sherpa_model_type,
    normalize_transcription_model,
)


def test_transcription_model_options_include_sherpa_onnx():
    options = get_transcription_model_options()
    assert SHERPA_ONNX_OPTION in options
    assert options[:5] == ["tiny", "base", "small", "medium", "large-v3"]


def test_normalize_transcription_model_falls_back_to_base():
    assert normalize_transcription_model("invalid-option") == "base"
    assert normalize_transcription_model(SHERPA_ONNX_OPTION) == SHERPA_ONNX_OPTION
    assert is_sherpa_onnx_model(SHERPA_ONNX_OPTION) is True


def test_sherpa_model_type_options_and_normalization():
    assert "auto" in get_sherpa_model_type_options()
    assert "whisper" in get_sherpa_model_type_options()
    assert normalize_sherpa_model_type("WENET-CTC") == "wenet-ctc"
    assert normalize_sherpa_model_type("unknown") == "auto"
