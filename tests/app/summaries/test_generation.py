from unittest.mock import MagicMock

from src.app.summaries import SummaryGenerationOptions, SummaryGenerationService


def _service(db, *, now=lambda: __import__("datetime").datetime(2026, 9, 10)):
    settings = MagicMock()
    settings.value.side_effect = lambda _key, default=None: default
    return SummaryGenerationService(db, settings, object(), MagicMock(return_value="summary"), now=now)


def test_generation_service_plans_specific_dates_and_week_dates_without_qt():
    db = MagicMock()
    service = _service(db)
    options = SummaryGenerationOptions(
        generate_weekly=False,
        specific_dates=["2026-09-08", "2026-09-09", "2026-09-08"],
    )

    assert service._dates_to_process(options) == ["2026-09-09", "2026-09-08"]
    assert service.week_dates("2026-09-13") == [
        "2026-09-07", "2026-09-08", "2026-09-09", "2026-09-10",
        "2026-09-11", "2026-09-12", "2026-09-13",
    ]
    db.get_dates_with_content.assert_not_called()


def test_generation_service_stops_before_work_when_cancelled():
    db = MagicMock()
    db.get_dates_with_content.return_value = ["2026-09-09"]
    service = _service(db)

    counts = service.generate(
        SummaryGenerationOptions(generate_weekly=False),
        is_cancelled=lambda: True,
        on_progress=lambda *_args: None,
        on_item_completed=lambda *_args: None,
        on_recording_summary_completed=lambda *_args: None,
        on_retry=lambda *_args: None,
    )

    assert counts == (0, 0, 0)
    db.fetch_by_dates.assert_not_called()
