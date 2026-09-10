"""Persistence and queue request helpers for transcription batches."""

import ntpath
import posixpath


def transcription_request(record, *, recordings_dir, model):
    """Build a queue payload without rewriting the caller's path convention."""
    path_join = ntpath.join if "\\" in recordings_dir or ":" in recordings_dir else posixpath.join
    return {
        "record_id": record["id"],
        "file_path": path_join(recordings_dir, record["filename"]),
        "model_size": model,
        "language": None,
        "diarization": True,
        "title": record.get("filename") or f"Recording {record['id']}",
        "source": "batch_process",
    }


def pending_records(db):
    return db.fetch_pending_diarization()
