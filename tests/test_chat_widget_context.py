import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QDialog

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.chat_widget import ChatWidget
from src.ui.styles import apply_theme


class TestChatWidgetContext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.db_patcher = patch("src.ui.chat_widget.DBManager")
        self.nb_db_patcher = patch("src.ui.chat_widget.NotebookDBManager")
        self.mock_db = self.db_patcher.start().return_value
        self.mock_nb_db = self.nb_db_patcher.start().return_value

        self.mock_db.fetch_by_date_range.return_value = []
        self.mock_db.fetch_by_dates.return_value = []
        self.mock_db.fetch_chat_sessions.return_value = []
        self.mock_nb_db.get_notebooks.return_value = []
        self.mock_nb_db.get_entries.return_value = []
        self.mock_db.compose_ai_text.side_effect = lambda t, n: f"T:{t}\nN:{n}"

        self.rag = MagicMock()
        self.rag.search.return_value = []

    def tearDown(self):
        self.db_patcher.stop()
        self.nb_db_patcher.stop()

    @patch("src.ui.chat_widget.ChatThread")
    @patch("src.ai_provider.validate_ai_provider_config", return_value=(True, ""))
    def test_recording_context_uses_single_meeting_and_notes(self, _mock_validate, mock_chat_thread):
        self.mock_db.fetch_record.return_value = {
            "id": 5,
            "title": "Design Review",
            "created_at": "2026-03-09 09:00:00",
            "transcription": "Transcript body",
            "recording_notes": "Important notes",
            "type": "recording",
            "tags": "",
        }
        worker = MagicMock()
        mock_chat_thread.return_value = worker

        widget = ChatWidget(
            self.rag,
            initial_contexts=[{"type": "recording", "value": 5, "label": "Design Review"}],
        )
        try:
            self.assertFalse(widget.context_panel.sync_cb.isChecked())
            self.assertEqual(widget.context_panel.entries_list.count(), 1)
            self.assertIn("Design Review", widget.context_panel.entries_list.item(0).text())

            widget.input_field.setText("What did we decide?")
            widget.send_message()

            self.assertTrue(mock_chat_thread.called)
            context_text = mock_chat_thread.call_args.args[2]
            self.assertIn("T:Transcript body", context_text)
            self.assertIn("N:Important notes", context_text)
        finally:
            widget.deleteLater()

    @patch("src.ui.chat_widget.ChatThread")
    @patch("src.ai_provider.validate_ai_provider_config", return_value=(True, ""))
    def test_week_range_context_includes_records_and_tasks(self, _mock_validate, mock_chat_thread):
        weekly_record = {
            "id": 8,
            "title": "Weekly Sync",
            "created_at": "2026-03-10 10:00:00",
            "transcription": "Weekly transcript",
            "recording_notes": "Weekly notes",
            "type": "recording",
            "tags": "ops",
        }
        self.mock_db.fetch_by_date_range.return_value = [weekly_record]
        self.mock_db.fetch_record.return_value = weekly_record
        self.mock_db.get_tasks_by_date_range.return_value = [
            {"content": "Send recap", "is_completed": 0, "task_origin": "Weekly Sync", "record_title": "Weekly Sync"}
        ]
        worker = MagicMock()
        mock_chat_thread.return_value = worker

        widget = ChatWidget(
            self.rag,
            initial_contexts=[
                {"type": "date_range", "value": {"start": "2026-03-09", "end": "2026-03-15"}, "label": "week"},
                {"type": "recording", "value": 8, "label": "Weekly Sync"},
                {"type": "tag", "value": "ops", "label": "ops"},
            ],
        )
        try:
            widget.input_field.setText("Summarize the week")
            widget.send_message()

            self.assertTrue(mock_chat_thread.called)
            context_text = mock_chat_thread.call_args.args[2]
            self.assertIn("Weekly transcript", context_text)
            self.assertIn("Weekly notes", context_text)
            self.assertIn("[Tasks]", context_text)
            self.assertIn("Send recap", context_text)
        finally:
            widget.deleteLater()

    @patch("src.ui.chat_widget.AddContextDialog")
    def test_add_context_allows_manual_tag_extension(self, mock_dialog_cls):
        dialog = MagicMock()
        dialog.exec.return_value = QDialog.DialogCode.Accepted
        dialog.selected_context = {"type": "tag", "value": "urgent", "label": "urgent"}
        mock_dialog_cls.return_value = dialog

        widget = ChatWidget(self.rag, initial_contexts=[{"type": "recording", "value": 5, "label": "Design Review"}])
        try:
            widget.add_context()
            self.assertIn("urgent", widget.context_panel.active_global_tags)
        finally:
            widget.deleteLater()

    def test_chat_widget_reapplies_dark_styles_when_theme_changes(self):
        apply_theme("Light")
        widget = ChatWidget(self.rag)
        try:
            self.assertIn("background-color: #ffffff", widget.display.styleSheet())
            self.assertIn("background-color: #f5f5f5", widget.input_field.styleSheet())

            apply_theme("Dark")
            self.app.processEvents()

            self.assertIn("background-color: #1f232a", widget.display.styleSheet())
            self.assertIn("color: #f3f6fb", widget.display.styleSheet())
            self.assertIn("background-color: #2a2f37", widget.input_field.styleSheet())
            self.assertIn("color: #e8eef7", widget.title_label.styleSheet())
        finally:
            widget.deleteLater()
            apply_theme("Light")

    def test_chat_widget_dark_messages_force_light_markdown_text(self):
        apply_theme("Dark")
        widget = ChatWidget(self.rag)
        try:
            widget.append_to_chat("Assistant", "Texto normal\n\n- punto\n\n**negrita**")
            html = widget.display.toHtml()
            self.assertIn("#ffffff", html.lower())
        finally:
            widget.deleteLater()
            apply_theme("Light")

    def test_context_panel_toggle_button_collapses_and_restores(self):
        widget = ChatWidget(self.rag)
        try:
            self.assertFalse(widget.context_panel.is_collapsed())
            self.assertFalse(widget.context_panel.header_label.isHidden())
            self.assertFalse(widget.context_panel.content_widget.isHidden())
            self.assertEqual(widget.context_panel.toggle_btn.text(), "⟩")

            widget.context_panel.toggle_btn.click()

            self.assertTrue(widget.context_panel.is_collapsed())
            self.assertTrue(widget.context_panel.header_label.isHidden())
            self.assertTrue(widget.context_panel.content_widget.isHidden())
            self.assertEqual(widget.context_panel.toggle_btn.text(), "⟨")
            self.assertEqual(widget.context_panel.minimumWidth(), widget.context_panel.COLLAPSED_WIDTH)
            self.assertEqual(widget.context_panel.maximumWidth(), widget.context_panel.COLLAPSED_WIDTH)

            widget.context_panel.toggle_btn.click()

            self.assertFalse(widget.context_panel.is_collapsed())
            self.assertFalse(widget.context_panel.header_label.isHidden())
            self.assertFalse(widget.context_panel.content_widget.isHidden())
            self.assertEqual(widget.context_panel.toggle_btn.text(), "⟩")
            self.assertEqual(widget.context_panel.minimumWidth(), 280)
            self.assertGreater(widget.context_panel.maximumWidth(), 280)
        finally:
            widget.deleteLater()
