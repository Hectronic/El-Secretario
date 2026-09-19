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

import os
import subprocess
import tempfile
import time
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

class Recorder(QObject):
    amplitude_changed = pyqtSignal(float) # Signal to emit RMS amplitude (0.0 to 1.0)

    def __init__(
        self,
        sample_rate=16000,
        channels=1,
        *,
        amplitude_update_hz=20.0,
        monotonic_clock=None,
    ):
        super().__init__()
        self.fs = sample_rate
        self.channels = channels
        self.recording = []
        self.stream = None
        self.is_recording = False
        self.is_paused = False
        self.start_time = None
        self.device_index = None # Default device
        self.capture_machine_audio = False
        # Audio callbacks can arrive 50-100 times/second.  Cap only the
        # UI-facing level signal; every PCM block is still retained unchanged.
        self.amplitude_update_hz = amplitude_update_hz
        self._monotonic_clock = monotonic_clock or time.monotonic
        self._last_amplitude_emit_at = None

    def set_device(self, device_index):
        """Set the input device index."""
        self.device_index = device_index
        
    def set_capture_machine_audio(self, enabled):
        """If enabled, start() will try to find a monitor/loopback device."""
        self.capture_machine_audio = enabled

    def callback(self, indata, frames, time, status):
        """Callback to collect audio data."""
        if status:
            print(status)
        
        # Calculate RMS amplitude for VU meter. Emitting each callback queues
        # needless UI events while recording; a 20 Hz VU meter is responsive.
        rms = np.sqrt(np.mean(indata**2))
        now = self._monotonic_clock()
        interval = (
            1.0 / float(self.amplitude_update_hz)
            if self.amplitude_update_hz and self.amplitude_update_hz > 0
            else 0.0
        )
        if self._last_amplitude_emit_at is None or now - self._last_amplitude_emit_at >= interval:
            self.amplitude_changed.emit(float(rms))
            self._last_amplitude_emit_at = now

        if not self.is_paused:
            self.recording.append(indata.copy())

    def start(self):
        """Start recording in a non-blocking stream."""
        import logging
        if self.is_recording:
            return
        
        self.recording = []
        self.is_recording = True
        self.is_paused = False
        self._last_amplitude_emit_at = None
        self.start_time = datetime.now()
        
        # Determine target device
        target_device = self.device_index
        if self.capture_machine_audio:
            # Try to find a monitor/loopback device automatically
            try:
                devices = sd.query_devices()
                # Prioritize devices with monitor, loopback, or stereo mix in their name
                found = False
                
                # Step 1: Look for explicit monitor/loopback keywords
                monitor_keywords = ['monitor', 'loopback', 'stereo mix', 'what u hear', 'output.monitor', 'analog-stereo.monitor']
                for i, dev in enumerate(devices):
                    if dev['max_input_channels'] > 0:
                        name = dev['name'].lower()
                        if any(kw in name for kw in monitor_keywords):
                            target_device = i
                            logging.info(f"INTERNAL AUDIO: Found explicit monitor device: {dev['name']} (Index {i})")
                            found = True
                            break
                
                # Step 2: Linux/Pipewire Fallback: If no monitor found, look for pipewire/default with many channels
                if not found:
                    for i, dev in enumerate(devices):
                        if dev['max_input_channels'] >= 2:
                            name = dev['name'].lower()
                            if name in ['pipewire', 'default', 'pulse']:
                                target_device = i
                                logging.info(f"INTERNAL AUDIO: Using Linux fallback device: {dev['name']} (Index {i})")
                                # For internal capture on these generic devices, stereo is almost always required
                                self.channels = 2 
                                found = True
                                break
                
                if not found:
                    logging.warning("INTERNAL AUDIO: No suitable internal capture device found. Falling back to default input.")
            except Exception as e:
                logging.error(f"INTERNAL AUDIO: Error during device discovery: {e}")

        # Try different sample rates and channel counts if the device doesn't support the requested one
        sample_rates_to_try = [self.fs, 44100, 48000, 22050, 8000]
        # Common channel counts: many loopback devices require stereo (2)
        channels_to_try = [self.channels]
        if self.channels == 1:
            channels_to_try.append(2)
        elif self.channels == 2:
            channels_to_try.append(1)

        logging.info(f"STARTING RECORDING: Device Index={target_device}, Initial Rate={self.fs}, Initial Channels={self.channels}")
        for rate in sample_rates_to_try:
            for ch in channels_to_try:
                try:
                    self.stream = sd.InputStream(
                        samplerate=rate,
                        channels=ch,
                        callback=self.callback,
                        device=target_device
                    )
                    self.stream.start()
                    self.fs = rate
                    self.channels = ch # Update to the channels that worked
                    logging.info(f"Recording started at {rate} Hz, {ch} channels")
                    return
                except Exception as e:
                    # Only log warning on the last channel attempt for this rate
                    if ch == channels_to_try[-1]:
                        logging.warning(f"Failed to start recording at {rate} Hz: {e}")
                    continue
        
        # All rates and channel combinations failed
        self.is_recording = False
        logging.error("Failed to start recording on all attempted sample rates and channel counts", exc_info=True)
        raise Exception("Could not initialize audio stream. Please check your audio settings.")

    def pause(self):
        """Pause the recording."""
        self.is_paused = True

    def resume(self):
        """Resume the recording."""
        self.is_paused = False

    def stop(self):
        """Stop recording and save to file. Returns the absolute path of the file."""
        import logging
        if not self.is_recording:
            return None

        try:
            # Handle case where stream failed to initialize
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            
            self.is_recording = False
            self.is_paused = False
            
            # Concatenate all recorded chunks
            if not self.recording:
                logging.warning("Recording stopped but no data was recorded.")
                return None
                
            full_recording = np.concatenate(self.recording, axis=0)
            
            # Ensure recordings directory exists
            recordings_dir = os.path.join(os.getcwd(), "recordings")
            os.makedirs(recordings_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rec_{timestamp}.wav"
            filepath = os.path.join(recordings_dir, filename)
            
            # Save to file
            sf.write(filepath, full_recording, self.fs)
            logging.info(f"Recording saved to {filepath}")
            return filepath
        finally:
            # Release audio buffer memory aggressively after stop (success or failure).
            self.recording.clear()

    @staticmethod
    def get_input_devices():
        """Return a list of input devices, including monitor/loopback devices."""
        import sounddevice as sd
        try:
            devices = sd.query_devices()
            input_devices = []
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    name = dev['name']
                    # Label monitor devices clearly
                    lname = name.lower()
                    if any(kw in lname for kw in ['monitor', 'loopback', 'stereo mix', 'what u hear', 'output.monitor']):
                        display_name = f"🖥️ {name}"
                    elif lname in ['pipewire', 'default'] and dev['max_input_channels'] >= 64:
                        display_name = f"🖥️ {name} (System Audio)"
                    else:
                        display_name = f"🎤 {name}"
                    input_devices.append((i, display_name))
            return input_devices
        except Exception:
            return []

    @staticmethod
    def get_duration(file_path):
        """Get the duration of an audio file in seconds."""
        import logging
        try:
            f = sf.SoundFile(file_path)
            return float(len(f) / f.samplerate)
        except Exception as e:
            logging.error(f"Error getting duration for {file_path}: {e}")
            return 0.0


def trim_audio_segment(source_path: str, start_seconds: float, end_seconds: float, output_path: str) -> float:
    """
    Trim an audio file and write the selected segment to ``output_path``.

    Returns the resulting duration in seconds.
    """
    import logging

    if start_seconds < 0:
        raise ValueError("start_seconds must be >= 0")
    if end_seconds <= start_seconds:
        raise ValueError("end_seconds must be greater than start_seconds")

    try:
        info = sf.info(source_path)
        total_duration = float(info.frames / info.samplerate)
        if start_seconds >= total_duration:
            raise ValueError("start_seconds is beyond the end of the file")

        clip_end = min(end_seconds, total_duration)
        start_frame = int(start_seconds * info.samplerate)
        end_frame = int(clip_end * info.samplerate)
        audio, samplerate = sf.read(source_path, always_2d=True)
        trimmed = audio[start_frame:end_frame]
        if trimmed.size == 0:
            raise ValueError("Selected segment is empty")

        same_target = os.path.abspath(source_path) == os.path.abspath(output_path)
        write_path = output_path
        temp_path = None
        if same_target:
            fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(output_path)[1] or ".tmp")
            os.close(fd)
            write_path = temp_path

        sf.write(
            write_path,
            trimmed,
            samplerate,
            format=info.format,
            subtype=info.subtype,
        )
        if temp_path is not None:
            os.replace(temp_path, output_path)
        return float(trimmed.shape[0] / samplerate)
    except Exception as primary_error:
        logging.warning("soundfile trimming failed for %s: %s", source_path, primary_error)

    same_target = os.path.abspath(source_path) == os.path.abspath(output_path)
    write_path = output_path
    temp_path = None
    if same_target:
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(output_path)[1] or ".tmp")
        os.close(fd)
        write_path = temp_path

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        source_path,
        "-ss",
        f"{start_seconds:.3f}",
        "-to",
        f"{end_seconds:.3f}",
        write_path,
    ]
    try:
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        if temp_path is not None:
            os.replace(temp_path, output_path)
        return Recorder.get_duration(output_path)
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is required to trim this audio format.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.stderr.decode("utf-8", errors="ignore") or "Audio trimming failed.") from exc


