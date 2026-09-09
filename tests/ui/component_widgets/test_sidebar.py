from src.ui.component_widgets.sidebar import SidebarChatSessionWidget, SidebarTaskCompactWidget


def test_sidebar_task_emits_completion_for_persisted_task(qtbot):
    widget = SidebarTaskCompactWidget("Review release", ["planning"], task_id=12)
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.completion_toggled) as signal:
        widget.complete_check.click()

    assert signal.args == [12, True]
    assert widget.sizeHint().height() == widget.ROW_HEIGHT


def test_sidebar_chat_expands_persisted_session(qtbot):
    widget = SidebarChatSessionWidget({"id": 9, "name": "Roadmap", "created_at": "2026-09-09"})
    qtbot.addWidget(widget)

    with qtbot.waitSignal(widget.expand_requested) as signal:
        widget.expand_btn.click()

    assert signal.args == [9]
    assert widget.expand_btn.toolTip() == "Open the full Chat History tab"
