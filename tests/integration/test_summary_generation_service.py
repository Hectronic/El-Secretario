"""SQLite contract for the non-Qt summary-generation workflow."""

from src.app.summaries import SummaryGenerationOptions, SummaryGenerationService
from src.database import DBManager


class _Settings:
    def value(self, _key, default=None):
        return default


def test_summary_generation_service_persists_recording_and_daily_summaries(tmp_path):
    db = DBManager(str(tmp_path / "summaries.sqlite"))
    record_id = db.save("planning.wav", "Decide the launch date", 5.0, "Planning")
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE records SET created_at = ? WHERE id = ?",
            ("2026-09-09 10:00:00", record_id),
        )
        conn.commit()

    calls = []
    events = []
    service = SummaryGenerationService(
        db,
        _Settings(),
        provider=object(),
        generate_content=lambda **kwargs: calls.append(kwargs["operation_name"]) or f"{kwargs['operation_name']} result",
    )

    counts = service.generate(
        SummaryGenerationOptions(
            generate_weekly=False,
            specific_dates=["2026-09-09"],
            exclude_today=False,
        ),
        is_cancelled=lambda: False,
        on_progress=lambda *_args: None,
        on_item_completed=lambda *event: events.append(event),
        on_recording_summary_completed=lambda *_args: None,
        on_retry=lambda *_args: None,
    )

    assert counts == (1, 1, 0)
    assert calls == [
        f"SummaryGenerator.recording_summary[{record_id}]",
        "SummaryGenerator.daily_summary[2026-09-09]",
    ]
    assert db.fetch_record(record_id)["summary"].endswith("result")
    assert db.get_daily_summary("2026-09-09", None).endswith("result")
    assert [event[0] for event in events] == ["recording", "daily"]
