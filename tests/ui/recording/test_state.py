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
# along with this program.  See <https://www.gnu.org/licenses/>.

import os

from src.ui.recording.state import (
    fallback_record_title,
    record_has_ai_text,
    recording_audio_path,
    to_bool,
)


def test_recording_audio_path_uses_recordings_directory():
    assert recording_audio_path({"filename": "call.wav"}, "/tmp/app") == os.path.join(
        "/tmp/app", "recordings", "call.wav"
    )


def test_record_has_ai_text_checks_transcription_and_notes():
    assert record_has_ai_text({"transcription": "", "recording_notes": ""}) is False
    assert record_has_ai_text({"transcription": "Transcript", "recording_notes": ""}) is True
    assert record_has_ai_text({"transcription": "", "recording_notes": "Notes"}) is True


def test_fallback_record_title_uses_stripped_title_or_recording_label():
    assert fallback_record_title(7, " Weekly sync ") == "Weekly sync"
    assert fallback_record_title(7, "   ") == "Recording 7"
    assert fallback_record_title(7, None) == "Recording 7"


def test_to_bool_normalizes_settings_values():
    assert to_bool(True) is True
    assert to_bool(False) is False
    assert to_bool(None) is False
    assert to_bool("yes") is True
    assert to_bool("0") is False
    assert to_bool(1) is True
