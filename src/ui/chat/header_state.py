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

def build_chat_header_state(display_mode: str, floating_minimized: bool):
    """Return derived header state for a chat widget."""
    is_floating = display_mode == "floating"
    minimized = bool(floating_minimized) and is_floating

    return {
        "header_visible": is_floating,
        "mode_btn_text": "⇱" if is_floating else "↗",
        "mode_btn_tooltip": "Move chat back to tab" if is_floating else "Move chat to floating bar",
        "minimize_visible": is_floating,
        "content_visible": not minimized,
        "minimize_btn_text": "□" if minimized else "_",
        "minimize_btn_tooltip": "Restore chat" if minimized else "Minimize to title bar",
        "cursor": "pointing" if minimized else "arrow",
        "layout_margin": 1 if is_floating else 0,
    }
