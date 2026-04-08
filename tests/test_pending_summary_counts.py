import pytest
from unittest.mock import MagicMock

from src.summary_generator import get_pending_summary_counts


@pytest.fixture
def fake_db(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr("src.summary_generator.DBManager", lambda: db)
    return db


def test_get_pending_summary_counts_returns_lengths_without_filter(fake_db):
    fake_db.get_dates_without_summary.return_value = [
        "2026-04-01",
        "2026-04-02",
        "2026-04-03",
    ]
    fake_db.get_weeks_without_summary.return_value = [
        "2026-04-06",
    ]

    assert get_pending_summary_counts() == (3, 1)
    fake_db.get_dates_without_summary.assert_called_once_with(None)
    fake_db.get_weeks_without_summary.assert_called_once_with(None)


def test_get_pending_summary_counts_forwards_tags_filter(fake_db):
    fake_db.get_dates_without_summary.return_value = [
        "2026-04-01",
    ]
    fake_db.get_weeks_without_summary.return_value = [
        "2026-04-06",
        "2026-04-13",
    ]

    assert get_pending_summary_counts("Trabajo") == (1, 2)
    fake_db.get_dates_without_summary.assert_called_once_with("Trabajo")
    fake_db.get_weeks_without_summary.assert_called_once_with("Trabajo")


def test_get_pending_summary_counts_handles_empty_database(fake_db):
    fake_db.get_dates_without_summary.return_value = []
    fake_db.get_weeks_without_summary.return_value = []

    assert get_pending_summary_counts(tags_filter=None) == (0, 0)
