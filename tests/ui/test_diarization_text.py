from src.ui.diarization_text import diarization_text


def test_diarization_text_supports_spanish_and_asturian():
    assert diarization_text("Check diarization", "es_ES") == "Comprobar diarización"
    assert diarization_text("Cancel check", "ast_ES") == "Cancelar comprobación"
    text = "Access to pyannote/segmentation-3.0 was denied (HTTP 403). Check the token and access conditions on Hugging Face."
    assert "Se denegó" in diarization_text(text, "es_ES")
    assert "pyannote/segmentation-3.0" in diarization_text(text, "es_ES")
    assert diarization_text(text, "en_US") == text
