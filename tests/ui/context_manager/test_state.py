from src.ui.context_manager.entries import entry_descriptors
from src.ui.context_manager.state import ContextPanelState, state_from_dict, status_labels


def test_context_state_round_trip_normalizes_values_and_labels():
    state = state_from_dict({
        "current_week_monday": "2026-09-07",
        "current_date_filter": "2026-09-08",
        "active_global_tags": [" work ", "", "ops"],
        "notebook_ids": [2],
        "forced_records": [{"id": 7, "title": "Pinned"}],
        "sync_enabled": False,
        "collapsed": True,
    })

    assert state.as_dict()["active_global_tags"] == ["work", "ops"]
    assert status_labels(state) == ("Dates: 2026-09-07 to 2026-09-08", "Tags: work, ops")


def test_entry_descriptors_deduplicate_forced_records_and_keep_notebooks():
    entries = entry_descriptors(
        [{"id": 1, "title": "Pinned", "created_at": "2026-09-01"}],
        [{"id": 1, "title": "Duplicate", "type": "recording"}, {"id": 2, "title": "Note", "type": "note"}],
        [{"title": "Notebook note"}],
    )

    assert [text for text, _tooltip in entries] == ["📌 🎤 Pinned", "📝 Note", "📓 Notebook note"]
