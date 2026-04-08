import json

import pytest

from src.data_export import DataExporter
from src.database import DBManager
from src.notebook_database import NotebookDBManager


@pytest.fixture
def exporter(tmp_path):
    db = DBManager(db_name=str(tmp_path / "export_logs.sqlite"))
    notebook_db = NotebookDBManager(db_name=str(tmp_path / "export_logs_notebooks.sqlite"))
    return DataExporter(db, notebook_db)


def test_export_transcription_logs_returns_rows_in_reverse_chronological_order(exporter):
    with exporter.db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO transcription_logs (
                created_at, model_name, audio_duration, audio_size_bytes,
                transcription_time_seconds, record_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-01 10:00:00", "base", 10.0, 1024, 1.25, 11),
        )
        conn.execute(
            """
            INSERT INTO transcription_logs (
                created_at, model_name, audio_duration, audio_size_bytes,
                transcription_time_seconds, record_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-02 10:00:00", "large-v3", 20.0, 2048, 2.5, 22),
        )
        conn.commit()

    logs = exporter.export_transcription_logs()

    assert len(logs) == 2
    assert [log["created_at"] for log in logs] == [
        "2026-04-02 10:00:00",
        "2026-04-01 10:00:00",
    ]
    assert logs[0]["model_name"] == "large-v3"
    assert logs[0]["audio_duration"] == 20.0
    assert logs[0]["audio_size_bytes"] == 2048
    assert logs[0]["transcription_time_seconds"] == 2.5
    assert logs[0]["record_id"] == 22


def test_export_all_includes_transcription_logs(exporter, tmp_path):
    exporter.db.save("rec.wav", "Transcription", 9.5, "Recording")
    with exporter.db.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO transcription_logs (
                created_at, model_name, audio_duration, audio_size_bytes,
                transcription_time_seconds, record_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("2026-04-03 12:00:00", "base", 9.5, 4096, 3.75, 1),
        )
        conn.commit()

    output_path = tmp_path / "export.json"
    stats = exporter.export_all(str(output_path))

    assert stats["records_count"] == 1
    assert stats["transcription_logs_count"] == 1

    with output_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data["transcription_logs"]) == 1
    assert data["transcription_logs"][0]["model_name"] == "base"
    assert data["transcription_logs"][0]["record_id"] == 1
