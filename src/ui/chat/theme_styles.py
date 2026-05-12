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

def build_chat_widget_theme(is_dark: bool):
    """Return the color palette used by ChatWidget styles."""
    if is_dark:
        return {
            "header_bg": "rgba(33, 150, 243, 0.15)",
            "header_border": "rgba(33, 150, 243, 0.45)",
            "title_color": "#e8eef7",
            "btn_color": "#94a3b8",
            "btn_hover": "rgba(255, 255, 255, 0.08)",
            "display_bg": "#1f232a",
            "display_text": "#f3f6fb",
            "input_bg": "#2a2f37",
            "input_border": "#4f5b6f",
            "display_border": "#404b5c",
        }

    return {
        "header_bg": "rgba(33, 150, 243, 0.10)",
        "header_border": "rgba(33, 150, 243, 0.35)",
        "title_color": "#2b3b52",
        "btn_color": "#546E7A",
        "btn_hover": "rgba(0, 0, 0, 0.05)",
        "display_bg": "#ffffff",
        "display_text": "#1a1c1e",
        "input_bg": "#f5f5f5",
        "input_border": "#cccccc",
        "display_border": "#cccccc",
    }
