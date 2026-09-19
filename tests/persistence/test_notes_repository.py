from src.persistence import RecordsRepository


def test_records_repository_saves_a_note(tmp_path):
    repository = RecordsRepository(tmp_path / "notes.sqlite")

    note_id = repository.save_note("My Note", "Content of the note", "tag1")

    record = repository.fetch_record(note_id)
    assert record["title"] == "My Note"
    assert record["transcription"] == "Content of the note"
    assert record["type"] == "note"
    assert record["duration"] == 0.0
