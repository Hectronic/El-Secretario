from unittest.mock import Mock

import requests

from src.worker_components.diarization_diagnostics import check_diarization, runtime_warning, safe_detail


def response(status=200, text=""):
    obj = Mock(status_code=status, text=text)
    if status >= 400:
        obj.raise_for_status.side_effect = requests.HTTPError(response=obj)
    return obj


def test_diagnostic_checks_actual_model_dependencies_without_downloading():
    session = Mock()
    session.get.side_effect = [response(), response(text="pipeline:\n  params:\n    segmentation: pyannote/segmentation-3.0\n    embedding: pyannote/embedding\nparams:\n  segmentation:\n    min_duration_off: 0.0\n")]
    session.head.return_value = response()
    result = check_diarization("hf_test", session=session, pipeline_loader=lambda: object())
    assert result.state == "available"
    assert "inference" in result.message.lower()
    assert session.head.call_count == 2
    assert all(call.kwargs["timeout"] == 10 for call in session.head.call_args_list)


def test_diagnostic_distinguishes_missing_token_denied_and_network():
    assert check_diarization("", pipeline_loader=lambda: object()).state == "problem"
    session = Mock()
    session.get.return_value = response(403)
    result = check_diarization("hf_test", session=session, pipeline_loader=lambda: object())
    assert result.state == "problem"
    assert "denied" in result.message and "expired" not in result.message
    session.get.side_effect = requests.ConnectionError("offline")
    assert check_diarization("hf_test", session=session, pipeline_loader=lambda: object()).state == "indeterminate"


def test_diagnostic_redacts_secrets_and_handles_missing_dependency():
    assert "hf_secret" not in safe_detail(Exception("Authorization: Bearer hf_secret"), "hf_secret")
    assert check_diarization("hf_test", pipeline_loader=lambda: None).state == "problem"
    session = Mock()
    session.get.side_effect = RuntimeError("bad token hf_test")
    assert "hf_test" not in check_diarization("hf_test", session=session, pipeline_loader=lambda: object()).message


def test_cancelled_check_stops_before_requesting_model():
    import threading
    cancelled = threading.Event()
    session = Mock()
    def get_account(*args, **kwargs):
        cancelled.set()
        return response()
    session.get.side_effect = get_account
    result = check_diarization("hf_test", session=session, pipeline_loader=lambda: object(), cancelled=cancelled)
    assert "cancelled" in result.message.lower()
    assert session.get.call_count == 1
    session.head.assert_not_called()


def test_unexpected_runtime_error_is_useful_without_leaking_token():
    message = runtime_warning(RuntimeError("failed to load for hf_secret"), token="hf_secret")
    assert "failed to load" in message
    assert "hf_secret" not in message


def test_denied_segmentation_resource_identifies_model():
    session = Mock()
    session.get.side_effect = [response(), response(text="pipeline:\n  params:\n    segmentation: pyannote/segmentation-3.0\n    embedding: pyannote/embedding\n")]
    session.head.return_value = response(403)
    result = check_diarization("hf_test", session=session, pipeline_loader=lambda: object())
    assert result.state == "problem"
    assert "pyannote/segmentation-3.0" in result.message
    assert "expired" not in result.message
