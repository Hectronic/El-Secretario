# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import pytest
from src.rag_engine import _InMemoryCollection, _InMemoryChromaClient, _get_or_create_collection_compatible, RAGEngine
import os
import shutil

@pytest.fixture
def collection():
    return _InMemoryCollection()

def test_in_memory_client():
    client = _InMemoryChromaClient()
    col1 = client.get_or_create_collection("test1")
    col2 = client.get_or_create_collection("test1")
    col3 = client.get_or_create_collection("test2")
    
    assert isinstance(col1, _InMemoryCollection)
    assert col1 is col2
    assert col1 is not col3 # Wait, looking at the code:
    # def get_or_create_collection(self, name, embedding_function=None):
    #    if name not in self._collections:
    #        self._collections[name] = _InMemoryCollection()
    #    return self._collections[name]
    assert col1 is not col3
    assert len(client._collections) == 2

def test_get_or_create_compatible():
    client = _InMemoryChromaClient()
    # Should work normally
    col = _get_or_create_collection_compatible(client, "test", None)
    assert col is not None
    
    # Mocking a conflict error
    class MockClient:
        def __init__(self):
            self.calls = 0
        def get_or_create_collection(self, name, embedding_function=None):
            self.calls += 1
            if embedding_function is not None:
                raise ValueError("Embedding function conflict")
            return "fallback_col"
            
    mock_client = MockClient()
    res = _get_or_create_collection_compatible(mock_client, "test", "some_fn")
    assert res == "fallback_col"
    assert mock_client.calls == 2

def test_rag_engine_init_and_basic_ops(tmp_path):
    # Use a temporary directory for chroma_db
    persist_dir = str(tmp_path / "chroma_test")
    
    # Force in-memory for testing if possible, or just let it use PersistentClient in tmp
    engine = RAGEngine(persist_directory=persist_dir)
    
    # Test add_document
    engine.add_document("doc1", "Hello world", {"meta": "data"})
    
    # Test search
    results = engine.search("Hello", n_results=1)
    assert len(results) == 1
    assert results[0]["id"] == "doc1"
    assert results[0]["text"] == "Hello world"
    
    # Test soft delete
    engine._safe_delete_mode = True
    engine.delete_document("doc1")
    
    # Search should now return nothing because of the "deleted": {"$ne": "1"} filter
    results = engine.search("Hello")
    assert len(results) == 0

def test_rag_engine_search_with_ids(tmp_path):
    persist_dir = str(tmp_path / "chroma_test_ids")
    engine = RAGEngine(persist_directory=persist_dir)
    
    engine.add_document("1", "Alpha")
    engine.add_document("2", "Beta")
    engine.add_document("3", "Gamma")
    
    # Search restricted to specific IDs
    results = engine.search("Alpha Beta Gamma", ids=["1", "3"])
    found_ids = [r["id"] for r in results]
    assert "1" in found_ids
    assert "3" in found_ids
    assert "2" not in found_ids

def test_rag_engine_empty_text_ignored(tmp_path):
    persist_dir = str(tmp_path / "chroma_test_empty")
    engine = RAGEngine(persist_directory=persist_dir)
    engine.add_document("empty", "")
    # Should not crash and not add
    results = engine.search("")
    assert len(results) == 0

def test_rag_engine_where_clause(tmp_path):
    persist_dir = str(tmp_path / "chroma_test_where")
    engine = RAGEngine(persist_directory=persist_dir)
    engine.add_document("1", "Content", {"color": "red"})
    engine.add_document("2", "Content", {"color": "blue"})
    
    # Test passing a complex where clause directly
    where = {"color": "blue"}
    results = engine.search("Content", where_clause=where)
    assert len(results) == 1
    assert results[0]["id"] == "2"

def test_rag_engine_hard_delete(tmp_path):
    persist_dir = str(tmp_path / "chroma_test_hard_delete")
    engine = RAGEngine(persist_directory=persist_dir)
    engine._safe_delete_mode = False # Force hard delete
    engine.add_document("1", "To be deleted")
    assert len(engine.search("deleted")) == 1
    
    engine.delete_document("1")
    assert len(engine.search("deleted")) == 0

def test_rag_engine_delete_exception(tmp_path, caplog):
    persist_dir = str(tmp_path / "chroma_test_exc")
    engine = RAGEngine(persist_directory=persist_dir)
    
    # Mock collection to raise exception on delete
    class MockCol:
        def delete(self, ids):
            raise Exception("Delete failed")
    engine.collection = MockCol()
    engine._safe_delete_mode = False
    
    with caplog.at_level("ERROR"):
        engine.delete_document("any")
        assert "Error deleting document" in caplog.text

def test_upsert_and_basic_query(collection):
    collection.upsert(
        ids=["1", "2"],
        documents=["This is a test document", "Another example text"],
        metadatas=[{"type": "test"}, {"type": "example"}]
    )
    
    # Search for "test"
    results = collection.query(["test"], n_results=5)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "1"
    assert results["documents"][0][0] == "This is a test document"
    assert results["metadatas"][0][0]["type"] == "test"

