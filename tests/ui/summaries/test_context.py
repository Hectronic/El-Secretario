from src.ui.summaries.context import build_week_chat_contexts, summary_date_range, summary_tags


class _DB:
    def fetch_by_date_range(self, start, end, tags=None):
        assert (start, end, tags) == ("2026-03-02", "2026-03-08", ["planning", "ops"])
        return [{"id": 4, "title": "Weekly sync"}]


def test_week_context_uses_range_tags_and_recordings():
    summary = {"type": "weekly", "week_start": "2026-03-08", "tags_filter": "planning, ops"}

    contexts = build_week_chat_contexts(summary, _DB())

    assert summary_date_range(summary) == ("2026-03-02", "2026-03-08")
    assert summary_tags(summary) == ["planning", "ops"]
    assert contexts[0]["type"] == "date_range"
    assert contexts[-1] == {"type": "recording", "value": 4, "label": "Weekly sync"}
