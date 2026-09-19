from src.database import DBManager
from src.persistence.base import PersistenceBase
from src.persistence import (
    ChatSessionsRepository,
    QueueJobsRepository,
    RAGIndexRepository,
    RecordsRepository,
    SummariesRepository,
    TasksRepository,
    TranscriptionLogsRepository,
)


def test_db_manager_instantiates_aggregate_repositories_with_shared_database(tmp_path):
    db = DBManager(str(tmp_path / "facade.sqlite"))

    assert DBManager.__bases__ == (PersistenceBase,)

    expected_repositories = {
        "records": RecordsRepository,
        "chat_sessions": ChatSessionsRepository,
        "transcription_logs": TranscriptionLogsRepository,
        "summaries": SummariesRepository,
        "tasks": TasksRepository,
        "rag_index": RAGIndexRepository,
        "queue_jobs": QueueJobsRepository,
    }

    for attribute, repository_type in expected_repositories.items():
        repository = getattr(db, attribute)
        assert isinstance(repository, repository_type)
        assert repository.db_name == db.db_name

    db.init_db()


def test_db_manager_delegates_to_the_aggregate_that_owns_the_operation(tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "facade.sqlite"))
    calls = []

    monkeypatch.setattr(db.records, "fetch_record", lambda record_id: calls.append(record_id) or {"id": record_id})

    assert db.fetch_record(17) == {"id": 17}
    assert calls == [17]
