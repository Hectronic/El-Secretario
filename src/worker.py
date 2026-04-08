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

from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from faster_whisper import WhisperModel
import os
import platform
import torch
import gc
import logging
import multiprocessing as mp
import shutil
import tarfile
import tempfile
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version
from types import SimpleNamespace
from urllib.request import urlopen
from src.whisper_subprocess import subprocess_transcribe_entry
from src.transcription_options import is_sherpa_onnx_model, normalize_sherpa_model_type

# Common resilience flag for Windows to avoid native crashes when multiple 
# libraries (torch, onnx, ctranslate2) bring conflicting OpenMP DLLs.
if platform.system() == "Windows":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

_PYANNOTE_PIPELINE_CLS = None
_PYANNOTE_IMPORT_ATTEMPTED = False


def _find_existing_file(directory: str, patterns: list[str]) -> str:
    root = Path(directory)
    for pattern in patterns:
        matches = sorted(root.glob(pattern))
        for match in matches:
            if match.is_file():
                return str(match)
    return ""


def _default_sherpa_model_dir() -> str:
    return os.path.join(os.getcwd(), "models", "sherpa-onnx")


def _default_sherpa_model_url() -> str:
    return (
        "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
        "sherpa-onnx-whisper-tiny.tar.bz2"
    )


def _iter_sherpa_candidate_dirs(model_dir: str):
    root = Path(model_dir)
    if not root.exists():
        return
    yield str(root)
    for current_root, dirnames, filenames in os.walk(root):
        if any(f.endswith("tokens.txt") for f in filenames):
            yield current_root
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]


def _resolve_existing_sherpa_model_dir(model_dir: str, model_type: str) -> tuple[str, dict] | tuple[None, None]:
    seen = set()
    for candidate_dir in _iter_sherpa_candidate_dirs(model_dir):
        if candidate_dir in seen:
            continue
        seen.add(candidate_dir)
        try:
            config = _resolve_sherpa_onnx_model_config(candidate_dir, model_type)
            return candidate_dir, config
        except RuntimeError:
            continue
    return None, None


def _safe_extract_tarball(archive_path: str, destination_dir: str) -> None:
    destination = os.path.abspath(destination_dir)
    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar.getmembers():
            member_path = os.path.abspath(os.path.join(destination, member.name))
            if not member_path.startswith(destination + os.sep) and member_path != destination:
                raise RuntimeError("Unsafe path detected while extracting Sherpa-ONNX archive.")
        tar.extractall(destination)


def _download_sherpa_onnx_model(url: str, destination_dir: str, status_callback=None) -> None:
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
        _safe_extract_tarball(tmp_path, destination_dir)
    except Exception as e:
        raise RuntimeError(f"Could not download sherpa-onnx model from {url}: {e}") from e
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _ensure_sherpa_onnx_model_ready(settings, status_callback=None) -> tuple[str, dict]:
    model_dir = str(
        settings.value("sherpa_onnx_model_dir", _default_sherpa_model_dir())
        or _default_sherpa_model_dir()
    ).strip()
    if not model_dir:
        model_dir = _default_sherpa_model_dir()

    model_type = normalize_sherpa_model_type(settings.value("sherpa_onnx_model_type", "auto"))
    resolved_dir, model_config = _resolve_existing_sherpa_model_dir(model_dir, model_type)
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
        settings.value("sherpa_onnx_model_url", _default_sherpa_model_url())
        or _default_sherpa_model_url()
    ).strip()
    _download_sherpa_onnx_model(model_url, model_dir, status_callback=status_callback)
    resolved_dir, model_config = _resolve_existing_sherpa_model_dir(model_dir, model_type)
    if not resolved_dir or not model_config:
        raise RuntimeError(
            f"Downloaded Sherpa-ONNX files from {model_url}, but no compatible model layout was found in {model_dir}."
        )
    settings.setValue("sherpa_onnx_model_dir", resolved_dir)
    settings.sync()
    return resolved_dir, model_config


