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

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout

from src.ui.main_window import chat_context_sidebar as sidebar_module
from src.ui.main_window.chat_context_sidebar import install_chat_context_sidebar_section


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication([])
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Panel(QWidget):
    def __init__(self, db, notebook_db, parent=None, show_header=True, interactive=True):
        super().__init__(parent)
        self.args = {
            "db": db,
            "notebook_db": notebook_db,
            "parent": parent,
            "show_header": show_header,
            "interactive": interactive,
        }


def test_install_chat_context_sidebar_section_registers_hidden_context_panel(monkeypatch):
    _app()
    monkeypatch.setattr(sidebar_module, "ContextManagerPanel", _Panel)

    window = MagicMock()
    window.db = object()
    window.notebook_db = object()
    window._right_sidebar_sections = {}

    right_panel = QWidget()
    right_layout = QVBoxLayout(right_panel)

    def create_section(section_key, title, top_widget=None, **_kwargs):
        section = QWidget()
        container = QWidget()
        content = QWidget()
        window._right_sidebar_sections[section_key] = {
            "title": title,
            "container": container,
            "content": content,
            "top_widget": top_widget,
        }
        return section

    try:
        section = install_chat_context_sidebar_section(
            window,
            right_panel=right_panel,
            right_layout=right_layout,
            create_section=create_section,
        )

        registered = window._right_sidebar_sections["chat_context"]
        assert window.chat_context_section is section
        assert registered["title"] == "💬 Active Chat Context"
        assert registered["context_panel"] is window.chat_context_panel
        assert registered["top_widget"] is window.chat_context_panel
        assert registered["index"] == right_layout.indexOf(section)
        assert registered["container"].isHidden()
        assert window.chat_context_panel.args == {
            "db": window.db,
            "notebook_db": window.notebook_db,
            "parent": right_panel,
            "show_header": False,
            "interactive": False,
        }
    finally:
        right_panel.deleteLater()
