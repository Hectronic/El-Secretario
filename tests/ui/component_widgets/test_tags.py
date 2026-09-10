from src.ui.component_widgets.tags import TagsLineEdit, create_tag_chip


def test_tag_chip_is_deterministic_and_exposes_full_tag(qtbot):
    first = create_tag_chip("Planning")
    second = create_tag_chip("planning")
    qtbot.addWidget(first)
    qtbot.addWidget(second)

    assert first.toolTip() == "Planning"
    assert first.styleSheet() == second.styleSheet()


def test_tags_line_edit_replaces_active_tag_with_completion(qtbot):
    field = TagsLineEdit()
    qtbot.addWidget(field)
    field.setText("work, pla")
    field.setCursorPosition(len(field.text()))

    field.insert_completion("planning")

    assert field.text() == "work, planning"
    assert field.cursorPosition() == len("work, planning")
