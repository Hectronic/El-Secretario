from PyQt6.QtCore import QDate
from unittest.mock import MagicMock

from src.database import DBManager
from src.ui.calendar_widget import CalendarWidget


def test_calendar_navigation_filters_records_and_emits_selection_sync(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "calendar.sqlite"))
    record_id = db.save("meeting.wav", "Transcript", 10.0, "Planning")
    db.update_tags(record_id, "planning")
    with db.get_connection() as conn:
        conn.execute("UPDATE records SET created_at = ? WHERE id = ?", ("2026-09-07 10:00:00", record_id))
        conn.commit()
    widget = CalendarWidget(rag_engine=None, persistence=db)
    qtbot.addWidget(widget)
    emitted = []
    widget.selection_changed.connect(lambda monday, date, tags: emitted.append((monday, date, tags)))

    widget.set_selection(QDate(2026, 9, 7), "2026-09-07", "planning")
    assert widget.recording_list.count() == 1
    widget.navigate_next_day()

    assert widget.recording_list.count() == 1
    assert emitted[-1][1] == "2026-09-08"
    assert emitted[-1][2] == "planning"


def test_calendar_queues_daily_summary_for_selected_persisted_date(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "calendar-summary.sqlite"))
    record_id = db.save("meeting.wav", "Transcript", 10.0, "Planning")
    db.update_tags(record_id, "planning")
    with db.get_connection() as conn:
        conn.execute("UPDATE records SET created_at = ? WHERE id = ?", ("2026-09-07 10:00:00", record_id))
        conn.commit()

    queue = MagicMock()
    widget = CalendarWidget(rag_engine=None, task_queue=queue, persistence=db)
    qtbot.addWidget(widget)
    widget.set_selection(None, "2026-09-07", "planning")
    widget.on_generate_daily_summary_clicked()

    queue.enqueue_daily_summary.assert_called_once_with({
        "date": "2026-09-07",
        "tags_filter": "planning",
        "source": "calendar",
    })
