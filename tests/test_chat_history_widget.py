import os
import sys
import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.chat_history_widget import ChatHistoryWidget, ChatHistorySessionCard


class TestChatHistoryWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def _sample_sessions(self):
        return [
            {
                "id": 1,
                "name": "Sprint review",
                "created_at": "2026-03-10 12:16:00",
                "messages": '[{"role":"user","content":"resume el sprint"},{"role":"assistant","content":"ok"}]',
            },
            {
                "id": 2,
                "name": "Infra notes",
                "created_at": "2026-03-09 08:00:00",
                "messages": '[{"role":"user","content":"kubernetes status"}]',
            },
        ]

    def test_set_sessions_renders_cards_and_count(self):
        widget = ChatHistoryWidget()
        try:
            widget.set_sessions(self._sample_sessions())
            self.assertEqual(widget.sessions_list.count(), 2)
            self.assertEqual(widget.count_label.text(), "2 sessions")
            card = widget.sessions_list.itemWidget(widget.sessions_list.item(0))
            self.assertIsInstance(card, ChatHistorySessionCard)
            self.assertIn("resume el sprint", card.preview_label.text())
        finally:
            widget.deleteLater()

    def test_search_filters_sessions_by_title_and_messages(self):
        widget = ChatHistoryWidget()
        try:
            widget.set_sessions(self._sample_sessions())
            widget.search_input.setText("kubernetes")
            self.assertEqual(widget.sessions_list.count(), 1)
            card = widget.sessions_list.itemWidget(widget.sessions_list.item(0))
            self.assertEqual(card.title_label.text(), "Infra notes")
        finally:
            widget.deleteLater()

    def test_card_buttons_emit_open_and_delete(self):
        widget = ChatHistoryWidget()
        try:
            widget.set_sessions(self._sample_sessions())
            card = widget.sessions_list.itemWidget(widget.sessions_list.item(0))
            opened = []
            deleted = []
            widget.session_requested.connect(opened.append)
            widget.session_delete_requested.connect(deleted.append)

            QTest.mouseClick(card.open_btn, Qt.MouseButton.LeftButton)
            QTest.mouseClick(card.delete_btn, Qt.MouseButton.LeftButton)

            self.assertEqual(opened, [1])
            self.assertEqual(deleted, [1])
        finally:
            widget.deleteLater()


if __name__ == "__main__":
    unittest.main()
