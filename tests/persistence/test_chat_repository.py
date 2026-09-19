import gc
import os
import sqlite3
import time
from datetime import date

from src.database import DBManager

from ._database_case import DatabaseRepositoryTestCase


class TestChatSessionsRepository(DatabaseRepositoryTestCase):
    def test_chat_sessions(self):
        session_id = self.db.save_chat_session('Chat 1', 'All', '[]')
        sessions = self.db.fetch_chat_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]['name'], 'Chat 1')
        self.db.update_chat_session(session_id, "[{'role': 'user'}]")
        sessions = self.db.fetch_chat_sessions()
        self.assertEqual(sessions[0]['messages'], "[{'role': 'user'}]")
        self.db.delete_chat_session(session_id)
        sessions = self.db.fetch_chat_sessions()
        self.assertEqual(len(sessions), 0)
