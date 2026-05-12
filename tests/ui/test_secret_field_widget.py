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

import sys

from PyQt6 import sip
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLineEdit

from src.ui.secret_field_widget import SecretFieldWidget


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


def test_secret_field_toggles_echo_mode_and_label():
    _app()
    widget = SecretFieldWidget(current_value="secret-value", placeholder="hf_...")
    try:
        assert widget.line_edit.text() == "secret-value"
        assert widget.line_edit.echoMode() == QLineEdit.EchoMode.Password
        assert widget.show_button.text() == "👁️"

        widget.show_button.click()

        assert widget.line_edit.echoMode() == QLineEdit.EchoMode.Normal
        assert widget.show_button.text() == "🔒"

        widget.show_button.click()

        assert widget.line_edit.echoMode() == QLineEdit.EchoMode.Password
        assert widget.show_button.text() == "👁️"
    finally:
        widget.close()
        sip.delete(widget)


def test_secret_field_copies_text_to_clipboard():
    _app()
    widget = SecretFieldWidget(current_value="copied-secret", placeholder="AIza...")
    try:
        clipboard = QApplication.clipboard()
        clipboard.clear()

        widget.copy_button.click()

        assert clipboard.text() == "copied-secret"
    finally:
        widget.close()
        sip.delete(widget)
