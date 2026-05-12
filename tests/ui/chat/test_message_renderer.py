# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from src.ui.chat.message_renderer import apply_message_html_theme, merge_inline_style, render_chat_message_html


def test_render_chat_message_html_themes_user_and_assistant():
    user_header, user_body, user_color = render_chat_message_html("User", "Hola", True)
    assistant_header, assistant_body, assistant_color = render_chat_message_html("Assistant", "Hola", False)

    assert "User:" in user_header
    assert "Assistant:" in assistant_header
    assert "#ffffff" == user_color
    assert "#000000" == assistant_color
    assert "Hola" in user_body
    assert "Hola" in assistant_body


def test_apply_message_html_theme_adds_inline_styles():
    themed = apply_message_html_theme("<p>Text</p><a href='#'>Link</a>", "#111111", False)
    assert "color: #111111;" in themed
    assert "color: #1565C0;" in themed


def test_merge_inline_style_appends_existing_style():
    html = merge_inline_style("p", ' class="x" style="color:red;"', "font-weight:bold;")
    assert "color:red;" in html
    assert "font-weight:bold;" in html
