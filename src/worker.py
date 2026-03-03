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

from PyQt6.QtCore import QThread, pyqtSignal
from faster_whisper import WhisperModel
import os
import platform
import torch
import gc
import logging
import multiprocessing as mp
from importlib.metadata import PackageNotFoundError, version
from types import SimpleNamespace

# Common resilience flag for Windows to avoid native crashes when multiple 
# libraries (torch, onnx, ctranslate2) bring conflicting OpenMP DLLs.
if platform.system() == "Windows":
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False


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


def _subprocess_transcribe_entry(payload: dict, result_queue):
    """Run faster-whisper in an isolated process to contain native crashes."""
    # Environment tuning for Windows stability.
    if platform.system() == "Windows":
        os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
        # Avoid potential crashes in native libs by limiting thread count if not on GPU.
        if payload["device"] == "cpu":
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["MKL_NUM_THREADS"] = "1"
            # OMP_WAIT_POLICY=PASSIVE can help with some native library instability on Windows.
            os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
            # Force more stable compute type for Windows CPU if it's default
            if payload["compute_type"] == "float32":
                payload["compute_type"] = "int8_float32"

    try:
        # Determine CPU threads for Windows CPU
        cpu_threads = 1 if (platform.system() == "Windows" and payload["device"] == "cpu") else 4
        
        logging.info(
            "Subprocess transcription starting: model=%s device=%s compute_type=%s cpu_threads=%s",
            payload["model_size"], payload["device"], payload["compute_type"], cpu_threads
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
        serialized_segments = [
            {"start": float(s.start), "end": float(s.end), "text": str(s.text)}
            for s in segments
        ]
        result_queue.put({"ok": True, "segments": serialized_segments})
    except Exception as e:
        result_queue.put({"ok": False, "error": str(e)})


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
    proc = ctx.Process(target=_subprocess_transcribe_entry, args=(payload, result_queue), daemon=True)
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


class TranscriberThread(QThread):
    finished = pyqtSignal(dict) # Changed to emit dict with text and stats
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_path, model_size="base", device=None, compute_type=None, language=None, hf_token=None, enable_diarization=False, total_duration=0, force_cpu=False):
        super().__init__()
        self.audio_path = audio_path
        self.model_size = model_size
        self.force_cpu = force_cpu
        
        # Auto-detect optimal device if not explicitly provided
        if device is None or compute_type is None:
            auto_device, auto_compute = get_optimal_device(force_cpu, model_size)
            self.device = device if device else auto_device
            self.compute_type = compute_type if compute_type else auto_compute
        else:
            self.device = device
            self.compute_type = compute_type

        # Protect Windows from unstable backend combinations that may crash the process.
        if platform.system() == "Windows":
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

    def run(self):
        try:
            import time
            start_time = time.time()
            
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
            use_subprocess_isolation = platform.system() == "Windows"
            if use_subprocess_isolation:
                self.status_update.emit("Loading model...")
                logging.info(
                    "Whisper checkpoint W1: subprocess isolation enabled (model=%s device=%s compute_type=%s)",
                    self.model_size,
                    self.device,
                    self.compute_type,
                )
                _flush_log_handlers()
                try:
                    serialized_segments = _run_transcription_in_subprocess(
                        audio_path=self.audio_path,
                        model_size=self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                        language=self.language,
                    )
                except RuntimeError as e:
                    if self.device == "cuda":
                        logging.warning("Whisper subprocess failed on CUDA. Falling back to CPU. Error: %s", e)
                        self.status_update.emit("Whisper failed on GPU. Falling back to CPU...")
                        self.device = "cpu"
                        self.compute_type = "float32" if platform.system() == "Windows" else "int8"
                        self.force_cpu = True
                        _flush_log_handlers()
                        serialized_segments = _run_transcription_in_subprocess(
                            audio_path=self.audio_path,
                            model_size=self.model_size,
                            device=self.device,
                            compute_type=self.compute_type,
                            language=self.language,
                        )
                    else:
                        raise
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

            # Run Diarization if token is present, library available, AND enabled
            diarization = None
            if self.enable_diarization and self.hf_token and PYANNOTE_AVAILABLE:
                self.status_update.emit("Diarizing (this may take a while)...")
                logging.info("Starting diarization...")
                # Bump progress to 80% to show we are moving to next phase
                self.progress.emit(80)
                try:
                    if self.isInterruptionRequested():
                        self.status_update.emit("Cancelled.")
                        return
                    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=self.hf_token)
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
                "transcription_time": transcription_time,
                "audio_duration": self.total_duration,
                "audio_size_bytes": os.path.getsize(self.audio_path),
                "is_diarized": self.enable_diarization
            }

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
