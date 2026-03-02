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
import os
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import tempfile
import shutil

from src.database import DBManager
from src.rag_engine import RAGEngine


class TestCalendarLogic(unittest.TestCase):
    def setUp(self):
        # Create a temp directory
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_db.sqlite")
        
        self.db = DBManager(self.db_path)
        self.rag = RAGEngine(os.path.join(self.test_dir, "chroma"))
        
        # Insert some test data
        self.db.save("rec1.wav", "Transcription 1", 10.0, "Title 1")
        # Update tags manually since save doesn't take tags
        records = self.db.fetch_all()
        rec1_id = records[0]['id']
        self.db.update_tags(rec1_id, "meeting, work")
        
        # Hack to simulate different dates
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE records SET created_at = '2023-01-01 10:00:00' WHERE id = ?", (rec1_id,))
            conn.commit()
            
        self.db.save("rec2.wav", "Transcription 2", 20.0, "Title 2")
        records = self.db.fetch_all()
        rec2_id = records[0]['id'] # This should be the new one
        self.db.update_tags(rec2_id, "personal")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE records SET created_at = '2023-01-02 10:00:00' WHERE id = ?", (rec2_id,))
            conn.commit()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_fetch_by_date_range(self):
        # Test fetching for 2023-01-01
        results = self.db.fetch_by_date_range("2023-01-01", "2023-01-01")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Title 1")
        
        # Test fetching for 2023-01-02
        results = self.db.fetch_by_date_range("2023-01-02", "2023-01-02")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Title 2")
        
        # Test fetching range
        results = self.db.fetch_by_date_range("2023-01-01", "2023-01-02")
        self.assertEqual(len(results), 2)
        
        # Test fetching empty range
        results = self.db.fetch_by_date_range("2023-01-03", "2023-01-03")
        self.assertEqual(len(results), 0)

    def test_fetch_by_date_and_tags(self):
        # Test fetching with tag filter
        results = self.db.fetch_by_date_range("2023-01-01", "2023-01-02", tags=["work"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Title 1")
        
        results = self.db.fetch_by_date_range("2023-01-01", "2023-01-02", tags=["personal"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Title 2")
        
        results = self.db.fetch_by_date_range("2023-01-01", "2023-01-02", tags=["nonexistent"])
        self.assertEqual(len(results), 0)

    def test_rag_search_with_ids(self):
        # Mock collection.query
        self.rag.collection.query = MagicMock(return_value={
            'ids': [['1']],
            'documents': [['Text']],
            'metadatas': [[{'id': '1'}]],
            'distances': [[0.1]]
        })
        
        # Test search with ids
        self.rag.search("query", ids=["1", "2"])
        
        # Verify call args
        call_args = self.rag.collection.query.call_args
        _, kwargs = call_args
        where_arg = kwargs.get('where')
        
        # We expect where con el filtro de borrado suave añadido automáticamente
        expected_where = {"$and": [{'id': {'$in': ['1', '2']}}, {"deleted": {"$ne": "1"}}]}
        self.assertEqual(where_arg, expected_where)
        
        # Test single id
        self.rag.search("query", ids=["1"])
        call_args = self.rag.collection.query.call_args
        _, kwargs = call_args
        where_arg = kwargs.get('where')
        self.assertEqual(where_arg, {'$and': [{'id': '1'}, {'deleted': {'$ne': '1'}}]})

if __name__ == '__main__':
    unittest.main()
