from pathlib import Path

from src.database import DBManager
from src.ui.main_window.setup_actions import SetupActionsCoordinator


class _RecordingTab:
    def __init__(self):
        self.transcription_requests = []

    def start_transcription_with_config(self, path, config):
        self.transcription_requests.append((path, config))


class _ImportWindow:
    def __init__(self, db):
        self.db = db
        self.opened = []
        self.recording_tab = _RecordingTab()

    def open_recording_tab(self, record_id, config):
        self.opened.append((record_id, config))
        return self.recording_tab


def test_drag_drop_import_copies_audio_persists_record_and_starts_transcription(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "incoming" / "interview.m4a"
    source.parent.mkdir()
    source.write_bytes(b"deterministic audio")
    db = DBManager(str(tmp_path / "records.sqlite"))
    window = _ImportWindow(db)

    record_id = SetupActionsCoordinator(window).import_audio_path(
        str(source), config={"mode": "fast"}
    )

    destination = tmp_path / "recordings" / "interview.m4a"
    assert record_id is not None
    assert destination.read_bytes() == source.read_bytes()
    record = db.fetch_record(record_id)
    assert record["filename"] == "interview.m4a"
    assert window.opened == [(record_id, {"mode": "fast"})]
    assert window.recording_tab.transcription_requests == [
        (str(destination), {"mode": "fast"})
    ]
