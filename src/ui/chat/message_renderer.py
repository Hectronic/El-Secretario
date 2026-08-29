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

"""Presentation helpers for rendering chat messages as themed HTML."""

import re

import markdown
from PyQt6.QtGui import QColor


def render_chat_message_html(role, text, is_dark):
    """Return themed HTML fragments for a chat message."""
    if role == "User":
        color = "#64b5f6" if is_dark else "#1565C0"
    elif role == "Assistant":
        color = "#81c784" if is_dark else "#2e7d32"
    else:
        color = "#ff8a80" if is_dark else "#d32f2f"

    text_color = "#ffffff" if is_dark else "#000000"
    font_size = "13px"
    html_content = markdown.markdown(text)
    html_content = apply_message_html_theme(html_content, text_color, is_dark)

    header_html = (
        f"<div style='margin-bottom: 4px;'><b><span style='color: {color}; font-size: 12px;'>{role}:</span></b></div>"
    )
    body_html = f"<div style='font-size: {font_size}; line-height: 1.4;'>{html_content}</div>"
    return header_html, body_html, text_color


def apply_message_html_theme(html_content, text_color, is_dark):
    code_bg = "#2a2f37" if is_dark else "#f3f5f7"
    link_color = "#8fb8ff" if is_dark else "#1565C0"
    themed_html = html_content

    tag_styles = {
        "p": f"color: {text_color};",
        "li": f"color: {text_color};",
        "ul": f"color: {text_color};",
        "ol": f"color: {text_color};",
        "strong": f"color: {text_color};",
        "em": f"color: {text_color};",
        "span": f"color: {text_color};",
        "blockquote": f"color: {text_color};",
        "code": f"color: {text_color}; background-color: {code_bg};",
        "pre": f"color: {text_color}; background-color: {code_bg};",
        "a": f"color: {link_color};",
    }

    for tag, style in tag_styles.items():
        themed_html = re.sub(
            rf"<{tag}(?P<attrs>[^>]*)>",
            lambda m: merge_inline_style(tag, m.group("attrs"), style),
            themed_html,
            flags=re.IGNORECASE,
        )

    return themed_html


def merge_inline_style(tag, attrs, style):
    attrs = attrs or ""
    if "style=" in attrs:
        return re.sub(
            r'style=(["\'])(.*?)\1',
            lambda m: f'style={m.group(1)}{m.group(2)} {style}{m.group(1)}',
            f"<{tag}{attrs}>",
            count=1,
            flags=re.IGNORECASE,
        )
    return f"<{tag}{attrs} style=\"{style}\">"
