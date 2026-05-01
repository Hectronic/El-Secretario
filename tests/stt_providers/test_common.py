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

from types import SimpleNamespace

from src.stt_providers.common import normalize_openai_whisper_model_name, serialize_segments


def test_serialize_segments_normalizes_objects():
    segments = [SimpleNamespace(start=1, end=2.5, text=123)]

    assert serialize_segments(segments) == [{"start": 1.0, "end": 2.5, "text": "123"}]


def test_normalize_openai_whisper_model_name_keeps_compatibility():
    assert normalize_openai_whisper_model_name("large-v3") == "large"
    assert normalize_openai_whisper_model_name("large-v2") == "large"
    assert normalize_openai_whisper_model_name("base") == "base"
