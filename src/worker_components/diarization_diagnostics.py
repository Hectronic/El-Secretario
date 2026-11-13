"""Safe diagnostics shared by diarization and the settings interface."""
from dataclasses import dataclass
from datetime import datetime
import re

MODEL_ID = "pyannote/speaker-diarization-3.1"


@dataclass(frozen=True)
class DiarizationDiagnosis:
    state: str
    message: str
    checked_at: str = ""


def runtime_warning(error=None, *, missing_token=False, missing_dependency=False, token=""):
    if missing_token:
        return "Diarization was not performed: add a Hugging Face token in Settings > Transcription & speakers, then retry."
    if missing_dependency:
        return "Diarization was not performed: pyannote.audio is unavailable or incompatible. Check the installation, then retry."
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status in (401, 403):
        return "Diarization was not performed: authentication or model access was denied. Check your Hugging Face token and model access in Settings."
    try:
        import requests
        if isinstance(error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
            return "Diarization was not performed: Hugging Face could not be reached. Check the connection and try again."
    except ImportError:
        pass
    message = "Diarization was not performed: the model could not be loaded or run. Check Settings > Transcription & speakers, then retry."
    if error:
        message += " Detail: " + safe_detail(error, token)
    return message


def safe_detail(error, token=""):
    text = str(error)
    if token:
        text = text.replace(token, "[redacted]")
    text = re.sub(r"(?i)(authorization[:=]\s*(?:bearer\s+)?)[^\s,;]+", r"\1[redacted]", text)
    text = re.sub(r"hf_[A-Za-z0-9]+", "[redacted]", text)
    return text[:300]


class _CheckCancelled(Exception):
    pass


def check_diarization(token, *, session=None, pipeline_loader=None, cancelled=None):
    """Check local import, identity and required model files without downloading weights."""
    import requests
    import yaml
    from src.worker_components.runtime import get_pyannote_pipeline_class

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    token = str(token or "").strip()
    if not token:
        return DiarizationDiagnosis("problem", runtime_warning(missing_token=True), now)
    resource = "account"
    client = None

    def check_cancelled():
        if cancelled is not None and cancelled.is_set():
            raise _CheckCancelled()
    try:
        if (pipeline_loader or get_pyannote_pipeline_class)() is None:
            return DiarizationDiagnosis("problem", runtime_warning(missing_dependency=True), now)
        check_cancelled()
        client = session or requests.Session()
        headers = {"Authorization": f"Bearer {token}"}
        auth = client.get("https://huggingface.co/api/whoami-v2", headers=headers, timeout=10)
        auth.raise_for_status()
        check_cancelled()
        resource = MODEL_ID
        config = client.get(f"https://huggingface.co/{MODEL_ID}/resolve/main/config.yaml", headers=headers, timeout=10)
        config.raise_for_status()
        check_cancelled()
        data = yaml.safe_load(config.text)
        pipeline = data.get("pipeline", {}) if isinstance(data, dict) else {}
        params = pipeline.get("params", {}) if isinstance(pipeline, dict) else {}
        params = params if isinstance(params, dict) else {}
        resources = [params.get("segmentation"), params.get("embedding")]
        if not all(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value) for value in resources):
            return DiarizationDiagnosis("indeterminate", "Account and pipeline access verified; model dependencies could not be identified. Inference was not tested.", now)
        for resource in dict.fromkeys(resources):
            response = client.head(f"https://huggingface.co/{resource}/resolve/main/pytorch_model.bin", headers=headers, timeout=10, allow_redirects=True)
            response.raise_for_status()
            check_cancelled()
        return DiarizationDiagnosis("available", "Account and model resource access verified. Download, audio inference and GPU were not tested.", now)
    except _CheckCancelled:
        return DiarizationDiagnosis("indeterminate", "Check cancelled.", now)
    except requests.exceptions.HTTPError as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        if status in (401, 403):
            return DiarizationDiagnosis("problem", f"Access to {resource} was denied (HTTP {status}). Check the token and access conditions on Hugging Face.", now)
        return DiarizationDiagnosis("indeterminate", f"Hugging Face returned HTTP {status or 'error'}; retry later. Inference was not tested.", now)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        return DiarizationDiagnosis("indeterminate", "Could not contact Hugging Face. Check your connection and retry. Cached models may still work offline.", now)
    except Exception as error:
        return DiarizationDiagnosis("indeterminate", "Could not complete the check: " + safe_detail(error, token), now)
    finally:
        if client is not None and session is None:
            client.close()
