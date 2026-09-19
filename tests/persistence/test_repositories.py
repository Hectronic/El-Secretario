from src.persistence import (
    ChatSessionsRepository,
    QueueJobsRepository,
    RAGIndexRepository,
    RecordsRepository,
    SummariesRepository,
    TasksRepository,
    TranscriptionLogsRepository,
)


def test_recording_and_task_repositories_share_schema_without_a_facade(tmp_path):
    database = tmp_path / "repositories.sqlite"
    records = RecordsRepository(database)
    tasks = TasksRepository(database)

    record_id = records.save("meeting.wav", "Transcript", 12.0, title="Planning")
    task_id = tasks.save_task(record_id, "Send summary")

    assert records.fetch_record(record_id)["title"] == "Planning"
    assert tasks.get_tasks_by_record(record_id)[0]["id"] == task_id


def test_supporting_repositories_persist_their_owned_aggregates(tmp_path):
    database = tmp_path / "repositories.sqlite"
    chats = ChatSessionsRepository(database)
    logs = TranscriptionLogsRepository(database)
    summaries = SummariesRepository(database)
    rag = RAGIndexRepository(database)
    queue = QueueJobsRepository(database)

    session_id = chats.save_chat_session("Daily", "", "[]")
    logs.log_transcription("tiny", 2.0, 32, 0.3, None)
    summaries.save_daily_summary("2026-09-19", "Done")
    rag.upsert_rag_index_status("recording:1", "abc", "ready")
    queue.save_queue_jobs([{"type": "daily_summary", "status": "pending"}])

    assert chats.fetch_chat_sessions()[0]["id"] == session_id
    assert logs.fetch_transcription_logs()[0]["model_name"] == "tiny"
    assert summaries.get_daily_summary("2026-09-19") == "Done"
    assert rag.get_rag_index_status("recording:1")["status"] == "ready"
    assert queue.load_queue_jobs() == [{"type": "daily_summary", "status": "pending"}]
