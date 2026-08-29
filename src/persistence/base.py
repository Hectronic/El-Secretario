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

import os
import sqlite3
from contextlib import contextmanager



class PersistenceBase:
    def __init__(self, db_name: str = "transcriptions.db"):
        self.db_name = os.path.abspath(db_name)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        # Use Row factory for easier access by default
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
