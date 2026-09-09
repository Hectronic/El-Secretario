from src.rag.search import search_documents


class _Collection:
    def __init__(self):
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ids": [["one"]],
            "documents": [["planning notes"]],
            "metadatas": [[{"deleted": "0"}]],
            "distances": [[0.25]],
        }


def test_in_process_search_builds_filter_and_maps_results():
    collection = _Collection()

    results, enabled = search_documents(
        collection,
        persist_directory="db",
        query="planning",
        n_results=2,
        where_clause={"source": "note"},
        ids=["one"],
        use_subprocess=False,
        semantic_query_enabled=True,
        query_in_subprocess=lambda **_kwargs: None,
        keyword_search_in_subprocess=lambda **_kwargs: [],
    )

    assert enabled is True
    assert results == [{
        "id": "one",
        "text": "planning notes",
        "metadata": {"deleted": "0"},
        "distance": 0.25,
    }]
    assert collection.calls[0]["where"] == {
        "$and": [{"source": "note", "id": "one"}, {"deleted": {"$ne": "1"}}]
    }


def test_failed_windows_semantic_search_disables_it_and_uses_keyword_fallback():
    calls = []

    results, enabled = search_documents(
        _Collection(),
        persist_directory="db",
        query="planning",
        n_results=2,
        where_clause=None,
        ids=None,
        use_subprocess=True,
        semantic_query_enabled=True,
        query_in_subprocess=lambda **kwargs: calls.append(("semantic", kwargs)) or None,
        keyword_search_in_subprocess=lambda **kwargs: calls.append(("keyword", kwargs)) or [{"id": "one"}],
    )

    assert results == [{"id": "one"}]
    assert enabled is False
    assert [kind for kind, _kwargs in calls] == ["semantic", "keyword"]


def test_disabled_windows_semantic_search_skips_semantic_runner():
    results, enabled = search_documents(
        _Collection(),
        persist_directory="db",
        query="planning",
        n_results=2,
        where_clause=None,
        ids=None,
        use_subprocess=True,
        semantic_query_enabled=False,
        query_in_subprocess=lambda **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
        keyword_search_in_subprocess=lambda **_kwargs: [{"id": "one"}],
    )

    assert results == [{"id": "one"}]
    assert enabled is False
