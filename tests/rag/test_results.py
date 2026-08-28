# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
from src.rag.results import keyword_rank_raw_results, parse_semantic_query_results


def test_parse_semantic_query_results_skips_deleted_and_tolerates_missing_fields():
    raw = {
        "ids": [["1", "2", "3"]],
        "documents": [["hello", "world"]],
        "metadatas": [[{"deleted": "0"}, {"deleted": "1"}, {}]],
        "distances": [[0.2]],
    }

    assert parse_semantic_query_results(raw) == [
        {"id": "1", "text": "hello", "metadata": {"deleted": "0"}, "distance": 0.2},
        {"id": "3", "text": "", "metadata": {}, "distance": 0.0},
    ]


def test_keyword_rank_raw_results_scores_limits_and_skips_deleted_records():
    raw = {
        "ids": ["a", "b", "c", "d"],
        "documents": ["apple apple", "apple banana", "banana", "apple"],
        "metadatas": [{"deleted": "0"}, {"deleted": "0"}, {"deleted": "1"}, {}],
    }

    ranked = keyword_rank_raw_results(raw, "apple banana", 2)

    assert [result["id"] for result in ranked] == ["a", "b"]
    assert ranked[0]["distance"] == -2.0
    assert ranked[1]["distance"] == -2.0
