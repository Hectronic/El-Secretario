import hashlib

from src.database import DBManager


def _set_created_at(db: DBManager, record_id: int, created_at: str) -> None:
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE records SET created_at = ? WHERE id = ?",
            (created_at, record_id),
        )
        conn.commit()


def test_record_exists_by_hash_matches_transcription_and_notes(tmp_path):
    db = DBManager(str(tmp_path / "records.sqlite"))
    created_at = "2026-03-01 09:15:00"

    record_id = db.save(
        "meeting.wav",
        "Transcription body",
        12.3,
        "Meeting",
        recording_notes="Some notes",
    )
    _set_created_at(db, record_id, created_at)

    combined_text = db.compose_ai_text("Transcription body", "Some notes")
    content_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()

    assert db.record_exists_by_hash(created_at, content_hash) is True


def test_record_exists_by_hash_requires_matching_created_at(tmp_path):
    db = DBManager(str(tmp_path / "records.sqlite"))

    record_id = db.save(
        "meeting.wav",
        "Transcription body",
        12.3,
        "Meeting",
        recording_notes="Some notes",
    )
    _set_created_at(db, record_id, "2026-03-01 09:15:00")

    combined_text = db.compose_ai_text("Transcription body", "Some notes")
    content_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()

    assert db.record_exists_by_hash("2026-03-01 09:15:01", content_hash) is False

