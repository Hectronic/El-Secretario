import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.chat_widget import ContextManagerPanel

app = QApplication.instance() or QApplication([])

class TestChatContextSync(unittest.TestCase):
    def test_notebooks_sync(self):
        db = MagicMock()
        notebook_db = MagicMock()
        notebook_db.get_notebooks.return_value = [{"id": 1, "name": "Notebook 1"}, {"id": 2, "name": "Notebook 2"}]
        
        panel1 = ContextManagerPanel(db, notebook_db)
        panel2 = ContextManagerPanel(db, notebook_db, show_header=False, interactive=False)
        
        panel1.load_notebooks()
        panel2.load_notebooks()
        
        # Check an item in panel 1
        panel1.nb_list.item(0).setCheckState(Qt.CheckState.Checked)
        
        state = panel1.serialize_state()
        self.assertIn(1, state["notebook_ids"])
        
        panel2.restore_from_panel(panel1)
        
        self.assertEqual(panel2.nb_list.item(0).checkState(), Qt.CheckState.Checked)
        self.assertEqual(panel2.nb_list.item(1).checkState(), Qt.CheckState.Unchecked)

    def test_restore_none(self):
        db = MagicMock()
        notebook_db = MagicMock()
        panel = ContextManagerPanel(db, notebook_db)
        panel.restore_from_panel(None) # Should return without error
