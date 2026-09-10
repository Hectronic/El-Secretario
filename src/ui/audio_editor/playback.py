"""Temporary preview-file and media-player lifecycle for the audio editor."""

import os
import tempfile

import soundfile as sf
from PyQt6.QtCore import QUrl


class AudioEditorPlaybackController:
    """Own preview media files while exposing a stable Qt player to the widget."""

    def __init__(self, player, audio_output):
        self.player = player
        self.audio_output = audio_output
        self.preview_temp_path = None

    def refresh_preview(self, audio, sample_rate):
        self._remove_preview_file()
        if audio is None:
            self.player.setSource(QUrl())
            return
        descriptor, path = tempfile.mkstemp(prefix="secretario_audio_preview_", suffix=".wav")
        os.close(descriptor)
        sf.write(path, audio, sample_rate)
        self.preview_temp_path = path
        self.player.setSource(QUrl.fromLocalFile(path))

    def cleanup(self):
        self.player.stop()
        self.player.setSource(QUrl())
        self._remove_preview_file()

    def _remove_preview_file(self):
        if self.preview_temp_path and os.path.exists(self.preview_temp_path):
            try:
                os.remove(self.preview_temp_path)
            except OSError:
                pass
        self.preview_temp_path = None
