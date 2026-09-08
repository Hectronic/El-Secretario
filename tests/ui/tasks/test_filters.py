from datetime import date

from PyQt6.QtCore import QDate

from src.ui.tasks.filters import (
    resolve_effective_tags_filter,
    resolve_global_date_range,
    task_matches_tag,
)


def test_global_date_range_normalizes_qdate_python_date_and_string():
    assert resolve_global_date_range(QDate(2026, 3, 2), None) == ("2026-03-02", "2026-03-08")
    assert resolve_global_date_range(date(2026, 3, 2), None) == ("2026-03-02", "2026-03-08")
    assert resolve_global_date_range("2026-03-02", "2026-03-05") == (
        "2026-03-02",
        "2026-03-05",
    )


def test_global_and_snapshot_context_take_precedence_over_local_tag():
    assert resolve_effective_tags_filter(
        snapshot_mode=None,
        global_start_date="2026-03-02",
        global_end_date="2026-03-08",
        global_tags_filter="planning",
        local_tag="ops",
    ) == "planning"
    assert resolve_effective_tags_filter(
        snapshot_mode="day_created",
        global_start_date=None,
        global_end_date=None,
        global_tags_filter="planning",
        local_tag="ops",
    ) == "planning"


def test_task_tag_matching_uses_record_tags_for_record_tasks():
    assert task_matches_tag({"record_id": 3, "record_tags": "planning, ops"}, "ops")
    assert not task_matches_tag({"record_id": 3, "record_tags": "planning"}, "ops")
