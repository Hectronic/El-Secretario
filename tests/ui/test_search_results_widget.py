from src.ui.search_results_widget import SearchResultsWidget


def test_search_activity_result_is_typed_and_routes_to_owning_source(qtbot):
    widget = SearchResultsWidget("milestone")
    qtbot.addWidget(widget)
    widget.display_results([{
        "event_type": "text_note", "source_id": 12, "title": "Planning notes",
        "occurred_at": "2026-09-25T10:00:00", "text": "Review milestones",
    }])
    result = widget.results_list.item(0)
    assert "text note" in result.text()
    routed = []
    widget.source_requested.connect(lambda kind, source_id: routed.append((kind, source_id)))
    widget.on_item_clicked(result)
    assert routed == [("text_note", 12)]
