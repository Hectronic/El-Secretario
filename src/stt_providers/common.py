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

from __future__ import annotations


def serialize_segments(segments):
    return [
        {"start": float(s.start), "end": float(s.end), "text": str(s.text)}
        for s in segments
    ]


def normalize_openai_whisper_model_name(model_size: str) -> str:
    if model_size in ("large-v3", "large-v2"):
        return "large"
    return model_size
