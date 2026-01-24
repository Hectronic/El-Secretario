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

import os
import shutil
import unittest
from src.notebook_database import NotebookDBManager

class TestNotebooks(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_notebooks.db"
        self.db = NotebookDBManager(self.db_name)
        
    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
            
    def test_create_notebook(self):
        nb_id = self.db.create_notebook("Test Notebook", "Description")
        notebooks = self.db.get_notebooks()
        self.assertEqual(len(notebooks), 1)
        self.assertEqual(notebooks[0]['name'], "Test Notebook")
        
    def test_add_text_entry(self):
        nb_id = self.db.create_notebook("Test Notebook")
        self.db.add_text_entry(nb_id, "Hello World", "Title")
        entries = self.db.get_entries(nb_id)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['content'], "Hello World")
        self.assertEqual(entries[0]['type'], "text")
        
    def test_add_audio_entry(self):
        nb_id = self.db.create_notebook("Test Notebook")
        self.db.add_audio_entry(nb_id, "/tmp/fake.wav", 10.0)
        entries = self.db.get_entries(nb_id)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['type'], "audio")
        self.assertEqual(entries[0]['content'], "Transcribing...")

    def test_rename_notebook(self):
        nb_id = self.db.create_notebook("Old Name")
        self.db.rename_notebook(nb_id, "New Name")
        notebook = self.db.get_notebook(nb_id)
        self.assertEqual(notebook['name'], "New Name")

    def test_rename_entry(self):
        nb_id = self.db.create_notebook("Test Notebook")
        entry_id = self.db.add_text_entry(nb_id, "Content", "Old Title")
        self.db.rename_entry(entry_id, "New Title")
        entries = self.db.get_entries(nb_id)
        self.assertEqual(entries[0]['title'], "New Title")

    def test_delete_notebook(self):
        nb_id = self.db.create_notebook("To Delete")
        self.db.add_text_entry(nb_id, "Content")
        self.db.delete_notebook(nb_id)
        notebooks = self.db.get_notebooks()
        self.assertEqual(len(notebooks), 0)
        # Verify entries are gone (cascade delete)
        entries = self.db.get_entries(nb_id)
        self.assertEqual(len(entries), 0)

if __name__ == '__main__':
    unittest.main()
