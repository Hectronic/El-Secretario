import os

import numpy as np

from src.ui.audio_editor.playback import AudioEditorPlaybackController


class _Player:
    def __init__(self):
        self.sources = []
        self.stopped = False

    def setSource(self, source):
        self.sources.append(source)

    def stop(self):
        self.stopped = True


def test_preview_playback_replaces_and_removes_its_temporary_audio_file():
    player = _Player()
    controller = AudioEditorPlaybackController(player, object())
    audio = np.array([[0.1], [0.2]], dtype=np.float32)

    controller.refresh_preview(audio, 4)
    first_path = controller.preview_temp_path
    controller.refresh_preview(audio, 4)
    second_path = controller.preview_temp_path
    controller.cleanup()

    assert first_path != second_path
    assert not os.path.exists(first_path)
    assert not os.path.exists(second_path)
    assert player.stopped is True
    assert controller.preview_temp_path is None
    assert len(player.sources) == 3