def _resolve_sherpa_onnx_model_config(model_dir: str, model_type: str) -> dict:
    model_type = normalize_sherpa_model_type(model_type)
    tokens = _find_existing_file(model_dir, ["tokens.txt", "*tokens.txt"])
    if not tokens:
        raise RuntimeError(
            "Sherpa-ONNX model is missing tokens.txt in the configured model directory."
        )

    transducer_encoder = _find_existing_file(model_dir, ["encoder.onnx", "*encoder*.onnx"])
    transducer_decoder = _find_existing_file(model_dir, ["decoder.onnx", "*decoder*.onnx"])
    transducer_joiner = _find_existing_file(model_dir, ["joiner.onnx", "*joiner*.onnx"])
    whisper_encoder = _find_existing_file(model_dir, ["*encoder*.onnx"])
    whisper_decoder = _find_existing_file(model_dir, ["*decoder*.onnx"])
    generic_model = _find_existing_file(model_dir, ["model.onnx", "*.onnx"])

    if model_type == "auto":
        if transducer_encoder and transducer_decoder and transducer_joiner:
            model_type = "transducer"
        elif whisper_encoder and whisper_decoder and ("whisper" in Path(whisper_encoder).name.lower() or "whisper" in str(model_dir).lower()):
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


def _create_sherpa_onnx_recognizer(*, sherpa_onnx_module, model_config: dict, language: str):
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


def _run_sherpa_onnx_transcription(*, audio_path: str, language: str, settings, status_callback=None) -> list[dict]:
    try:
        import numpy as np
        import sherpa_onnx
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError(
            "sherpa-onnx support requires the 'sherpa-onnx' package to be installed."
        ) from e

    model_dir, model_config = _ensure_sherpa_onnx_model_ready(settings, status_callback=status_callback)
    recognizer = _create_sherpa_onnx_recognizer(
        sherpa_onnx_module=sherpa_onnx,
        model_config=model_config,
        language=language,
    )

    audio, sample_rate = sf.read(audio_path, always_2d=False)
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


