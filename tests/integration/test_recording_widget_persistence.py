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
