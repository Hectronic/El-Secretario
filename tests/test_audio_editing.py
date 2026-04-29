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
import tempfile
import unittest

import numpy as np
import soundfile as sf

from src.audio import trim_audio_segment


class TestAudioEditing(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp(prefix="secretario_audio_edit_")
        self.audio_path = os.path.join(self.tempdir, "sample.wav")
        samplerate = 16000
        tone = np.sin(2 * np.pi * 220 * np.arange(samplerate) / samplerate).astype(np.float32)
        sf.write(self.audio_path, tone, samplerate)

    def tearDown(self):
        for root, _, files in os.walk(self.tempdir, topdown=False):
            for filename in files:
                try:
                    os.remove(os.path.join(root, filename))
                except FileNotFoundError:
                    pass
        try:
            os.rmdir(self.tempdir)
        except OSError:
            pass

    def test_trim_audio_segment_overwrites_file_with_selected_range(self):
        duration = trim_audio_segment(self.audio_path, 0.25, 0.75, self.audio_path)

        self.assertAlmostEqual(duration, 0.5, places=2)
        info = sf.info(self.audio_path)
        self.assertAlmostEqual(info.frames / info.samplerate, 0.5, places=2)

    def test_trim_audio_segment_rejects_invalid_ranges(self):
        with self.assertRaises(ValueError):
            trim_audio_segment(self.audio_path, 0.8, 0.2, self.audio_path)


if __name__ == "__main__":
    unittest.main()