def get_transcription_preflight_error(model_size: str, settings) -> str | None:
    if not is_sherpa_onnx_model(model_size):
        return None

    auto_download = settings.value("sherpa_onnx_auto_download", True, type=bool)
    model_dir = str(
        settings.value("sherpa_onnx_model_dir", _default_sherpa_model_dir())
        or _default_sherpa_model_dir()
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
    resolved_dir, _ = _resolve_existing_sherpa_model_dir(
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


def get_optimal_device(force_cpu: bool = False, model_size: str = "base"):
    """
    Determine optimal device and compute type for transcription.
    
    Uses int8 quantization on GPU for better memory efficiency (especially
    important for GPUs with limited VRAM like RTX 3060 with 6GB).
    
    Returns:
        tuple: (device, compute_type) - e.g., ("cuda", "int8") or ("cpu", "int8")
    """
    is_windows = platform.system() == "Windows"

    if not force_cpu and torch.cuda.is_available():
        # On Windows keep float16 default for CUDA.
        if is_windows:
            return ("cuda", "float16")

        # Get available GPU memory
        try:
            gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            # For large models on GPUs with <= 8GB, use int8 for memory efficiency
            # int8 is generally recommended for inference anyway (faster + less memory)
            if model_size in ("large-v3", "large", "medium") and gpu_mem_gb <= 8:
                return ("cuda", "int8")
            # For smaller models or larger GPUs, float16 is fine
            if gpu_mem_gb > 8:
                return ("cuda", "float16")
        except Exception:
            pass
        # Default: use int8 for safety on most consumer GPUs
        return ("cuda", "int8")
    # On Windows, prefer float32 on CPU to avoid rare int8 runtime crashes.
    if is_windows:
        return ("cpu", "float32")
    return ("cpu", "int8")


def _pkg_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "<not-installed>"
    except Exception:
        return "<unknown>"


def _get_pyannote_pipeline_class():
    """
    Lazy import pyannote only when diarization is explicitly requested.
    This reduces DLL/OpenMP conflicts on Windows for plain transcription.
    """
    global _PYANNOTE_PIPELINE_CLS, _PYANNOTE_IMPORT_ATTEMPTED
    if _PYANNOTE_IMPORT_ATTEMPTED:
        return _PYANNOTE_PIPELINE_CLS

    _PYANNOTE_IMPORT_ATTEMPTED = True
    try:
        from pyannote.audio import Pipeline as ImportedPipeline

        _PYANNOTE_PIPELINE_CLS = ImportedPipeline
    except Exception as e:
        logging.warning("pyannote.audio is not available for diarization: %s", e)
        _PYANNOTE_PIPELINE_CLS = None

    return _PYANNOTE_PIPELINE_CLS


def _flush_log_handlers():
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        try:
            handler.flush()
        except Exception:
            pass


def _log_transcription_runtime_context(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    force_cpu: bool,
    enable_diarization: bool,
    language: str,
):
    cuda_available = False
    cuda_device_count = 0
    cuda_device_name = "<none>"
    cuda_total_mem_gb = None
    cuda_error = None

    try:
        cuda_available = bool(torch.cuda.is_available())
        if cuda_available:
            cuda_device_count = int(torch.cuda.device_count())
            if cuda_device_count > 0:
                cuda_device_name = torch.cuda.get_device_name(0)
                cuda_total_mem_gb = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2
                )
    except Exception as e:
        cuda_error = str(e)

    logging.info(
        "Transcription runtime context: platform=%s release=%s python=%s torch=%s faster_whisper=%s ctranslate2=%s",
        platform.system(),
        platform.release(),
        platform.python_version(),
        torch.__version__,
        _pkg_version("faster-whisper"),
        _pkg_version("ctranslate2"),
    )
    logging.info(
        "Transcription execution params: audio=%s model=%s device=%s compute_type=%s language=%s diarization=%s force_cpu=%s",
        audio_path,
        model_size,
        device,
        compute_type,
        language,
        enable_diarization,
        force_cpu,
    )
    logging.info(
        "CUDA context: available=%s device_count=%s device0=%s vram_gb=%s cuda_error=%s",
        cuda_available,
        cuda_device_count,
        cuda_device_name,
        cuda_total_mem_gb,
        cuda_error,
    )
    logging.info(
        "Env flags: EL_SECRETARIO_WINDOWS_CUDA=%s CUDA_VISIBLE_DEVICES=%s",
        os.environ.get("EL_SECRETARIO_WINDOWS_CUDA", "<unset>"),
        os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"),
    )
    _flush_log_handlers()


def _run_transcription_in_subprocess(
    *,
    audio_path: str,
    model_size: str,
    device: str,
    compute_type: str,
    language: str,
    timeout_seconds: int = 1800,
):
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()
    payload = {
        "audio_path": audio_path,
        "model_size": model_size,
        "device": device,
        "compute_type": compute_type,
        "language": language,
        "beam_size": 5,
    }
    # Keep daemon disabled on Windows for better native library stability.
    proc = ctx.Process(target=subprocess_transcribe_entry, args=(payload, result_queue), daemon=False)
    proc.start()
    proc.join(timeout=timeout_seconds)

    if proc.is_alive():
        proc.terminate()
        proc.join(timeout=5)
        raise RuntimeError("Transcription subprocess timed out.")

    if proc.exitcode != 0:
        raise RuntimeError(
            f"Transcription subprocess crashed with exit code {proc.exitcode} "
            f"(possible native crash in faster-whisper/ctranslate2)."
        )

    if result_queue.empty():
        raise RuntimeError("Transcription subprocess finished without returning a result.")

    result = result_queue.get()
    if not result.get("ok"):
        raise RuntimeError(result.get("error") or "Unknown subprocess transcription error.")

    return result["segments"]


def _is_subprocess_native_crash(error: RuntimeError) -> bool:
    message = str(error).lower()
    return "subprocess crashed with exit code" in message


def _is_subprocess_timeout(error: RuntimeError) -> bool:
    return "subprocess timed out" in str(error).lower()


def _windows_subprocess_fallback_profiles(device: str, compute_type: str):
    """
    Return fallback profiles ordered from safer to most compatible for Windows.
    """
    candidates = []
    if device == "cuda":
        candidates.extend(
            [
                ("cpu", "int8_float32"),
                ("cpu", "float32"),
                ("cpu", "int8"),
            ]
        )
    else:
        candidates.extend(
            [
                ("cpu", "float32"),
                ("cpu", "int8_float32"),
                ("cpu", "int8"),
            ]
        )

    unique = []
    for cand in candidates:
        if cand == (device, compute_type):
            continue
        if cand not in unique:
            unique.append(cand)
    return unique


def _windows_model_fallback_order(model_size: str):
    candidates = [model_size]
    if model_size == "large-v3":
        candidates.extend(["medium", "base"])
    elif model_size == "large":
        candidates.extend(["medium", "base"])
    elif model_size == "medium":
        candidates.append("base")
    return candidates


def _normalize_openai_whisper_model_name(model_size: str) -> str:
    # Keep mapping conservative for compatibility with openai-whisper names.
    if model_size in ("large-v3", "large-v2"):
        return "large"
    return model_size


def _prepare_audio_for_openai_whisper(audio_path: str):
    """
    Load audio without ffmpeg when possible (especially for WAV files).
    Returns a float32 mono waveform at 16 kHz.
    """
    import numpy as np
    import soundfile as sf

    audio, sample_rate = sf.read(audio_path, always_2d=False)
    audio = np.asarray(audio, dtype=np.float32)

    # Convert multi-channel audio to mono.
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1).astype(np.float32)

    # Resample to 16kHz expected by Whisper.
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


