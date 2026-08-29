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
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from src.ui.chat.context_state import parse_chat_context_state


def test_parse_chat_context_state_normalizes_mixed_contexts():
    state = parse_chat_context_state(
        [
            {"type": "date_range", "value": {"start": "2026-03-09", "end": "2026-03-15"}},
            {"type": "tag", "value": "ops"},
            {"type": "notebook", "value": 3},
            {"type": "recording", "value": "7", "label": "Design Review"},
        ]
    )

    assert state["current_date_filter"] == "2026-03-15"
    assert state["active_global_tags"] == ["ops"]
    assert state["notebook_ids"] == [3]
    assert state["forced_record_ids"] == {7}
    assert state["forced_record_labels"] == ["Design Review"]
    assert state["has_recording_context"] is True
