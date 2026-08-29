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

from src.ui.context_manager_panel import ContextManagerPanel


def install_chat_context_sidebar_section(window, *, right_panel, right_layout, create_section):
    """Create and register the non-interactive active-chat context section."""
    window.chat_context_panel = ContextManagerPanel(
        window.db,
        window.notebook_db,
        parent=right_panel,
        show_header=False,
        interactive=False,
    )
    window.chat_context_section = create_section(
        "chat_context",
        "💬 Active Chat Context",
        top_widget=window.chat_context_panel,
    )
    window._right_sidebar_sections["chat_context"]["context_panel"] = window.chat_context_panel
    right_layout.addWidget(window.chat_context_section)
    window._right_sidebar_sections["chat_context"]["index"] = right_layout.indexOf(
        window.chat_context_section
    )
    window._right_sidebar_sections["chat_context"]["container"].setVisible(False)
    return window.chat_context_section
