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
import google.generativeai as genai
try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False

class TranscriberThread(QThread):
    finished = pyqtSignal(dict) # Changed to emit dict with text and stats
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_path, model_size="base", device="cpu", compute_type="int8", language=None, hf_token=None, enable_diarization=False, total_duration=0):
        super().__init__()
        self.audio_path = audio_path
        self.model_size = model_size
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
            model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            
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
                        # Move to device if possible, but pyannote defaults to CPU if no GPU
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
            
            import gc
            gc.collect()

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
        super().__init__()
        self.api_key = api_key
        self.query = query
        self.context_text = context_text
        self.history = history or []
        self.model_name = model_name

    def run(self):
        try:
            if not self.api_key:
                raise ValueError("Gemini API Key is missing.")

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)

            # Construct prompt with context and history
            history_str = ""
            for msg in self.history:
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_str += f"{role}: {msg['content']}\n"

            prompt = f"""
            You are a helpful assistant that answers questions based on the user's notes and transcriptions.
            Use the provided context to answer the question. If the answer is not in the context, say you don't know based on the notes, but try to be as helpful as possible.
            
            Context:
            {self.context_text}
            
            Chat History:
            {history_str}
            
            User Question: {self.query}
            
            Assistant:
            """

            response = model.generate_content(prompt)
            self.finished.emit(response.text)

        except Exception as e:
            self.error.emit(str(e))
