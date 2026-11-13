from src.database import DBManager
from src.app.summary_queue.completion import handle_worker_completion
from src.ui.recording_widget import RecordingWidget
from src.ui.settings.diarization_check import DiarizationCheckWidget
from src.worker_components.diarization_diagnostics import DiarizationDiagnosis
from PyQt6.QtWidgets import QLineEdit, QWidget


def test_failed_batch_preserves_existing_transcript_and_warning_survives_reload(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "recordings.sqlite"))
    record_id = db.save("meeting.wav", "Original transcript", 5, is_diarized=True)
    result = {"text": "New unlabelled text", "is_diarized": False, "model_name": "base",
              "diarization_warning": "Check your token in Settings."}
    actions = handle_worker_completion(db, {"type": "transcription", "record_id": record_id,
                                             "source": "batch_process"}, result)
    record = db.fetch_record(record_id)
    assert actions == []
    assert record["transcription"] == "Original transcript"
    assert record["is_diarized"] == 1
    widget = RecordingWidget(rag_engine=None, record_id=record_id, persistence=db)
    qtbot.addWidget(widget)
    assert "Check your token" in widget.diarization_warning_label.text()
    requests = []
    widget.settings_requested.connect(lambda: requests.append(True))
    widget.diarization_settings_button.click()
    assert requests == [True]


def test_failed_first_transcription_is_saved_as_not_diarized(tmp_path):
    db = DBManager(str(tmp_path / "records.sqlite"))
    record_id = db.save("meeting.wav", "", 5)
    handle_worker_completion(db, {"type": "transcription", "record_id": record_id, "source": "batch_process"},
                             {"text": "Recognized", "is_diarized": False, "model_name": "base",
                              "diarization_warning": "Token required"})
    record = db.fetch_record(record_id)
    assert record["transcription"] == "Recognized"
    assert record["is_diarized"] == 0
    assert record["diarization_warning"] == "Token required"


def test_settings_check_uses_edited_token_and_invalidates_stale_result(qtbot, monkeypatch):
    monkeypatch.setattr("src.ui.settings.diarization_check.check_diarization",
                        lambda token, **_: DiarizationDiagnosis("available", "Checked " + token[-1:], "now"))
    field = QWidget()
    token = QLineEdit("old")
    widget = DiarizationCheckWidget(field, token)
    qtbot.addWidget(widget)
    widget.check_button.click()
    qtbot.waitUntil(lambda: "Checked d" in widget.status_label.text(), timeout=3000)
    token.setText("new")
    assert "not checked" in widget.status_label.text().lower()
    widget._completed(widget._generation - 1, DiarizationDiagnosis("available", "stale", "now"))
    assert "stale" not in widget.status_label.text()


def test_queue_real_worker_keeps_going_after_diarization_failure(qtbot, monkeypatch, tmp_path):
    from src.ui.summary_queue.manager import SummaryTaskQueueManager

    class Settings:
        def value(self, key, default=None, type=None):
            return {"hf_token": "", "force_cpu": True}.get(key, default)

    monkeypatch.setattr("src.ui.summary_queue.worker_runtime.QSettings", lambda *_: Settings())
    monkeypatch.setattr("src.worker_components.transcriber_thread._run_transcription_in_subprocess",
                        lambda **_: [{"start": 0, "end": 1, "text": "Recognized"}])
    monkeypatch.setattr("src.app.summary_queue.workers.read_audio_duration_seconds", lambda _: 1.0)
    db = DBManager(str(tmp_path / "queue.sqlite"))
    first = db.save("one.wav", "", 1)
    second = db.save("two.wav", "", 1)
    paths = [tmp_path / "one.wav", tmp_path / "two.wav"]
    for path in paths:
        path.write_bytes(b"audio")
    queue = SummaryTaskQueueManager(persistence=db)
    try:
        assert queue.enqueue_transcription(first, str(paths[0]), diarization=True, source="batch_process")
        assert queue.enqueue_transcription(second, str(paths[1]), diarization=False, source="batch_process")
        qtbot.waitUntil(lambda: not queue.is_running and queue.pending_count == 0, timeout=10000)
        assert db.fetch_record(first)["diarization_warning"]
        assert db.fetch_record(first)["is_diarized"] == 0
        assert db.fetch_record(second)["transcription"] == "Recognized"
        assert any(entry["event"] == "warning" for entry in queue.get_session_history())
    finally:
        queue.cancel_all()


def test_direct_worker_failure_keeps_existing_record_and_shows_warning(qtbot, monkeypatch, tmp_path):
    from PyQt6.QtCore import QSettings

    monkeypatch.setattr("src.worker_components.transcriber_thread._run_transcription_in_subprocess",
                        lambda **_: [{"start": 0, "end": 1, "text": "New text"}])
    monkeypatch.setattr("src.ui.recording_widget.get_transcription_preflight_error", lambda *_: None)
    settings = QSettings("Hectronic", "Secretario")
    settings.setValue("hf_token", "")
    settings.setValue("force_cpu", True)
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    db = DBManager(str(tmp_path / "direct.sqlite"))
    record_id = db.save("audio.wav", "Existing text", 1, is_diarized=True)
    widget = RecordingWidget(rag_engine=None, record_id=record_id, persistence=db)
    qtbot.addWidget(widget)
    with qtbot.waitSignal(widget.recording_saved, timeout=10000):
        worker = widget.start_transcription_with_config(str(audio), {"diarization": True})
        assert worker is not None
    assert db.fetch_record(record_id)["transcription"] == "Existing text"
    assert db.fetch_record(record_id)["is_diarized"] == 1
    assert "token" in widget.diarization_warning_label.text().lower()
    assert widget.text_display.toPlainText() == "Existing text"


def test_cancel_check_ignores_late_result(qtbot, monkeypatch):
    import threading
    entered = threading.Event()
    release = threading.Event()
    def slow_check(token, **kwargs):
        entered.set()
        release.wait(2)
        return DiarizationDiagnosis("available", "late success", "now")
    monkeypatch.setattr("src.ui.settings.diarization_check.check_diarization", slow_check)
    widget = DiarizationCheckWidget(QWidget(), QLineEdit("token"))
    qtbot.addWidget(widget)
    widget.check_button.click()
    qtbot.waitUntil(entered.is_set, timeout=3000)
    widget.cancel_button.click()
    release.set()
    qtbot.waitUntil(lambda: not widget._checks, timeout=3000)
    assert "cancelled" in widget.status_label.text().lower()
    assert "late success" not in widget.status_label.text()
