"""Persistence and queue request helpers for transcription batches."""

import os


def transcription_request(record, *, recordings_dir, model):
    return {
        "record_id": record["id"],
        "file_path": os.path.join(recordings_dir, record["filename"]),
        "model_size": model,
        "language": None,
        "diarization": True,
        "title": record.get("filename") or f"Recording {record['id']}",
        "source": "batch_process",
    }


def pending_records(db):
    return db.fetch_pending_diarization()
