import pytest

from src.database import DBManager


@pytest.fixture
def db_manager(tmp_path):
    db_file = tmp_path / "test_daily_summary_details.sqlite"
    return DBManager(db_name=str(db_file))


def test_get_daily_summary_details_returns_complete_row_without_tags(db_manager):
    db_manager.save_daily_summary("2026-04-01", "Resumen general")

    details = db_manager.get_daily_summary_details("2026-04-01")

    assert details is not None
    assert details["date"] == "2026-04-01"
    assert details["summary"] == "Resumen general"
    assert details["tags_filter"] == ""
    assert details["generated_at"] == "2026-04-01 23:59:59"
    assert details["updated_at"] == "2026-04-01 23:59:59"


def test_get_daily_summary_details_uses_tags_filter_as_part_of_lookup(db_manager):
    db_manager.save_daily_summary("2026-04-01", "Resumen general")
    db_manager.save_daily_summary("2026-04-01", "Resumen trabajo", tags_filter="Trabajo")

    general = db_manager.get_daily_summary_details("2026-04-01")
    work = db_manager.get_daily_summary_details("2026-04-01", tags_filter="Trabajo")

    assert general is not None
    assert general["summary"] == "Resumen general"
    assert general["tags_filter"] == ""

    assert work is not None
    assert work["summary"] == "Resumen trabajo"
    assert work["tags_filter"] == "Trabajo"
    assert work["date"] == "2026-04-01"


def test_get_daily_summary_details_returns_none_when_missing(db_manager):
    assert db_manager.get_daily_summary_details("2026-04-01") is None
