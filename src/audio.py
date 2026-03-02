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

import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

class Recorder(QObject):
    amplitude_changed = pyqtSignal(float) # Signal to emit RMS amplitude (0.0 to 1.0)

    def __init__(self, sample_rate=16000, channels=1):
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
        
        # Calculate RMS amplitude for VU meter
        rms = np.sqrt(np.mean(indata**2))
        self.amplitude_changed.emit(rms)

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
