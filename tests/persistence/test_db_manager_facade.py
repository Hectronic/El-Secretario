from src.database import DBManager
from src.persistence import (
    ChatSessionsRepository,
    RecordsRepository,
    SummariesRepository,
    TasksRepository,
    TranscriptionLogsRepository,
)


def test_db_manager_keeps_the_established_public_api_through_repositories():
    """Existing callers keep using DBManager while each aggregate owns its code."""
    expected_methods = {
        RecordsRepository: (
            "save",
            "fetch_all",
            "fetch_record",
            "update_title",
            "delete",
            "import_record",
        ),
        ChatSessionsRepository: (
            "save_chat_session",
            "fetch_chat_sessions",
            "update_chat_session",
            "delete_chat_session",
            "import_chat_session",
        ),
        TranscriptionLogsRepository: ("log_transcription", "fetch_transcription_logs"),
        SummariesRepository: (
            "save_daily_summary",
            "get_daily_summary",
            "save_weekly_summary",
            "get_weekly_summary",
        ),
        TasksRepository: (
            "save_task",
            "get_tasks_by_date",
            "get_tasks_for_board",
            "toggle_task_completion",
        ),
    }

    for repository, method_names in expected_methods.items():
        for method_name in method_names:
            assert getattr(DBManager, method_name) is getattr(repository, method_name)
