# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Standalone headless PyQt test server running LocalAPIServerThread for Karate."""

import sys
import os
import signal
from unittest.mock import MagicMock

# Force offscreen if any graphics are used
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Add current path to PYTHONPATH
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtCore import QCoreApplication
from src.api.server import LocalAPIServerThread


def main():
    # Instantiate headless console QCoreApplication
    app = QCoreApplication(sys.argv)

    print("[INFO] Initializing Local REST API Test Server for Karate...")
    thread = LocalAPIServerThread()
    
    # Mock databases and RAG dependencies to isolate the HTTP server
    thread.db = MagicMock()
    thread.rag = MagicMock()
    
    # Mock default database fetch outputs
    thread.db.fetch_all.return_value = [
        {"id": 42, "title": "Mock Meeting", "created_at": "2026-09-15 10:00:00", "duration": 120, "summary": "Some summary", "tags": "sync,test"}
    ]
    thread.db.fetch_record.return_value = {
        "id": 42, "title": "Mock Meeting", "created_at": "2026-09-15 10:00:00", "duration": 120, "transcription": "Hello", "recording_notes": "None", "summary": "Some summary", "tags": "sync,test"
    }
    thread.db.get_tasks_for_board.return_value = [
        {"id": 1, "content": "Complete Spec 24", "notes": "Write tests", "day_date": "2026-09-15", "completed": 0}
    ]
    thread.db.save_task.return_value = 100
    
    thread.rag.search.return_value = [
        {"id": "42", "text": "RAG matching snippet", "distance": 0.1, "metadata": {"title": "Mock Meeting"}}
    ]

    # Handle OS signals to stop cleanly
    def handle_signal(signum, frame):
        print("\n[INFO] Signal received. Shutting down REST API thread...")
        thread.stop()
        app.quit()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Simulate status transitions on mock signals for Karate integration testing
    thread.signals.sig_start_recording.connect(lambda: thread.set_recording_status(True, mic_name="Mock Microphone", elapsed=1))
    thread.signals.sig_stop_recording.connect(lambda: thread.set_recording_status(False))

    # Start API server thread
    thread.start()

    # Enter PyQt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
