import gc
import os
import sqlite3
import time
from datetime import date

from src.database import DBManager

from ._database_case import DatabaseRepositoryTestCase


class TestRecordsRepository(DatabaseRepositoryTestCase):
    def test_save_and_fetch(self):
        self.db.save('test.wav', 'Transcription', 10.0, 'Title')
        records = self.db.fetch_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['title'], 'Title')
        self.assertEqual(records[0]['transcription'], 'Transcription')

    def test_update_methods(self):
        self.db.save('test.wav', 'Transcription', 10.0)
        records = self.db.fetch_all()
        record_id = records[0]['id']
        self.db.update_title(record_id, 'New Title')
        self.db.update_transcription(record_id, 'New Text')
        self.db.update_tags(record_id, 'tag1, tag2')
        self.db.update_ai_content(record_id, summary='Summary', cleaned_text='Cleaned')
        updated_record = self.db.fetch_all()[0]
        self.assertEqual(updated_record['title'], 'New Title')
        self.assertEqual(updated_record['transcription'], 'New Text')
        self.assertEqual(updated_record['tags'], 'tag1, tag2')
        self.assertEqual(updated_record['summary'], 'Summary')
        self.assertEqual(updated_record['cleaned_text'], 'Cleaned')

    def test_recording_notes_are_persisted_and_composed_for_ai(self):
        record_id = self.db.save('test.wav', 'Meeting transcription', 10.0, 'Title')
        self.db.update_recording_notes(record_id, 'Remember to send proposal.')
        record = self.db.fetch_record(record_id)
        self.assertEqual(record['recording_notes'], 'Remember to send proposal.')
        ai_text = self.db.get_record_ai_text(record_id)
        self.assertIn('Meeting transcription', ai_text)
        self.assertIn('Remember to send proposal.', ai_text)

    def test_records_with_only_notes_are_detected_as_content(self):
        record_id = self.db.save('test.wav', '', 10.0, 'Title', recording_notes='Only notes')
        dates = self.db.get_dates_with_content()
        self.assertTrue(len(dates) >= 1)
        pending_no_summary = self.db.get_records_without_summary()
        ids = [r['id'] for r in pending_no_summary]
        self.assertIn(record_id, ids)
