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

import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlopen

from src.transcription_options import is_sherpa_onnx_model, normalize_sherpa_model_type


def find_existing_file(directory: str, patterns: list[str]) -> str:
    root = Path(directory)
    for pattern in patterns:
        matches = sorted(root.glob(pattern))
        for match in matches:
            if match.is_file():
                return str(match)
    return ""


def default_sherpa_model_dir() -> str:
    return os.path.join(os.getcwd(), "models", "sherpa-onnx")


def default_sherpa_model_url() -> str:
    return (
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
        "sherpa-onnx-whisper-tiny.tar.bz2"
    )


def iter_sherpa_candidate_dirs(model_dir: str):
    root = Path(model_dir)
    if not root.exists():
        return
    yield str(root)
    for current_root, dirnames, filenames in os.walk(root):
        if any(f.endswith("tokens.txt") for f in filenames):
            yield current_root
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]


def resolve_sherpa_onnx_model_config(model_dir: str, model_type: str) -> dict:
    model_type = normalize_sherpa_model_type(model_type)
    tokens = find_existing_file(model_dir, ["tokens.txt", "*tokens.txt"])
    if not tokens:
        raise RuntimeError(
            "Sherpa-ONNX model is missing tokens.txt in the configured model directory."
        )

    transducer_encoder = find_existing_file(model_dir, ["encoder.onnx", "*encoder*.onnx"])
    transducer_decoder = find_existing_file(model_dir, ["decoder.onnx", "*decoder*.onnx"])
    transducer_joiner = find_existing_file(model_dir, ["joiner.onnx", "*joiner*.onnx"])
    whisper_encoder = find_existing_file(model_dir, ["*encoder*.onnx"])
    whisper_decoder = find_existing_file(model_dir, ["*decoder*.onnx"])
    generic_model = find_existing_file(model_dir, ["model.onnx", "*.onnx"])

    if model_type == "auto":
        if transducer_encoder and transducer_decoder and transducer_joiner:
            model_type = "transducer"
        elif whisper_encoder and whisper_decoder and (
            "whisper" in Path(whisper_encoder).name.lower() or "whisper" in str(model_dir).lower()
        ):
            model_type = "whisper"
        else:
            hint = f"{model_dir} {Path(generic_model).name}".lower()
            if "wenet" in hint:
                model_type = "wenet-ctc"
            elif "nemo" in hint or "citrinet" in hint or "conformer" in hint:
                model_type = "nemo-ctc"
            elif "tdnn" in hint:
                model_type = "tdnn-ctc"
            elif generic_model:
                model_type = "paraformer"
            elif whisper_encoder and whisper_decoder:
                model_type = "whisper"
            else:
                raise RuntimeError(
                    "Could not auto-detect the Sherpa-ONNX model layout. "
                    "Configure 'Sherpa-ONNX Model Type' explicitly in Settings."
                )

    if model_type == "transducer":
        if not (transducer_encoder and transducer_decoder and transducer_joiner):
            raise RuntimeError("Sherpa-ONNX transducer models require encoder, decoder and joiner ONNX files.")
        return {
            "type": model_type,
            "tokens": tokens,
            "encoder": transducer_encoder,
            "decoder": transducer_decoder,
            "joiner": transducer_joiner,
        }

    if model_type == "whisper":
        if not (whisper_encoder and whisper_decoder):
            raise RuntimeError("Sherpa-ONNX whisper models require encoder and decoder ONNX files.")
        return {
            "type": model_type,
            "tokens": tokens,
            "encoder": whisper_encoder,
            "decoder": whisper_decoder,
        }

    if not generic_model:
        raise RuntimeError("Sherpa-ONNX model.onnx was not found in the configured model directory.")

    return {
        "type": model_type,
        "tokens": tokens,
        "model": generic_model,
    }


def resolve_existing_sherpa_model_dir(model_dir: str, model_type: str) -> tuple[str, dict] | tuple[None, None]:
    seen = set()
    for candidate_dir in iter_sherpa_candidate_dirs(model_dir):
        if candidate_dir in seen:
            continue
        seen.add(candidate_dir)
        try:
            config = resolve_sherpa_onnx_model_config(candidate_dir, model_type)
            return candidate_dir, config
        except RuntimeError:
            continue
    return None, None


