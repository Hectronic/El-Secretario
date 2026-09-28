from PyQt6.QtCore import Qt

from src.ui.chat.composer import ChatComposer


def test_shift_enter_inserts_newline_and_enter_requests_send(qtbot):
    composer = ChatComposer()
    qtbot.addWidget(composer)
    sent = []
    composer.returnPressed.connect(lambda: sent.append(composer.toPlainText()))
    composer.setFocus()

    qtbot.keyClicks(composer, "first")
    qtbot.keyClick(composer, Qt.Key.Key_Return, modifier=Qt.KeyboardModifier.ShiftModifier)
    qtbot.keyClicks(composer, "second")
    qtbot.keyClick(composer, Qt.Key.Key_Return)

    assert composer.toPlainText() == "first\nsecond"
    assert sent == ["first\nsecond"]
