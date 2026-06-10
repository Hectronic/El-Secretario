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


def recording_audio_path(record, base_dir):
    return os.path.join(base_dir, "recordings", record["filename"])


def record_has_ai_text(record):
    return bool(
        (record.get("transcription") or "").strip()
        or (record.get("recording_notes") or "").strip()
    )


def fallback_record_title(record_id, title=None):
    value = (title or "").strip()
    return value or f"Recording {record_id}"


def to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)
