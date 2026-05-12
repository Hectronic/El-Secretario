# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <https://www.gnu.org/licenses/>.

from src.ui.chat.busy_state import build_chat_busy_state


def test_busy_state_enabled():
    state = build_chat_busy_state(False)

    assert state["send_enabled"] is True
    assert state["input_enabled"] is True
    assert state["cursor_shape"] == "restore"


def test_busy_state_disabled():
    state = build_chat_busy_state(True)

    assert state["send_enabled"] is False
    assert state["input_enabled"] is False
    assert state["cursor_shape"] == "wait"
