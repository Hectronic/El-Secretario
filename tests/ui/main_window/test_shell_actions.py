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

from unittest.mock import MagicMock

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QPushButton

from src.ui.main_window.shell_actions import MainWindowShellCoordinator


def test_set_active_right_section_updates_headers_content_and_stretch(qtbot):
    window = MagicMock()
    layout_host = QWidget()
    qtbot.addWidget(layout_host)
    layout = QVBoxLayout(layout_host)
    header = QPushButton()
    shell = QWidget()
    content = QWidget()
    layout.addWidget(content)
    layout.addStretch()
    window._right_sidebar_sections = {
        "tasks": {
            "title": "Tasks",
            "header": header,
            "header_shell": shell,
            "content": content,
            "index": 0,
        }
    }
    window._right_sidebar_layout = layout
    window._right_sidebar_bottom_spacer_index = 1
    window._active_right_section = None
    window._right_sidebar_last_non_chat_section = "tasks"

    MainWindowShellCoordinator(window).set_active_right_section("tasks")

    assert window._active_right_section == "tasks"
    assert header.text() == "▾ Tasks"
    assert not content.isHidden()
    assert shell.property("active") == "true"