def test_query_scoring_logic(collection):
    collection.upsert(
        ids=["1", "2", "3"],
        documents=[
            "apple apple apple", # 3 occurrences
            "apple apple",       # 2 occurrences
            "banana"             # 0 occurrences
        ],
        metadatas=[{}, {}, {}]
    )
    
    results = collection.query(["apple"], n_results=5)
    assert len(results["ids"][0]) == 2
    assert results["ids"][0][0] == "1" # Should be first due to higher count
    assert results["ids"][0][1] == "2"
    
    # Distances should be inversely proportional to score
    # score for "1" is 3, dist = 1/(1+3) = 0.25
    # score for "2" is 2, dist = 1/(1+2) = 0.333...
    assert results["distances"][0][0] == 0.25
    assert results["distances"][0][1] == pytest.approx(0.333333, rel=1e-5)

def test_query_no_results(collection):
    collection.upsert(["1"], ["Document"], [{}])
    results = collection.query(["nonexistent"], n_results=5)
    assert len(results["ids"][0]) == 0

def test_delete_document(collection):
    collection.upsert(["1", "2"], ["Doc 1", "Doc 2"], [{}, {}])
    assert len(collection._docs) == 2
    
    collection.delete(["1"])
    assert len(collection._docs) == 1
    assert "1" not in collection._docs
    assert "2" in collection._docs
    
    results = collection.query(["Doc"], n_results=5)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "2"

def test_filter_exact_match(collection):
    collection.upsert(
        ids=["1", "2"],
        documents=["Content A", "Content B"],
        metadatas=[{"category": "A"}, {"category": "B"}]
    )
    
    where = {"category": "A"}
    results = collection.query(["Content"], n_results=5, where=where)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "1"

def test_filter_id_exact_match(collection):
    collection.upsert(
        ids=["id1", "id2"],
        documents=["Content 1", "Content 2"],
        metadatas=[{}, {}]
    )
    
    where = {"id": "id2"}
    results = collection.query(["Content"], n_results=5, where=where)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "id2"

def test_filter_operator_in(collection):
    collection.upsert(
        ids=["1", "2", "3"],
        documents=["Doc 1", "Doc 2", "Doc 3"],
        metadatas=[{"val": 10}, {"val": 20}, {"val": 30}]
    )
    
    where = {"val": {"$in": [10, 30]}}
    results = collection.query(["Doc"], n_results=5, where=where)
    assert len(results["ids"][0]) == 2
    assert set(results["ids"][0]) == {"1", "3"}

def test_filter_operator_ne(collection):
    collection.upsert(
        ids=["1", "2", "3"],
        documents=["Doc 1", "Doc 2", "Doc 3"],
        metadatas=[{"tag": "blue"}, {"tag": "red"}, {"tag": "blue"}]
    )
    
    where = {"tag": {"$ne": "blue"}}
    results = collection.query(["Doc"], n_results=5, where=where)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "2"

def test_filter_operator_and(collection):
    collection.upsert(
        ids=["1", "2", "3", "4"],
        documents=["Doc 1", "Doc 2", "Doc 3", "Doc 4"],
        metadatas=[
            {"color": "red", "size": "small"},
            {"color": "red", "size": "large"},
            {"color": "blue", "size": "small"},
            {"color": "blue", "size": "large"}
        ]
    )
    
    # color == red AND size == small
    where = {
        "$and": [
            {"color": "red"},
            {"size": "small"}
        ]
    }
    results = collection.query(["Doc"], n_results=5, where=where)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "1"

def test_complex_nested_and(collection):
    collection.upsert(
        ids=["1", "2", "3"],
        documents=["D1", "D2", "D3"],
        metadatas=[
            {"a": 1, "b": 10},
            {"a": 1, "b": 20},
            {"a": 2, "b": 10}
        ]
    )
    
    # (a == 1) AND (b != 10)
    where = {
        "$and": [
            {"a": 1},
            {"b": {"$ne": 10}}
        ]
    }
    results = collection.query(["D"], n_results=5, where=where)
    assert len(results["ids"][0]) == 1
    assert results["ids"][0][0] == "2"

def test_query_n_results_limit(collection):
    collection.upsert(
        ids=[str(i) for i in range(10)],
        documents=["match" for _ in range(10)],
        metadatas=[{} for _ in range(10)]
    )
    
    results = collection.query(["match"], n_results=3)
    assert len(results["ids"][0]) == 3

def test_empty_query_string(collection):
    collection.upsert(["1"], ["Content"], [{}])
    # Empty query matches everything but score is 0
    results = collection.query([""], n_results=5)
    assert len(results["ids"][0]) == 1
    assert results["distances"][0][0] == 1.0 # 1 / (1 + 0)

def test_matches_where_logic_directly(collection):
    # Testing edge cases of _matches_where that might be hard to reach via query()
    entry = {
        "id": "test_id",
        "metadata": {"key": "value", "num": 42}
    }
    
    # None where
    assert collection._matches_where(entry, None) is True
    
    # Empty where
    assert collection._matches_where(entry, {}) is True
    
    # $and with $and inside (nested)
    nested_where = {
        "$and": [
            {"$and": [{"key": "value"}]}
        ]
    }
    assert collection._matches_where(entry, nested_where) is True
    
    # $and with non-existent key
    assert collection._matches_where(entry, {"nonexistent": "foo"}) is False
