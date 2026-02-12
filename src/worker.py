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
import torch
import gc
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
    if not force_cpu and torch.cuda.is_available():
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
    return ("cpu", "int8")


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
            
        self.language = language
        self.hf_token = hf_token
        self.enable_diarization = enable_diarization
        self.total_duration = total_duration

    def run(self):
        try:
            import time
            import logging
            start_time = time.time()
            
            logging.info(f"Starting transcription for {self.audio_path} (Model: {self.model_size}, Diarization: {self.enable_diarization})")

            # Load Whisper model
            self.status_update.emit("Loading model...")
            try:
                model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            except RuntimeError as e:
                if "out of memory" in str(e) and self.device == "cuda":
                    logging.warning("CUDA Out of Memory during model load. Fallback to CPU.")
                    self.status_update.emit("CUDA OOM detected. Falling back to CPU...")
                    self.device = "cpu"
                    self.compute_type = "int8"
                    self.force_cpu = True
                    model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                else:
                    raise e
            
            self.status_update.emit("Transcribing...")
            segments, info = model.transcribe(self.audio_path, beam_size=5, language=self.language)
            
            whisper_segments = []
            for segment in segments:
                whisper_segments.append(segment)
                if self.total_duration > 0:
                    prog = int((segment.end / self.total_duration) * 100)
                    # If diarization is enabled, cap transcription progress at 80%
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
