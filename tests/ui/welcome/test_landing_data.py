# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
from datetime import date

from src.ui.welcome.landing_data import (
    fetch_favorites_page,
    fetch_today_items,
    search_result_items,
)


class _DB:
    def __init__(self):
        self.favorite_calls = []
        self.favorites_by_offset = {}
        self.date_range_calls = []
        self.records = []

    def fetch_favorites(self, *, limit, offset):
        self.favorite_calls.append({"limit": limit, "offset": offset})
        return self.favorites_by_offset.get(offset, [])

    def fetch_by_date_range(self, start_date, end_date, tags=None, favorites_only=False):
        self.date_range_calls.append(
            {
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "favorites_only": favorites_only,
            }
        )
        return self.records


def test_search_result_items_formats_score_excerpt_and_id():
    items = search_result_items(
        [
            {
                "id": 42,
                "distance": 0.125,
                "text": "abcdefghij" * 12,
                "metadata": {"title": "Roadmap"},
            }
        ]
    )

    assert len(items) == 1
    assert items[0].record_id == 42
    assert items[0].text == f"Roadmap (Score: 0.88)\n{'abcdefghij' * 10}..."


def test_fetch_favorites_page_formats_items_and_navigation_state():
    db = _DB()
    db.favorites_by_offset = {
        5: [
            {"id": 7, "title": "Meeting", "created_at": "2026-06-01", "duration": 12.34},
            {"id": 8, "title": "", "created_at": "2026-06-02", "duration": 3},
        ],
        10: [{"id": 9, "title": "Next", "created_at": "2026-06-03", "duration": 1}],
    }

    page = fetch_favorites_page(db, page=1, page_size=5)

    assert page.page == 1
    assert page.has_previous is True
    assert page.has_next is True
    assert [(item.record_id, item.text) for item in page.items] == [
        (7, "Meeting (12.3s)"),
        (8, "2026-06-02 (3.0s)"),
    ]


def test_fetch_favorites_page_steps_back_when_current_page_is_empty():
    db = _DB()
    db.favorites_by_offset = {
        0: [{"id": 1, "title": "Only", "created_at": "2026-06-01", "duration": 1}],
    }

    page = fetch_favorites_page(db, page=1, page_size=5)

    assert page.page == 0
    assert page.has_previous is False
    assert page.has_next is False
    assert [(item.record_id, item.text) for item in page.items] == [(1, "Only (1.0s)")]
    assert db.favorite_calls[:2] == [
        {"limit": 5, "offset": 5},
        {"limit": 5, "offset": 0},
    ]


def test_fetch_favorites_page_steps_back_across_multiple_empty_pages():
    db = _DB()
    db.favorites_by_offset = {
        5: [{"id": 2, "title": "Previous", "created_at": "2026-06-02", "duration": 2}],
    }

    page = fetch_favorites_page(db, page=4, page_size=5)

    assert page.page == 1
    assert page.has_previous is True
    assert page.has_next is False
    assert [(item.record_id, item.text) for item in page.items] == [(2, "Previous (2.0s)")]
    assert db.favorite_calls[:4] == [
        {"limit": 5, "offset": 20},
        {"limit": 5, "offset": 15},
        {"limit": 5, "offset": 10},
        {"limit": 5, "offset": 5},
    ]


def test_fetch_today_items_formats_notes_and_recordings_for_requested_day():
    db = _DB()
    db.records = [
        {"id": 3, "type": "note", "title": ""},
        {"id": 4, "type": "recording", "title": "Standup", "created_at": "09:00", "duration": 6.2},
        {"id": 5, "type": "recording", "title": "", "created_at": "10:00"},
    ]

    items = fetch_today_items(db, today=date(2026, 6, 16))

    assert db.date_range_calls == [
        {
            "start_date": "2026-06-16",
            "end_date": "2026-06-16",
            "tags": None,
            "favorites_only": False,
        }
    ]
    assert [(item.record_id, item.text) for item in items] == [
        (3, "📝 Untitled Note"),
        (4, "🎤 Standup (6.2s)"),
        (5, "🎤 10:00 (0.0s)"),
    ]
