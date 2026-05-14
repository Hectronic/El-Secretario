from src.app.summary_queue.runtime import (
    build_retry_wait_state,
    collect_runtime_stats,
)


def test_collect_runtime_stats_counts_events_and_live_state():
    history_entries = [
        {"event": "queued"},
        {"event": "finished"},
        {"event": "failed"},
        {"event": "skipped"},
        {"event": "trace"},
        {"event": "unknown"},
    ]

    stats = collect_runtime_stats(
        has_current_task=True,
        pending_count=3,
        history_entries=history_entries,
    )

    assert stats["running"] == 1
    assert stats["pending"] == 3
    assert stats["queued"] == 1
    assert stats["finished"] == 1
    assert stats["failed"] == 1
    assert stats["skipped"] == 1
    assert stats["trace"] == 1


def test_build_retry_wait_state_trims_long_error_messages():
    wait, description, message = build_retry_wait_state(
        delay_seconds=2.6,
        attempt=1,
        total_attempts=4,
        error_text="x" * 200,
    )

    assert wait == 3
    assert description == "Retry 2/4 in progress"
    assert "Waiting 3s before retry (2/4)." in message
    assert len(message) < 200
