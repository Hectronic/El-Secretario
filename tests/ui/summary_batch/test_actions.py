from src.ui.summary_batch.actions import (
    SummaryBatchOptions,
    enqueue_missing_summaries,
    pending_counts,
    recordings_text,
    week_dates,
)


class _Database:
    def get_records_without_summary(self):
        return [{"id": 1, "title": "Meeting", "transcription": "Decision", "recording_notes": "Owner"}]

    def get_dates_without_summary(self, **_kwargs):
        return ["2026-09-01"]

    def get_weeks_without_summary(self, **_kwargs):
        return ["2026-09-06"]

    def fetch_by_dates(self, dates, _tags):
        return [{"title": "Meeting", "created_at": dates[0], "transcription": "Decision", "recording_notes": "Owner"}]

    def compose_ai_text(self, transcription, notes):
        return f"{transcription}\n{notes}"


class _Queue:
    def __init__(self):
        self.calls = []

    def enqueue_recording_summary(self, *args, **kwargs):
        self.calls.append(("recording", args, kwargs)); return True

    def enqueue_daily_summary(self, *args, **kwargs):
        self.calls.append(("daily", args, kwargs)); return True

    def enqueue_weekly_summary(self, *args, **kwargs):
        self.calls.append(("weekly", args, kwargs)); return True


def test_summary_batch_actions_count_and_enqueue_all_selected_scopes():
    db = _Database()
    queue = _Queue()
    options = SummaryBatchOptions(True, True, True, True, True)

    assert pending_counts(db, options) == (1, 1, 1)
    assert enqueue_missing_summaries(db, queue, options) == 3
    assert [call[0] for call in queue.calls] == ["recording", "daily", "weekly"]
    assert week_dates("2026-09-06")[0] == "2026-08-31"
    assert "Recording: Meeting" in recordings_text(db, db.fetch_by_dates(["2026-09-01"], None))
