from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from PyQt6.QtCore import QDate, Qt

from src.app.scheduling.scheduler import MeetingScheduler
from src.database import DBManager
from src.ui.meetings.template_dialog import MeetingTemplateDialog
from src.ui.meetings.widget import RecurringMeetingsWidget


def _meeting(start_date):
    return {
        "title": "Planning",
        "tags": ["Work"],
        "timezone": "Europe/Madrid",
        "local_start_time": "10:00",
        "expected_duration_seconds": 3600,
        "reminder_lead_seconds": 600,
        "recurrence_kind": "weekly",
        "recurrence_payload": {"version": 1, "weekdays": [0, 2]},
        "starts_on": start_date.isoformat(),
    }


def test_template_dialog_validates_and_previews_next_three(qtbot):
    dialog = MeetingTemplateDialog(_meeting(date.today()))
    qtbot.addWidget(dialog)
    dialog.title_edit.setText("  Design review  ")
    dialog._save()

    assert dialog.result_data["title"] == "Design review"
    assert len(dialog.preview_label.text().split(" · ")) >= 3

    dialog.title_edit.clear()
    dialog._save()
    assert dialog.result_data["title"] == "Design review"
    assert "required" in dialog.error_label.text().lower()


def test_calendar_view_shows_occurrence_details_and_start_action(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "meetings-ui.sqlite"))
    now = datetime.now(timezone.utc)
    local_date = (datetime.now(ZoneInfo("Europe/Madrid")).date() + timedelta(days=1))
    template_id = db.create_template(_meeting(local_date), now=now)
    scheduler = MeetingScheduler(db.meetings)
    widget = RecurringMeetingsWidget(db.meetings, scheduler)
    qtbot.addWidget(widget)
    rows = db.meetings.list_occurrences(template_id=template_id)
    assert rows

    requested = []
    widget.start_requested.connect(requested.append)
    widget.select_occurrence(rows[0]["id"])
    assert widget.occurrence_list.currentItem() is not None
    assert "Planning" in widget.occurrence_details.text()
    assert widget.start_button.isEnabled()
    widget.start_button.click()
    assert requested == [rows[0]["id"]]

    occurrence_date = rows[0]["scheduled_local"][:10]
    widget.calendar.setSelectedDate(QDate.fromString(occurrence_date, "yyyy-MM-dd"))
    assert widget.occurrence_list.count() >= 1
