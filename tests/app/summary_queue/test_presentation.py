from src.app.summary_queue.presentation import (
    build_queue_management_snapshot,
    build_queue_view_snapshot,
    format_current_task_label,
    format_history_entry,
    format_metrics_label,
    format_task_display,
    format_wait_label,
    map_progress_state,
    normalize_status_message,
)


def test_format_task_display_variants():
    assert format_task_display({"type": "summary", "title": "Demo"}) == "[Summary] Demo"
    assert "missing only" in format_task_display({"type": "rag_reindex", "reindex_scope": "missing"})
    assert "(work)" in format_task_display({"type": "daily_summary", "date": "2026-05-13", "tags_filter": "work"})
    assert "batch process" in format_task_display({"type": "transcription", "title": "A", "source": "batch_process"})


def test_format_history_entry_includes_message_when_present():
    text = format_history_entry(
        {
            "time": "12:00:00",
            "event": "task_failed",
            "task": {"type": "transcription", "title": "Call"},
            "message": "boom",
        }
    )
    assert "[12:00:00] Task failed" in text
    assert "Transcription: Call" in text
    assert " - boom" in text


def test_format_metrics_label_defaults_to_zero():
    text = format_metrics_label({"running": 1, "pending": 2})
    assert "running=1" in text
    assert "pending=2" in text
    assert "queued=0" in text
    assert "failed=0" in text


def test_wait_and_current_and_status_formatters():
    assert format_wait_label(False, 0, "") == "Wait: none"
    assert format_wait_label(True, 7, "") == "Wait: 7s"
    assert format_wait_label(True, 7, "Retry 2/3 in progress") == "Wait: 7s - Retry 2/3 in progress"

    assert format_current_task_label(None) == "None (Idle)"
    assert format_current_task_label({"type": "summary", "title": "Demo"}) == "[Summary] Demo"

    assert normalize_status_message("  running  ") == "Status: running"
    assert normalize_status_message("") == ""


def test_build_queue_view_snapshot_maps_current_wait_and_pending():
    snapshot = build_queue_view_snapshot(
        current_task={"type": "summary", "title": "Demo"},
        pending_tasks=[
            {"type": "transcription", "title": "Audio A"},
            {"type": "daily_summary", "date": "2026-05-13"},
        ],
        is_waiting=True,
        seconds_left=5,
        wait_description="Retry 2/3 in progress",
    )

    assert snapshot["current_label"] == "[Summary] Demo"
    assert snapshot["has_current_task"] is True
    assert snapshot["wait_label"] == "Wait: 5s - Retry 2/3 in progress"
    assert snapshot["pending_labels"][0] == "[Transcription] Transcription: Audio A"
    assert snapshot["pending_labels"][1] == "[Daily summary] Day: 2026-05-13"


def test_map_progress_state_variants():
    assert map_progress_state(-1) == {
        "mode": "indeterminate",
        "min": 0,
        "max": 0,
        "value": 0,
        "format": "Working...",
    }
    assert map_progress_state(-2) == {
        "mode": "idle",
        "min": 0,
        "max": 1,
        "value": 0,
        "format": "Idle",
    }
    assert map_progress_state(-3)["mode"] == "ignore"
    assert map_progress_state(42) == {
        "mode": "determinate",
        "min": 0,
        "max": 100,
        "value": 42,
        "format": "42%",
    }


def test_build_queue_management_snapshot_includes_metrics_and_history_labels():
    snapshot = build_queue_management_snapshot(
        current_task={"type": "summary", "title": "Demo"},
        pending_tasks=[{"type": "daily_summary", "date": "2026-05-13"}],
        is_waiting=False,
        seconds_left=0,
        wait_description="",
        history_entries=[
            {
                "time": "12:00:00",
                "event": "finished",
                "task": {"type": "summary", "title": "Demo"},
                "message": "",
            }
        ],
        runtime_stats={"running": 1, "pending": 1, "queued": 2, "finished": 3, "failed": 0, "skipped": 0},
        fallback_running=0,
        fallback_pending=0,
    )
    assert snapshot["current_label"] == "[Summary] Demo"
    assert snapshot["wait_label"] == "Wait: none"
    assert snapshot["pending_labels"] == ["[Daily summary] Day: 2026-05-13"]
    assert "queued=2" in snapshot["metrics_label"]
    assert snapshot["history_labels"] == ["[12:00:00] Finished: [Summary] Demo"]