def safe_extract_tarball(archive_path: str, destination_dir: str) -> None:
    destination = os.path.abspath(destination_dir)
    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(destination, member.name))
            if not member_path.startswith(destination + os.sep) and member_path != destination:
                raise RuntimeError("Unsafe path detected while extracting Sherpa-ONNX archive.")
        tar.extractall(destination)


def download_sherpa_onnx_model(url: str, destination_dir: str, status_callback=None) -> None:
    os.makedirs(destination_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="sherpa_onnx_", suffix=".tar.bz2")
    os.close(fd)
    try:
        if status_callback:
            status_callback("Downloading sherpa-onnx model...")
        with urlopen(url, timeout=1800) as response, open(tmp_path, "wb") as out:
            shutil.copyfileobj(response, out)
        if status_callback:
            status_callback("Extracting sherpa-onnx model...")
        safe_extract_tarball(tmp_path, destination_dir)
    except Exception as e:
        raise RuntimeError(f"Could not download sherpa-onnx model from {url}: {e}") from e
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def ensure_sherpa_onnx_model_ready(settings, status_callback=None) -> tuple[str, dict]:
    model_dir = str(
        settings.value("sherpa_onnx_model_dir", default_sherpa_model_dir())
        or default_sherpa_model_dir()
    ).strip()
    if not model_dir:
        model_dir = default_sherpa_model_dir()

    model_type = normalize_sherpa_model_type(settings.value("sherpa_onnx_model_type", "auto"))
    resolved_dir, model_config = resolve_existing_sherpa_model_dir(model_dir, model_type)
    if resolved_dir and model_config:
        if resolved_dir != model_dir:
            settings.setValue("sherpa_onnx_model_dir", resolved_dir)
            settings.sync()
        return resolved_dir, model_config

    auto_download = settings.value("sherpa_onnx_auto_download", True, type=bool)
    if not auto_download:
        if not os.path.isdir(model_dir):
            raise RuntimeError(f"Sherpa-ONNX model directory does not exist: {model_dir}")
        raise RuntimeError(
            f"No compatible Sherpa-ONNX model was found in: {model_dir}\n\n"
            "Download a compatible offline model or enable automatic download in Settings -> Audio."
        )

    model_url = str(
        settings.value("sherpa_onnx_model_url", default_sherpa_model_url())
        or default_sherpa_model_url()
    ).strip()
    download_sherpa_onnx_model(model_url, model_dir, status_callback=status_callback)
    resolved_dir, model_config = resolve_existing_sherpa_model_dir(model_dir, model_type)
    if not resolved_dir or not model_config:
        raise RuntimeError(
            f"Downloaded Sherpa-ONNX files from {model_url}, but no compatible model layout was found in {model_dir}."
        )
    settings.setValue("sherpa_onnx_model_dir", resolved_dir)
    settings.sync()
    return resolved_dir, model_config


def get_transcription_preflight_error(model_size: str, settings) -> str | None:
    if not is_sherpa_onnx_model(model_size):
        return None

    auto_download = settings.value("sherpa_onnx_auto_download", True, type=bool)
    model_dir = str(
        settings.value("sherpa_onnx_model_dir", default_sherpa_model_dir())
        or default_sherpa_model_dir()
    ).strip()
    if not model_dir:
        if auto_download:
            return None
        return (
            "Sherpa-ONNX model directory is empty. "
            "Set it in Settings -> Audio before using sherpa-onnx."
        )
    if not os.path.isdir(model_dir):
        if auto_download:
            return None
        return (
            f"Sherpa-ONNX model directory does not exist: {model_dir}\n\n"
            "Download a compatible offline model and set its directory in Settings -> Audio."
        )
    resolved_dir, _ = resolve_existing_sherpa_model_dir(
        model_dir,
        settings.value("sherpa_onnx_model_type", "auto"),
    )
    if resolved_dir:
        return None
    if auto_download:
        return None
    if not os.path.isfile(os.path.join(model_dir, "tokens.txt")):
        return (
            f"Sherpa-ONNX model directory is missing tokens.txt: {model_dir}\n\n"
            "Make sure the selected directory contains a valid sherpa-onnx model."
        )
    return (
        f"No compatible Sherpa-ONNX model was found in: {model_dir}\n\n"
        "Select a valid model directory or enable automatic download in Settings -> Audio."
    )
