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

import logging
import os
import shutil


AUDIO_FILE_NOT_AVAILABLE_MESSAGE = "Audio file not available."
INVALID_TRIM_RANGE_MESSAGE = "The trim end must be greater than the start."


def playhead_seconds(position_milliseconds):
    return max(0.0, float(position_milliseconds) / 1000.0)


def mark_trim_start(start_value, end_value, playhead_value):
    start = max(0.0, float(playhead_value))
    end = max(float(end_value), start)
    return start, end


def mark_trim_end(start_value, end_value, playhead_value):
    end = max(0.0, float(playhead_value))
    start = min(float(start_value), end)
    return start, end


def validate_trim_request(audio_path, start_seconds, end_seconds, exists=os.path.exists):
    if not audio_path or not exists(audio_path):
        return AUDIO_FILE_NOT_AVAILABLE_MESSAGE
    if float(end_seconds) <= float(start_seconds):
        return INVALID_TRIM_RANGE_MESSAGE
    return None


def trim_recording_audio(
    audio_path,
    start_seconds,
    end_seconds,
    trim_audio_segment_func,
    copy_func=shutil.copy2,
    exists=os.path.exists,
):
    backup_path = f"{audio_path}.orig"
    if not exists(backup_path):
        try:
            copy_func(audio_path, backup_path)
        except Exception:
            logging.exception("Unable to create backup copy before trimming")

    return trim_audio_segment_func(audio_path, start_seconds, end_seconds, audio_path)
