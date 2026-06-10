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

from unittest.mock import MagicMock

from src.ui.recording.audio_trim import (
    AUDIO_FILE_NOT_AVAILABLE_MESSAGE,
    INVALID_TRIM_RANGE_MESSAGE,
    mark_trim_end,
    mark_trim_start,
    playhead_seconds,
    trim_recording_audio,
    validate_trim_request,
)


def test_playhead_seconds_clamps_negative_positions():
    assert playhead_seconds(2500) == 2.5
    assert playhead_seconds(-100) == 0.0


def test_mark_trim_start_keeps_end_after_start():
    assert mark_trim_start(0.0, 2.0, 1.5) == (1.5, 2.0)
    assert mark_trim_start(0.0, 1.0, 1.5) == (1.5, 1.5)


def test_mark_trim_end_keeps_start_before_end():
    assert mark_trim_end(1.0, 2.0, 1.5) == (1.0, 1.5)
    assert mark_trim_end(2.0, 3.0, 1.5) == (1.5, 1.5)


def test_validate_trim_request_reports_missing_audio_and_invalid_range():
    assert validate_trim_request("", 0.0, 1.0) == AUDIO_FILE_NOT_AVAILABLE_MESSAGE
    assert validate_trim_request("/tmp/a.wav", 1.0, 1.0, exists=lambda _path: True) == INVALID_TRIM_RANGE_MESSAGE
    assert validate_trim_request("/tmp/a.wav", 0.0, 1.0, exists=lambda _path: True) is None


def test_trim_recording_audio_creates_backup_then_trims_in_place():
    copy_func = MagicMock()
    trim_func = MagicMock(return_value=3.5)
    existing_paths = {"/tmp/a.wav"}

    duration = trim_recording_audio(
        "/tmp/a.wav",
        1.0,
        4.5,
        trim_func,
        copy_func=copy_func,
        exists=lambda path: path in existing_paths,
    )

    assert duration == 3.5
    copy_func.assert_called_once_with("/tmp/a.wav", "/tmp/a.wav.orig")
    trim_func.assert_called_once_with("/tmp/a.wav", 1.0, 4.5, "/tmp/a.wav")


def test_trim_recording_audio_skips_existing_backup():
    copy_func = MagicMock()
    trim_func = MagicMock(return_value=2.0)
    existing_paths = {"/tmp/a.wav", "/tmp/a.wav.orig"}

    trim_recording_audio(
        "/tmp/a.wav",
        0.0,
        2.0,
        trim_func,
        copy_func=copy_func,
        exists=lambda path: path in existing_paths,
    )

    copy_func.assert_not_called()
