# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from src.database import DBManager
from src.ui.queue_management_widget import QueueManagementWidget
from src.ui.summary_task_queue import SummaryTaskQueueManager


class _FakeAIAssistantThread(QThread):
    task_completed = pyqtSignal(str, str)
    status_update = pyqtSignal(str)
    retry_wait = pyqtSignal(float, int, int, str)
    error = pyqtSignal(str)

    def __init__(self, _api_key, task_type, text):
        super().__init__()
        self.task_type = task_type
        self.text = text

    def run(self):
        self.status_update.emit(f"{self.task_type}: started")
        if self.task_type == "summary":
            self.task_completed.emit(self.task_type, "Generated summary")
        elif self.task_type == "task_extraction":
            self.task_completed.emit(self.task_type, '["Follow up", "Send notes"]')
        elif self.task_type == "weekly_summary":
            self.task_completed.emit(self.task_type, "Weekly summary")
        else:
            self.task_completed.emit(self.task_type, "Done")


class _FakeTranscriberThread(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_path, **kwargs):
        super().__init__()
        self.audio_path = audio_path
        self.kwargs = kwargs

    def run(self):
        self.status_update.emit("Fake transcription running")
        self.progress.emit(25)
        self.msleep(80)
        self.progress.emit(100)
        self.finished.emit(
            {
                "text": "Recognized speech",
                "model_name": self.kwargs.get("model_size", "base"),
                "is_diarized": bool(self.kwargs.get("enable_diarization")),
            }
        )


class _FailThenSucceedTranscriberThread(QThread):
    finished = pyqtSignal(object)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    error = pyqtSignal(str)

    _instances_started = 0

    def __init__(self, audio_path, **kwargs):
        super().__init__()
        self.audio_path = audio_path
        self.kwargs = kwargs
        self.instance_index = type(self)._instances_started
        type(self)._instances_started += 1

    def run(self):
        self.status_update.emit(f"Transcriber {self.instance_index}: started")
        if self.instance_index == 0:
            self.error.emit("Transcription subprocess timed out.")
            self.finished.emit(None)
            return
        self.progress.emit(100)
        self.finished.emit(
            {
                "text": "Recovered transcription",
                "model_name": self.kwargs.get("model_size", "base"),
                "is_diarized": bool(self.kwargs.get("enable_diarization")),
            }
        )


class _FakeSettings:
    def value(self, key, default=None, type=None):
        values = {
            "hf_token": "",
            "force_cpu": False,
            "compute_type": "auto",
            "transcription_backend": "auto",
        }
        return values.get(key, default)


class _FakeRagEngine:
    def __init__(self):
        self.indexed = []

    def add_document(self, record_id, text, metadata=None):
        self.indexed.append((record_id, text, dict(metadata or {})))

    def search(self, *_args, **_kwargs):
        return []


def _queue_with_temp_db(monkeypatch, tmp_path):
    db = DBManager(str(tmp_path / "queue.sqlite"))
    monkeypatch.setattr("src.ui.summary_task_queue.DBManager", lambda: db)
    queue = SummaryTaskQueueManager()
    return queue, db


