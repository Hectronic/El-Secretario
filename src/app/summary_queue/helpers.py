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

import json
import logging
import re
from typing import Any


def read_audio_duration_seconds(audio_path: str) -> float:
    """Best-effort duration probe used to scale queued transcription progress."""
    try:
        import soundfile as sf

        with sf.SoundFile(audio_path) as audio_file:
            return len(audio_file) / audio_file.samplerate
    except Exception as e:
        logging.warning("Could not read audio duration for queued transcription %s: %s", audio_path, e)
        return 0.0


def parse_task_extraction_result(raw_result: Any) -> list[str]:
    """Parse the AI task-extraction response into clean task strings."""
    clean_result = str(raw_result or "").strip()
    match = re.search(r"(\[.*\])", clean_result, re.DOTALL)
    if match:
        clean_result = match.group(1)

    try:
        parsed = json.loads(clean_result)
    except Exception:
        return []

    if not isinstance(parsed, list):
        return []
    return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]
