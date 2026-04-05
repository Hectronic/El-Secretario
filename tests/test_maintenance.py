# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ui.maintenance_widget import MaintenanceWidget

class TestMaintenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.mock_db = MagicMock()
        self.widget = MaintenanceWidget(self.mock_db)
        
        # Setup temporary test directory and files
        self.test_dir = os.path.join(os.getcwd(), "recordings")
        os.makedirs(self.test_dir, exist_ok=True)
        self.test_files = ["test_maint_1.wav", "test_maint_2.wav", "test_maint_3.wav"]
        
        for f in self.test_files:
            with open(os.path.join(self.test_dir, f), "w") as tf:
                tf.write("test data")

    def tearDown(self):
        self.widget.close()
        # Cleanup any remaining files

        for f in self.test_files:
            p = os.path.join(self.test_dir, f)
            if os.path.exists(p):
                os.remove(p)

    def test_calculate_stats(self):
        # Mock DB returns
        self.mock_db.fetch_all.return_value = [{}, {}, {}] # 3 total
        self.mock_db.fetch_diarized_records.return_value = [
            {'filename': 'test_maint_1.wav'},
            {'filename': 'test_maint_2.wav'}
        ] # 2 diarized
        self.mock_db.fetch_pending_diarization.return_value = [{'id': 1}, {'id': 2}, {'id': 3}] # 3 pending
        
        # Determine size of standard test file
        test_file_size = os.path.getsize(os.path.join(self.test_dir, "test_maint_1.wav"))
        expected_size_mb = (test_file_size * 2) / (1024 * 1024)
        
        self.widget.calculate_stats()
        
        self.assertIn("Total Recordings: 3", self.widget.total_lbl.text())
        self.assertIn("Diarized Recordings: 2", self.widget.diarized_lbl.text())
        self.assertIn("Pending Diarization: 3", self.widget.pending_lbl.text())
        
        # Verify reclaimable files list
        self.assertEqual(len(self.widget.reclaimable_files), 2)
        self.assertTrue(any("test_maint_1.wav" in f for f in self.widget.reclaimable_files))
        self.assertTrue(any("test_maint_2.wav" in f for f in self.widget.reclaimable_files))
        self.assertFalse(any("test_maint_3.wav" in f for f in self.widget.reclaimable_files))

    def test_cleanup(self):
        # Setup dialog state manually
        self.widget.reclaimable_files = [
            os.path.join(self.test_dir, "test_maint_1.wav"),
            os.path.join(self.test_dir, "test_maint_2.wav")
        ]
        
        # Keep dialogs patched while we force the processing loop.
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=0x00004000), \
             patch('PyQt6.QtWidgets.QMessageBox.information') as _info_mock:
            self.widget.clean_up()
            while self.widget.files_to_delete:
                self.widget.process_next_file()
            # One extra tick to execute the "no pending files" branch and finish cleanup.
            self.widget.process_next_file()
            
        # Verify files are gone
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test_maint_1.wav")))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "test_maint_2.wav")))
        
        # Verify non-diarized file still exists
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "test_maint_3.wav")))

    def test_cleanup_finish_is_idempotent_with_manual_process_calls(self):
        self.widget.reclaimable_files = [
            os.path.join(self.test_dir, "test_maint_1.wav"),
        ]
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=0x00004000), \
             patch('PyQt6.QtWidgets.QMessageBox.information') as info_mock:
            self.widget.clean_up()
            # Manual invocations emulate old test behavior while timers are also queued.
            self.widget.process_next_file()
            self.widget.process_next_file()
            self.widget.process_next_file()

        self.assertEqual(info_mock.call_count, 1)

if __name__ == '__main__':
    unittest.main()
