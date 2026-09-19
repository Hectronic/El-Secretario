import os
import unittest

from src.database import DBManager


class DatabaseRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.db_name = "test_db.sqlite"
        self.db = DBManager(self.db_name)

    def tearDown(self):
        if os.path.exists(self.db_name):
            os.remove(self.db_name)
