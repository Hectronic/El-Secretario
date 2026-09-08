from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from src.database import DBManager
from src.ui.recording_widget import RecordingWidget


def test_recording_widget_uses_injected_sqlite_for_chat_context(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "recording-widget.sqlite"))
    record_id = db.save("planning.wav", "Transcript", 12.0, "Planning review")
    widget = RecordingWidget(rag_engine=None, record_id=record_id, persistence=db)
    qtbot.addWidget(widget)
    contexts = []
    widget.start_chat_requested.connect(contexts.append)

    widget.open_chat_for_recording()

    assert contexts == [[{"type": "recording", "value": record_id, "label": "Planning review"}]]
    assert widget.db is db


def test_recording_widget_deletion_removes_sqlite_file_and_rag_document(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "recording-delete.sqlite"))
    record_id = db.save("delete-me.wav", "Transcript", 12.0, "Delete me")
    recordings_dir = tmp_path / "recordings"
    recordings_dir.mkdir()
    audio_file = recordings_dir / "delete-me.wav"
    audio_file.write_bytes(b"audio")
    monkeypatch.chdir(tmp_path)

    class Rag:
        def __init__(self):
            self.deleted = []

        def delete_document(self, document_id):
            self.deleted.append(document_id)

    rag = Rag()
    widget = RecordingWidget(rag_engine=rag, record_id=record_id, persistence=db)
    qtbot.addWidget(widget)
    deleted_ids = []
    widget.recording_deleted.connect(deleted_ids.append)

    with patch(
        "src.ui.recording.record_actions.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        widget.delete_recording()

    assert db.fetch_record(record_id) is None
    assert not audio_file.exists()
    assert rag.deleted == [str(record_id)]
    assert deleted_ids == [record_id]