def _run_openai_whisper_fallback(*, audio_path: str, model_size: str, language: str):
    """
    Compatibility fallback for Windows when faster-whisper crashes natively.
    Uses openai-whisper backend (torch-based) which does not depend on ctranslate2.
    """
    import whisper

    fallback_model = _normalize_openai_whisper_model_name(model_size)
    model = whisper.load_model(fallback_model)
    try:
        audio_data = _prepare_audio_for_openai_whisper(audio_path)
        result = model.transcribe(audio_data, language=language)
    except Exception as audio_prepare_error:
        logging.warning(
            "openai-whisper local audio loading failed (%s). Falling back to ffmpeg path mode.",
            audio_prepare_error,
        )
        try:
            result = model.transcribe(audio_path, language=language)
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


class TranscriberThread(QThread):
    finished = pyqtSignal(dict) # Changed to emit dict with text and stats
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_path, model_size="base", device=None, compute_type=None, language=None, hf_token=None, enable_diarization=False, total_duration=0, force_cpu=False, backend_preference="auto"):
        super().__init__()
        from src.transcription_options import get_whisper_model_name
        self.audio_path = audio_path
        self.ui_model_name = model_size # Store original UI name
        self.model_size = get_whisper_model_name(model_size) # Use internal name
        self.force_cpu = force_cpu
        self.backend_preference = backend_preference or "auto"
        self.effective_backend = "faster-whisper"
        self.is_sherpa_onnx = is_sherpa_onnx_model(model_size)
        
        # Auto-detect optimal device if not explicitly provided
        if self.is_sherpa_onnx:
            self.device = "cpu"
            self.compute_type = "onnxruntime"
        elif device is None or compute_type is None:
            auto_device, auto_compute = get_optimal_device(force_cpu, model_size)
            self.device = device if device else auto_device
            self.compute_type = compute_type if compute_type else auto_compute
        else:
            self.device = device
            self.compute_type = compute_type

        # Protect Windows from unstable backend combinations that may crash the process.
        if platform.system() == "Windows" and not self.is_sherpa_onnx:
            if self.device == "cpu":
                # int8_float32 is often more stable than pure float32/int8 on Windows CPU
                # for preventing C0000005 Access Violations in ctranslate2.
                self.compute_type = "int8_float32"
            elif self.device == "cuda" and self.compute_type == "int8":
                # On Windows, keep float16 default for CUDA to avoid rare crashes.
                self.compute_type = "float16"
            
        self.language = language
        self.hf_token = hf_token
        self.enable_diarization = enable_diarization
        self.total_duration = total_duration

    def _persist_working_transcription_settings(self):
        try:
            settings = QSettings("Hectronic", "Secretario")
            settings.setValue("transcription_backend", self.effective_backend)
            settings.setValue("whisper_model", self.model_size)
            settings.setValue("rec_config/model", self.model_size)
            settings.setValue("force_cpu", self.device == "cpu" or self.force_cpu)
            if self.effective_backend == "faster-whisper":
                settings.setValue("compute_type", self.compute_type or "auto")
            settings.sync()
        except Exception as e:
            logging.warning("Could not persist working transcription settings: %s", e)

    def _get_subprocess_attempt_timeout_seconds(self) -> int:
        """
        Per-attempt timeout. Keep it shorter on Windows to avoid long silent hangs.
        """
        default_timeout = 120 if platform.system() == "Windows" else 1800
        try:
            settings = QSettings("Hectronic", "Secretario")
            configured = settings.value(
                "transcription_attempt_timeout_seconds",
                default_timeout,
                type=int,
            )
            return max(30, int(configured))
        except Exception:
            return default_timeout

    def run(self):
        try:
            import time
            start_time = time.time()
            settings = QSettings("Hectronic", "Secretario")
            
            logging.info(f"Starting transcription for {self.audio_path} (Model: {self.model_size}, Diarization: {self.enable_diarization})")
            _log_transcription_runtime_context(
                audio_path=self.audio_path,
                model_size=self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                force_cpu=self.force_cpu,
                enable_diarization=self.enable_diarization,
                language=self.language,
            )

            # On Windows, run faster-whisper in an isolated subprocess to avoid
            # bringing down the whole app if native libraries crash.
            use_subprocess_isolation = (
                not self.is_sherpa_onnx
                and
                platform.system() == "Windows"
                and self.backend_preference != "openai-whisper"
            )
            if self.is_sherpa_onnx:
                self.status_update.emit("Loading sherpa-onnx model...")
                self.effective_backend = "sherpa-onnx"
                serialized_segments = _run_sherpa_onnx_transcription(
                    audio_path=self.audio_path,
                    language=self.language,
                    settings=settings,
                    status_callback=self.status_update.emit,
                )
                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
                self.status_update.emit("Transcribing...")
                if self.total_duration > 0:
                    self.progress.emit(80)
            elif self.backend_preference == "openai-whisper":
                self.status_update.emit("Loading model...")
                self.effective_backend = "openai-whisper"
                serialized_segments = _run_openai_whisper_fallback(
                    audio_path=self.audio_path,
                    model_size=self.model_size,
                    language=self.language,
                )
                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
            elif use_subprocess_isolation:
                self.status_update.emit("Loading model...")
                self.effective_backend = "faster-whisper"
                logging.info(
                    "Whisper checkpoint W1: subprocess isolation enabled (model=%s device=%s compute_type=%s)",
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                _flush_log_handlers()
                is_windows = platform.system() == "Windows"
                base_device = self.device
                base_compute_type = self.compute_type
                attempt_models = (
                    _windows_model_fallback_order(self.model_size)
                    if is_windows
                    else [self.model_size]
                )
                serialized_segments = None
                last_error = None
                total_models = len(attempt_models)
                per_attempt_timeout = self._get_subprocess_attempt_timeout_seconds()
                for model_idx, attempt_model_size in enumerate(attempt_models):
                    self.model_size = attempt_model_size
                    attempt_profiles = [(base_device, base_compute_type)]
                    if is_windows:
                        attempt_profiles.extend(
                            _windows_subprocess_fallback_profiles(base_device, base_compute_type)
                        )
                    total_profiles = len(attempt_profiles)

                    for attempt_idx, (attempt_device, attempt_compute_type) in enumerate(attempt_profiles):
                        self.device = attempt_device
                        self.compute_type = attempt_compute_type
                        self.force_cpu = attempt_device == "cpu"
                        self.status_update.emit(
                            f"Attempt {attempt_idx + 1}/{total_profiles}, model {model_idx + 1}/{total_models}: "
                            f"backend=faster-whisper model={self.model_size} device={self.device} compute={self.compute_type}"
                        )
                        try:
                            serialized_segments = _run_transcription_in_subprocess(
                                audio_path=self.audio_path,
                                model_size=self.model_size,
                                device=self.device,
                                compute_type=self.compute_type,
                                language=self.language,
                                timeout_seconds=per_attempt_timeout,
                            )
                            break
                        except RuntimeError as e:
                            last_error = e
                            has_next_profile = attempt_idx < (len(attempt_profiles) - 1)
                            has_next_model = model_idx < (len(attempt_models) - 1)
                            native_crash = _is_subprocess_native_crash(e)
                            timeout_error = _is_subprocess_timeout(e)
                            should_retry_profile = has_next_profile and (
                                self.device == "cuda" or (is_windows and (native_crash or timeout_error))
                            )
                            if should_retry_profile:
                                logging.warning(
                                    "Whisper subprocess failed on profile model=%s device=%s compute_type=%s. Retrying with safer profile. Error: %s",
                                    self.model_size,
                                    self.device,
                                    self.compute_type,
                                    e,
                                )
                                self.status_update.emit(
                                    f"Retrying after crash: model={self.model_size}, device={self.device}, compute={self.compute_type}"
                                )
                                _flush_log_handlers()
                                continue

                            if has_next_model and is_windows and (native_crash or timeout_error):
                                next_model = attempt_models[model_idx + 1]
                                logging.warning(
                                    "Whisper kept failing on model=%s. Retrying with smaller model=%s.",
                                    self.model_size,
                                    next_model,
                                )
                                self.status_update.emit(
                                    f"Switching model after repeated crashes: {self.model_size} -> {next_model}"
                                )
                                _flush_log_handlers()
                                break

                            if is_windows and (native_crash or timeout_error):
                                # Exhausted profiles/models. Defer failure to compatibility fallback.
                                break

                            raise

                    if serialized_segments is not None:
                        break

                if serialized_segments is None and last_error is not None:
                    if is_windows and _is_subprocess_native_crash(last_error):
                        logging.warning(
                            "All faster-whisper subprocess attempts crashed natively. "
                            "Trying compatibility fallback with openai-whisper."
                        )
                        self.status_update.emit(
                            "faster-whisper unstable. Trying openai-whisper compatibility fallback..."
                        )
                        _flush_log_handlers()
                        try:
                            serialized_segments = _run_openai_whisper_fallback(
                                audio_path=self.audio_path,
                                model_size=self.model_size,
                                language=self.language,
                            )
                            self.effective_backend = "openai-whisper"
                        except Exception as fallback_error:
                            logging.error(
                                "Compatibility fallback (openai-whisper) failed: %s",
                                fallback_error,
                                exc_info=True,
                            )
                            raise
                    else:
                        raise last_error

                whisper_segments = [SimpleNamespace(**s) for s in serialized_segments]
                logging.info("Whisper checkpoint W2: subprocess transcription completed.")
                _flush_log_handlers()
            else:
                # Load Whisper model
                self.status_update.emit("Loading model...")
                logging.info(
                    "Whisper checkpoint A: about to initialize model (model=%s device=%s compute_type=%s)",
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                _flush_log_handlers()
                try:
                    # Explicitly set cpu_threads=1 on Windows CPU to prevent native crashes.
                    cpu_threads = 1 if (platform.system() == "Windows" and self.device == "cpu") else 4
                    model = WhisperModel(
                        self.model_size, 
                        device=self.device, 
                        compute_type=self.compute_type,
                        cpu_threads=cpu_threads
                    )
                    logging.info("Whisper checkpoint B: model initialized successfully.")
                    _flush_log_handlers()
                except RuntimeError as e:
                    if "out of memory" in str(e) and self.device == "cuda":
                        logging.warning("CUDA Out of Memory during model load. Fallback to CPU.")
                        self.status_update.emit("CUDA OOM detected. Falling back to CPU...")
                        self.device = "cpu"
                        self.compute_type = "float32" if platform.system() == "Windows" else "int8"
                        self.force_cpu = True
                        logging.info(
                            "Whisper checkpoint C: retrying model init after OOM (device=%s compute_type=%s)",
                            self.device,
                            self.compute_type,
                        )
                        _flush_log_handlers()
                        model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                        logging.info("Whisper checkpoint D: model initialized after OOM fallback.")
                        _flush_log_handlers()
                    else:
                        raise e
                
                self.status_update.emit("Transcribing...")
                logging.info("Whisper checkpoint E: starting model.transcribe(...)")
                _flush_log_handlers()
                segments, info = model.transcribe(self.audio_path, beam_size=5, language=self.language)
                logging.info("Whisper checkpoint F: model.transcribe(...) returned successfully.")
                _flush_log_handlers()
                whisper_segments = []
                for segment in segments:
                    if self.isInterruptionRequested():
                        self.status_update.emit("Cancelled.")
                        return
                    whisper_segments.append(segment)
                    if self.total_duration > 0:
                        prog = int((segment.end / self.total_duration) * 100)
                        # If diarization is enabled, cap transcription progress at 80%
                        if self.enable_diarization:
                            prog = int(prog * 0.8)
                        self.progress.emit(min(prog, 100))
            
            if use_subprocess_isolation:
                self.status_update.emit("Transcribing...")
                for segment in whisper_segments:
                    if self.isInterruptionRequested():
                        self.status_update.emit("Cancelled.")
                        return
                    if self.total_duration > 0:
                        prog = int((segment.end / self.total_duration) * 100)
                        if self.enable_diarization:
                            prog = int(prog * 0.8)
                        self.progress.emit(min(prog, 100))

            transcription = ""

            # Run Diarization if token is present and enabled.
            diarization = None
            pipeline_cls = (
                _get_pyannote_pipeline_class()
                if (self.enable_diarization and self.hf_token)
                else None
            )
            if self.enable_diarization and self.hf_token and pipeline_cls:
                self.status_update.emit("Diarizing (this may take a while)...")
                logging.info("Starting diarization...")
                # Bump progress to 80% to show we are moving to next phase
                self.progress.emit(80)
                try:
                    if self.isInterruptionRequested():
                        self.status_update.emit("Cancelled.")
                        return
                    pipeline = pipeline_cls.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=self.hf_token)
                    if pipeline:
                        # Move pipeline to GPU if CUDA available and not forced to CPU
                        if torch.cuda.is_available() and not self.force_cpu:
                            pipeline = pipeline.to(torch.device("cuda"))
                            logging.info("Pyannote pipeline moved to GPU.")
                        diarization = pipeline(self.audio_path)
                        logging.info("Diarization completed successfully.")
                except Exception as e:
                    logging.error(f"Diarization failed: {e}", exc_info=True)
                    print(f"Diarization failed: {e}")
                    import traceback
                    traceback.print_exc()
            elif self.enable_diarization and self.hf_token and not pipeline_cls:
                logging.warning("Diarization requested but pyannote.audio is unavailable.")
            
            # Merge results
            self.status_update.emit("Merging results...")
            if self.enable_diarization:
                self.progress.emit(90)
                
            for segment in whisper_segments:
                if self.isInterruptionRequested():
                    self.status_update.emit("Cancelled.")
                    return
                speaker_label = ""
                if diarization:
                    # Find speaker who spoke the most during this segment
                    # Segment start/end
                    start = segment.start
                    end = segment.end
                    
                    # Get overlapping turns
                    # This is a simplified heuristic
                    speakers = []
                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        # Calculate overlap
                        overlap_start = max(start, turn.start)
                        overlap_end = min(end, turn.end)
                        overlap_duration = max(0, overlap_end - overlap_start)
                        if overlap_duration > 0:
                            speakers.append((speaker, overlap_duration))
                    
                    if speakers:
                        # Sort by duration desc
                        speakers.sort(key=lambda x: x[1], reverse=True)
                        best_speaker = speakers[0][0]
                        speaker_label = f"\n\n[{best_speaker}] "

                transcription += f"{speaker_label}{segment.text} "

            end_time = time.time()
            transcription_time = end_time - start_time
            
            result = {
                "text": transcription.strip(),
                "model_name": self.model_size,
                "backend": self.effective_backend,
                "device": self.device,
                "compute_type": self.compute_type,
                "transcription_time": transcription_time,
                "audio_duration": self.total_duration,
                "audio_size_bytes": os.path.getsize(self.audio_path),
                "is_diarized": self.enable_diarization
            }

            self._persist_working_transcription_settings()

            logging.info(f"Transcription finished in {transcription_time:.2f}s")
            self.progress.emit(100)
            self.status_update.emit("Finished.")
            self.finished.emit(result)

        except Exception as e:
            logging.error(f"Transcription failed: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            # Cleanup to free memory
            if 'model' in locals():
                del model
            if 'pipeline' in locals():
                del pipeline
            if 'diarization' in locals():
                del diarization
            
            gc.collect()
            if torch.cuda.is_available():
                try:
                    torch.cuda.synchronize()
                except Exception:
                    pass
                torch.cuda.empty_cache()

class SearchThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, rag_engine, query):
        super().__init__()
        self.rag = rag_engine
        self.query = query

    def run(self):
        try:
            results = self.rag.search(self.query)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class ChatThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, query, context_text, history=None, model_name="gemini-3-flash-preview"):
        """Initialize the Chat Thread.
        
        Note: api_key parameter is kept for backward compatibility but the actual
        provider configuration is read from QSettings.
        """
        super().__init__()
        self.query = query
        self.context_text = context_text
        self.history = history or []
        # api_key and model_name kept for backward compatibility
        self._legacy_api_key = api_key
        self._legacy_model_name = model_name

    def run(self):
        try:
            from PyQt6.QtCore import QSettings
            from src.ai_provider import get_ai_provider
            
            settings = QSettings("Hectronic", "Secretario")
            provider = get_ai_provider(settings)

            response = provider.chat(self.history, self.query, self.context_text)
            self.finished.emit(response)

        except Exception as e:
            self.error.emit(str(e))