class AudioCompressionJob:
    """Compress one completed WAV capture without blocking the Qt event loop.

    The encoded file is produced immediately.  The source WAV is retained until
    ``release_source`` is called, allowing active transcription workers to finish
    reading it before the database reference is swapped.
    """

    def __init__(
        self,
        source_path,
        record_id,
        db,
        *,
        encoder=None,
        on_success=None,
        on_error=None,
    ):
        import threading

        self.source_path = os.path.abspath(str(source_path))
        self.record_id = int(record_id)
        self.db = db
        self.encoder = encoder or compress_wav_to_mp3
        self.on_success = on_success
        self.on_error = on_error
        self._source_released = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=f"audio-compression-{self.record_id}",
            daemon=True,
        )

    @property
    def thread(self):
        return self._thread

    def start(self):
        self._thread.start()
        return self

    def release_source(self):
        """Permit the job to replace the WAV after its current consumer finishes."""
        self._source_released.set()

    def _run(self):
        import logging

        target_path = None
        database_swapped = False
        try:
            target_path = self.encoder(self.source_path)
            self._source_released.wait()
            source_name = os.path.basename(self.source_path)
            target_name = os.path.basename(target_path)
            if not self.db.replace_filename(self.record_id, source_name, target_name):
                raise RuntimeError("Recording changed or was deleted before compression completed.")
            database_swapped = True
            try:
                os.remove(self.source_path)
            except OSError:
                logging.warning("Compressed recording retained original WAV %s", self.source_path)
            logging.info(
                "Compressed recording record_id=%s source=%s target=%s",
                self.record_id,
                source_name,
                target_name,
            )
            if self.on_success:
                self.on_success(self.record_id, target_path)
        except Exception as exc:
            logging.exception("Audio compression failed for record_id=%s", self.record_id)
            if not database_swapped and target_path and os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except OSError:
                    logging.warning("Unable to remove failed compressed output %s", target_path)
            if self.on_error:
                self.on_error(self.record_id, str(exc))


