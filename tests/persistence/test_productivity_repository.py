from src.database import DBManager
import pytest


def test_pomodoro_completion_and_notes_are_idempotent_and_filterable(tmp_path):
    db = DBManager(str(tmp_path / "productivity.sqlite"))
    pomodoro_id = db.create_pomodoro("Write proposal", ["Work"], 1500, "2026-09-25T09:00:00+00:00")
    text_id = db.create_productivity_note("text", "Outline", ["Ideas"], body="Draft", pomodoro_id=pomodoro_id,
                                          captured_at="2026-09-25T09:05:00+00:00")
    audio_id = db.create_productivity_note("audio", "Voice thought", [],
                                           audio_ref=str(tmp_path / "thought.wav"),
                                           duration_seconds=12, pomodoro_id=pomodoro_id,
                                           captured_at="2026-09-25T09:06:00+00:00")
    db.complete_pomodoro(pomodoro_id, "2026-09-25T09:25:00+00:00", 1500, "completed")
    db.complete_pomodoro(pomodoro_id, "2026-09-25T09:25:00+00:00", 1500, "completed")

    assert db.fetch_pomodoro(pomodoro_id)["state"] == "completed"
    assert {note["id"] for note in db.fetch_productivity_notes(pomodoro_id)} == {text_id, audio_id}
    events = db.fetch_timeline(start_date="2026-09-25", end_date="2026-09-25", tag="Work")
    assert len(events) == 3
    assert {event["event_type"] for event in events} == {"pomodoro", "text_note", "audio_note"}
    assert len([event for event in events if event["event_type"] == "pomodoro"]) == 1


def test_cancel_keeps_saved_notes_but_no_completed_focus(tmp_path):
    db = DBManager(str(tmp_path / "cancel.sqlite"))
    pomodoro_id = db.create_pomodoro("Research", ["Work"], 1500, "2026-09-25T09:00:00+00:00")
    note_id = db.create_productivity_note("text", "Reference", [], body="Paper", pomodoro_id=pomodoro_id)
    db.cancel_pomodoro(pomodoro_id, "2026-09-25T09:03:00+00:00", 180)

    assert db.fetch_pomodoro(pomodoro_id)["state"] == "cancelled"
    assert db.fetch_productivity_note(note_id)["pomodoro_id"] is None
    assert [event["event_type"] for event in db.fetch_timeline()] == ["text_note"]


def test_schema_init_preserves_existing_productivity_data(tmp_path):
    path = str(tmp_path / "upgrade.sqlite")
    db = DBManager(path)
    pomodoro_id = db.create_pomodoro("Review", [], 1500)
    db.init_db()
    assert DBManager(path).fetch_pomodoro(pomodoro_id)["title"] == "Review"


def test_timeline_pages_in_sqlite_and_supports_future_event_types(tmp_path):
    db = DBManager(str(tmp_path / "pages.sqlite"))
    for index in range(55):
        db.create_productivity_note("text", f"Note {index}", ["Work"], body="body")
    db.upsert_timeline_event("meeting", 7, "2026-09-25T10:00:00+00:00", "Weekly sync", ["Work"])
    db.upsert_timeline_event("meeting", 7, "2026-09-25T10:00:00+00:00", "Weekly sync", ["Work"])

    first = db.fetch_timeline(tag="work", limit=50)
    second = db.fetch_timeline(tag="Work", limit=50, offset=50)
    assert len(first) == 50
    assert len(second) == 6
    assert {event["id"] for event in first}.isdisjoint({event["id"] for event in second})
    assert len([event for event in first + second if event["event_type"] == "meeting"]) == 1


def test_note_validation_rejects_empty_body_and_invalid_audio_duration(tmp_path):
    db = DBManager(str(tmp_path / "validation.sqlite"))
    with pytest.raises(ValueError, match="body"):
        db.create_productivity_note("text", "Empty", [], body="  ")
    with pytest.raises(ValueError, match="audio"):
        db.create_productivity_note("audio", "Silent", [],
                                    audio_ref=str(tmp_path / "silent.wav"), duration_seconds=0)
    assert db.fetch_timeline() == []


def test_deleting_note_removes_timeline_reference(tmp_path):
    db = DBManager(str(tmp_path / "delete.sqlite"))
    note_id = db.create_productivity_note("text", "Temporary", [], body="One thought")
    assert db.delete_productivity_note(note_id) is None
    assert db.fetch_productivity_note(note_id) is None
    assert db.fetch_timeline() == []


def test_deleting_completed_pomodoro_keeps_notes_as_standalone_history(tmp_path):
    db = DBManager(str(tmp_path / "delete-focus.sqlite"))
    pomodoro_id = db.create_pomodoro("Draft", ["Work"], 1500)
    note_id = db.create_productivity_note("text", "Idea", ["Ideas"], body="Keep this", pomodoro_id=pomodoro_id)
    db.complete_pomodoro(pomodoro_id, "2026-09-25T09:25:00+00:00", 1500, "completed")

    assert db.delete_pomodoro(pomodoro_id)
    assert db.fetch_pomodoro(pomodoro_id) is None
    assert db.fetch_productivity_note(note_id)["pomodoro_id"] is None
    assert [event["event_type"] for event in db.fetch_timeline()] == ["text_note"]
    assert db.fetch_timeline()[0]["parent_source_id"] is None


def test_productivity_only_tags_are_available_to_global_selector(tmp_path):
    db = DBManager(str(tmp_path / "tags.sqlite"))
    db.create_productivity_note("text", "Today", ["Ideas"], body="a",
                                captured_at="2026-09-25T10:00:00+00:00")
    db.create_productivity_note("text", "Yesterday", ["Personal"], body="b",
                                captured_at="2026-09-24T10:00:00+00:00")
    assert db.get_productivity_tags("2026-09-25", "2026-09-25") == ["Ideas"]
    assert db.get_productivity_tags() == ["Ideas", "Personal"]
