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

import sqlite3
import os
from src.database import DBManager

# Remove existing db to force recreation or just check existing one
# We want to check if migration works, so we should check the existing one if possible, 
# but we don't know if it exists or is empty.
# Let's just initialize DBManager and check columns.

db = DBManager("transcriptions.db")
# init_db is called in __init__

conn = sqlite3.connect("transcriptions.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(records)")
columns = [info[1] for info in cursor.fetchall()]

print("Columns in records table:", columns)

expected_columns = ['is_diarized', 'transcription_model']
missing = [col for col in expected_columns if col not in columns]

if missing:
    print(f"FAILED: Missing columns: {missing}")
else:
    print("SUCCESS: All expected columns found.")

conn.close()