def compress_wav_to_mp3(source_path: str, *, bitrate: str = "32k") -> str:
    """Encode a WAV capture into a mono 16 kHz MP3 voice profile atomically."""
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Audio source does not exist: {source_path}")
    if os.path.splitext(source_path)[1].lower() != ".wav":
        raise ValueError("Automatic compression only accepts WAV recordings.")

    target_path = os.path.splitext(source_path)[0] + ".mp3"
    temp_path = os.path.splitext(target_path)[0] + ".compressing.mp3"
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        source_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        temp_path,
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
            raise RuntimeError("FFmpeg did not create compressed audio output.")
        os.replace(temp_path, target_path)
        return target_path
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is required for automatic audio compression.") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(detail or "FFmpeg could not compress the recording.") from exc
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


class AudioCompressionService(QObject):
    """Start and coordinate background compression jobs for completed captures."""

    compression_finished = pyqtSignal(int, str)
    compression_failed = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs = {}

    def start_compression(self, source_path, record_id, db, *, encoder=None):
        job = AudioCompressionJob(
            source_path,
            record_id,
            db,
            encoder=encoder,
            on_success=self._on_success,
            on_error=self._on_error,
        )
        self._jobs[int(record_id)] = job
        return job.start()

    def release_source(self, record_id):
        job = self._jobs.get(int(record_id))
        if job is not None:
            job.release_source()

    def _on_success(self, record_id, target_path):
        self._jobs.pop(record_id, None)
        self.compression_finished.emit(record_id, target_path)

    def _on_error(self, record_id, message):
        self._jobs.pop(record_id, None)
        self.compression_failed.emit(record_id, message)