def test_queue_e2e_summary_chains_task_extraction_and_persists(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr("src.ui.summary_task_queue.AIAssistant", _FakeAIAssistantThread)
    queue, db = _queue_with_temp_db(monkeypatch, tmp_path)

    record_id = db.save("meeting.wav", "Transcript", 10.0, "Planning")
    db.update_tags(record_id, "work")
    statuses = []
    queue.task_status_update.connect(statuses.append)

    try:
        assert queue.enqueue_recording_summary(record_id, "Transcript", "Planning")
        qtbot.waitUntil(
            lambda: (
                not queue.is_running
                and queue.pending_count == 0
                and len(db.get_tasks_by_record(record_id)) == 2
            ),
            timeout=3000,
        )

        record = db.fetch_record(record_id)
        tasks = db.get_tasks_by_record(record_id)
        history_events = [entry["event"] for entry in queue.get_session_history()]

        assert record["summary"] == "Generated summary"
        assert [task["content"] for task in tasks] == ["Follow up", "Send notes"]
        assert "summary: started" in statuses
        assert "task_extraction: started" in statuses
        assert history_events.count("finished") >= 2
    finally:
        queue.cancel_all()


def test_queue_component_transcription_updates_widget_and_database(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr("src.ui.summary_task_queue.TranscriberThread", _FakeTranscriberThread)
    monkeypatch.setattr("src.ui.summary_task_queue.QSettings", lambda *_args: _FakeSettings())
    monkeypatch.setattr("src.ui.summary_task_queue._read_audio_duration_seconds", lambda _path: 12.5)
    queue, db = _queue_with_temp_db(monkeypatch, tmp_path)
    widget = QueueManagementWidget(queue)
    qtbot.addWidget(widget)

    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"fake audio")
    record_id = db.save(str(audio_path), "", 0.0, "Queued audio")

    try:
        assert queue.enqueue_transcription(
            record_id,
            str(audio_path),
            model_size="base",
            language="es",
            diarization=True,
            title="Queued audio",
            source="batch_process",
        )
        qtbot.waitUntil(
            lambda: "Fake transcription running" in widget.live_status_label.text(),
            timeout=3000,
        )
        assert widget.live_progress.value() == 25

        qtbot.waitUntil(lambda: not queue.is_running and queue.pending_count == 0, timeout=3000)
        record = db.fetch_record(record_id)

        assert record["transcription"] == "Recognized speech"
        assert record["transcription_model"] == "base"
        assert record["is_diarized"] == 1
        assert widget.queue_list.count() == 0
        assert "None" in widget.current_task_label.text()
    finally:
        queue.cancel_all()


def test_queue_component_skips_fatal_transcription_and_continues(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr("src.ui.summary_task_queue.TranscriberThread", _FailThenSucceedTranscriberThread)
    monkeypatch.setattr("src.ui.summary_task_queue.QSettings", lambda *_args: _FakeSettings())
    monkeypatch.setattr("src.app.summary_queue.workers.read_audio_duration_seconds", lambda _path: 12.5)
    _FailThenSucceedTranscriberThread._instances_started = 0
    queue, db = _queue_with_temp_db(monkeypatch, tmp_path)
    widget = QueueManagementWidget(queue)
    qtbot.addWidget(widget)

    audio_path_1 = tmp_path / "audio1.wav"
    audio_path_1.write_bytes(b"fake audio 1")
    record_id_1 = db.save(str(audio_path_1), "", 0.0, "Broken audio")

    audio_path_2 = tmp_path / "audio2.wav"
    audio_path_2.write_bytes(b"fake audio 2")
    record_id_2 = db.save(str(audio_path_2), "", 0.0, "Recovered audio")

    skipped_events = []
    failed_events = []
    queue.task_skipped.connect(lambda task, reason: skipped_events.append((task, reason)))
    queue.task_failed.connect(lambda task, reason: failed_events.append((task, reason)))

    try:
        assert queue.enqueue_transcription(
            record_id_1,
            str(audio_path_1),
            model_size="base",
            language="es",
            diarization=True,
            title="Broken audio",
            source="batch_process",
        )
        assert queue.enqueue_transcription(
            record_id_2,
            str(audio_path_2),
            model_size="base",
            language="es",
            diarization=True,
            title="Recovered audio",
            source="batch_process",
        )

        qtbot.waitUntil(lambda: not queue.is_running and queue.pending_count == 0, timeout=3000)

        assert any(entry[1].startswith("Transcription subprocess timed out") for entry in skipped_events)
        assert not failed_events
        assert db.fetch_record(record_id_1)["transcription"] == ""
        assert db.fetch_record(record_id_2)["transcription"] == "Recovered transcription"
        assert any("Skipped" in widget.history_list.item(i).text() for i in range(widget.history_list.count()))
    finally:
        queue.cancel_all()


def test_queue_e2e_rag_reindex_uses_real_worker_thread(qtbot, monkeypatch, tmp_path):
    queue, db = _queue_with_temp_db(monkeypatch, tmp_path)
    rag = _FakeRagEngine()
    queue.set_rag_engine(rag)
    record_id = db.save("rec.wav", "Indexed text", 5.0, "Indexed record")
    db.update_tags(record_id, "tag-a")
    statuses = []
    progress = []
    queue.task_status_update.connect(statuses.append)
    queue.task_progress.connect(progress.append)

    try:
        assert queue.enqueue_rag_reindex(scope="all", source="test")
        qtbot.waitUntil(lambda: not queue.is_running and queue.pending_count == 0, timeout=3000)

        assert len(rag.indexed) == 1
        indexed_id, indexed_text, metadata = rag.indexed[0]
        assert indexed_id == record_id
        assert indexed_text == "Indexed text"
        assert metadata["title"] == "Indexed record"
        assert metadata["tags"] == "tag-a"
        assert 100 in progress
        assert any("RAG reindex (all records) completed" in status for status in statuses)
    finally:
        queue.cancel_all()
