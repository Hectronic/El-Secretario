from PyQt6.QtWidgets import QLabel, QPushButton

from src.ui.chat.conversation_view import ConversationView


def _source(source_id, title):
    return {
        "source_id": source_id,
        "title": title,
        "role": "recording",
        "excerpt": f"Excerpt for {title}",
        "degraded": False,
    }


def test_sources_are_collapsed_and_scoped_to_their_answer(qtbot):
    view = ConversationView()
    qtbot.addWidget(view)
    view.show()
    first = view.add_message("Assistant", "Answer one")
    second = view.add_message("Assistant", "Answer two")
    first.set_sources([_source(1, "First source")])
    second.set_sources([_source(2, "Second source")])

    assert first.sources_toggle.text() == "Fuentes (1)"
    assert not first.sources_toggle.isChecked()
    assert first.sources_panel.isHidden()
    assert second.sources_panel.isHidden()

    first.sources_toggle.click()

    assert not first.sources_panel.isHidden()
    assert second.sources_panel.isHidden()
    first_button = first.findChild(QPushButton, "")
    assert first_button is not None
    assert first_button.text() == "First source · recording"
    second_source_button = second.findChildren(QPushButton)[0]
    assert not second_source_button.isVisible()

    first.sources_toggle.click()
    assert first.sources_panel.isHidden()


def test_missing_sources_show_compact_honest_status(qtbot):
    view = ConversationView()
    qtbot.addWidget(view)
    view.show()
    card = view.add_message("Assistant", "Answer")

    card.set_sources([], degraded=True)

    assert card.sources_toggle.isHidden()
    assert "La recuperación se degradó" in card.sources_panel.findChild(QLabel).text()
