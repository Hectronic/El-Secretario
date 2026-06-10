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

import re


SPEAKER_LABEL_PATTERN = re.compile(r"SPEAKER_\d+")


def find_speaker_labels(text):
    return sorted(set(SPEAKER_LABEL_PATTERN.findall(text or "")))


def apply_speaker_mapping(text, mapping):
    updated = text or ""
    for speaker_label, new_name in mapping.items():
        updated = updated.replace(speaker_label, new_name)
    return updated
