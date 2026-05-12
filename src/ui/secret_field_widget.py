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

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QPushButton, QWidget


class SecretFieldWidget(QWidget):
    """Masked text field with visibility and copy controls.

    This widget centralizes the token-style input used in settings panels so the
    UI keeps one implementation for show/hide and copy-to-clipboard behavior.
    """

    def __init__(self, current_value: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self.line_edit = QLineEdit()
        self.show_button = QPushButton("👁️")
        self.copy_button = QPushButton("📋")
        self._setup_ui(current_value, placeholder)

    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, value: str):
        self.line_edit.setText(value)

    def _setup_ui(self, current_value: str, placeholder: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setText(current_value)
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setMinimumWidth(350)

        self.show_button.setToolTip("Show/Hide Token")
        self.show_button.setFixedSize(30, 30)
        self.show_button.setCheckable(True)
        self.show_button.clicked.connect(self._toggle_echo)

        self.copy_button.setToolTip("Copy Token")
        self.copy_button.setFixedSize(30, 30)
        self.copy_button.clicked.connect(self._copy_text)

        layout.addWidget(self.line_edit)
        layout.addWidget(self.show_button)
        layout.addWidget(self.copy_button)

    def _toggle_echo(self):
        if self.show_button.isChecked():
            self.line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_button.setText("🔒")
            return

        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_button.setText("👁️")

    def _copy_text(self):
        QApplication.clipboard().setText(self.line_edit.text())
