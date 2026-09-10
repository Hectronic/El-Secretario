from src.ui.component_widgets.rows import RecordingListItemWidget, TaskRowWidget


def test_recording_row_emits_favorite_and_delete_actions(qtbot):
    widget = RecordingListItemWidget({"created_at": "2026-09-09", "duration": 4.2})
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.favorite_toggled) as favorite:
        widget.fav_btn.click()
    with qtbot.waitSignal(widget.delete_requested):
        widget.del_btn.click()

    assert favorite.args == [True]
    assert widget.fav_btn.text() == "★"


def test_task_row_reports_completion_state(qtbot):
    widget = TaskRowWidget({"id": 3, "content": "Review tests", "tags": "quality"})
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.status_changed) as signal:
        widget.status_btn.click()

    assert signal.args == [3, True]
    assert widget.content_label.font().strikeOut()
