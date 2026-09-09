from PyQt6.QtCore import Qt

from src.database import DBManager
from src.ui.summary_viewer import SummaryViewerWidget


def test_weekly_summary_viewer_loads_persisted_records_and_emits_chat_context(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "summary-viewer.sqlite"))
    record_id = db.save("weekly.wav", "Transcript", 30.0, "Weekly sync")
    db.update_tags(record_id, "planning")
    with db.get_connection() as conn:
        conn.execute("UPDATE records SET created_at = ? WHERE id = ?", ("2026-03-04 10:00:00", record_id))
        conn.commit()
    db.save_task(None, "Publish notes", tags="planning", day_date="2026-03-04")
    viewer = SummaryViewerWidget(
        {"type": "weekly", "week_start": "2026-03-08", "tags_filter": "planning", "summary": "Week"},
        db=db,
    )
    qtbot.addWidget(viewer)
    emitted = []
    viewer.start_chat_contexts_requested.connect(lambda contexts, floating: emitted.append((contexts, floating)))

    viewer._open_week_chat()

    assert viewer.weekly_recordings_list.count() == 1
    assert emitted[0][1] is True
    assert {item["type"] for item in emitted[0][0]} == {"date_range", "tag", "recording"}


def test_daily_summary_viewer_refreshes_persisted_task_snapshot(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "daily-summary-viewer.sqlite"))
    task_id = db.save_task(None, "Capture decision", tags="planning", day_date="2026-09-09")
    viewer = SummaryViewerWidget(
        {"type": "daily", "date": "2026-09-09", "tags_filter": "planning", "summary": "Initial"},
        db=db,
    )
    qtbot.addWidget(viewer)

    item = viewer.daily_created_board.tasks_list.item(0)
    assert item.data(Qt.ItemDataRole.UserRole)["id"] == task_id

    viewer.update_content({"type": "daily", "date": "2026-09-09", "tags_filter": "planning", "summary": "Updated"})

    assert viewer.content_area.toPlainText() == "Updated"
    assert viewer.daily_created_board.tasks_list.count() == 1
