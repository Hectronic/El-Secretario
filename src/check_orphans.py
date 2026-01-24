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
import sqlite3

def check_orphans():
    conn = sqlite3.connect("transcriptions.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, filename, is_diarized FROM records")
    rows = cursor.fetchall()
    
    orphans = []
    for row in rows:
        file_path = os.path.join(os.getcwd(), "recordings", row['filename'])
        if not os.path.exists(file_path):
            orphans.append(dict(row))
            
    print(f"Total records: {len(rows)}")
    print(f"Orphaned records: {len(orphans)}")
    for o in orphans:
        print(f"Orphan: ID={o['id']}, File={o['filename']}, Diarized={o['is_diarized']}")
        
    conn.close()

if __name__ == "__main__":
    check_orphans()
