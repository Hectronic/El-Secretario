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

"""Helpers that derive UI state for the chat busy indicator."""


def build_chat_busy_state(busy: bool):
    """Return the button and cursor state for a busy chat widget."""
    busy = bool(busy)
    return {
        "send_enabled": not busy,
        "input_enabled": not busy,
        "cursor_shape": "wait" if busy else "restore",
    }
