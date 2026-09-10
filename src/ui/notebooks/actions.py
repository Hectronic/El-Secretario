"""Persistence and file actions initiated from a notebook view."""

import logging
import os


def add_text_entry(db, notebook_id, content):
    return db.add_text_entry(notebook_id, content.strip())


def apply_transcription_result(db, entry_id, result):
    db.update_entry_content(entry_id, result.get("text", ""))


def apply_transcription_error(db, entry_id, error):
    db.update_entry_content(entry_id, f"Transcription Failed: {error}")


def rename_entry(db, entry_id, title):
    db.rename_entry(entry_id, title.strip())


def delete_entry_and_audio(db, entry_id):
    file_path = db.delete_entry(entry_id)
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            logging.exception("Failed deleting notebook audio file: %s", file_path)
    return file_path
