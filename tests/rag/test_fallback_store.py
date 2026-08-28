# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import pytest

from src.rag.fallback_store import InMemoryChromaClient, InMemoryCollection


@pytest.fixture
def collection():
    return InMemoryCollection()


def test_in_memory_client_reuses_named_collections():
    client = InMemoryChromaClient()

    col1 = client.get_or_create_collection("test1")
    col2 = client.get_or_create_collection("test1")
    col3 = client.get_or_create_collection("test2")

    assert isinstance(col1, InMemoryCollection)
    assert col1 is col2
    assert col1 is not col3


def test_query_ranks_term_matches_and_applies_where_filters(collection):
    collection.upsert(
        ids=["1", "2", "3"],
        documents=["apple apple", "apple", "apple apple apple"],
        metadatas=[{"kind": "include"}, {"kind": "skip"}, {"kind": "include"}],
    )

    results = collection.query(["apple"], n_results=5, where={"kind": "include"})

    assert results["ids"][0] == ["3", "1"]
    assert results["distances"][0] == [0.25, pytest.approx(0.333333, rel=1e-5)]


def test_nested_where_and_id_filters(collection):
    collection.upsert(
        ids=["1", "2", "3"],
        documents=["Doc 1", "Doc 2", "Doc 3"],
        metadatas=[{"color": "red"}, {"color": "red"}, {"color": "blue"}],
    )

    results = collection.query(
        ["Doc"],
        n_results=5,
        where={"$and": [{"color": "red"}, {"id": {"$in": ["2", "3"]}}]},
    )

    assert results["ids"][0] == ["2"]
