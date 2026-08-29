# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
from src.rag.filters import build_search_where_clause


def test_build_search_where_clause_always_excludes_soft_deleted_records():
    assert build_search_where_clause(None, None) == {"deleted": {"$ne": "1"}}

    assert build_search_where_clause({"color": "blue"}, ["id2"]) == {
        "$and": [
            {"color": "blue", "id": "id2"},
            {"deleted": {"$ne": "1"}},
        ]
    }

    assert build_search_where_clause({}, ["id1", "id3"]) == {
        "$and": [
            {"id": {"$in": ["id1", "id3"]}},
            {"deleted": {"$ne": "1"}},
        ]
    }
