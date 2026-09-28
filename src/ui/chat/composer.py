"""Accessible multiline composer with explicit Enter/Shift+Enter behavior."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QTextEdit


class ChatComposer(QTextEdit):
    returnPressed = pyqtSignal()

    def text(self):
        return self.toPlainText()

    def setText(self, text):
        self.setPlainText(text)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and not (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.returnPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
