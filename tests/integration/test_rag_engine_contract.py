"""Cross-module RAG engine contracts using the deterministic store adapter."""

from src.rag.chroma_store import ChromaStore
from src.rag.engine import RAGEngine
from src.rag.fallback_store import InMemoryChromaClient
from src.rag.runtime_policy import RAGRuntimePolicy


def _fallback_store(_persist_directory, *, chromadb_module):  # noqa: ARG001
    client = InMemoryChromaClient()
    return ChromaStore(
        client=client,
        collection=client.get_or_create_collection("transcriptions"),
        embedding_fn=None,
        is_persistent=False,
    )


def test_rag_engine_preserves_index_search_filter_and_delete_contracts():
    engine = RAGEngine(
        persist_directory="ignored-by-fallback",
        runtime_policy=RAGRuntimePolicy.resolve("Linux", {}),
        store_factory=_fallback_store,
    )

    engine.add_document("recording", "project planning project", {"kind": "recording"})
    engine.add_document("note", "project note", {"kind": "note"})

    assert engine.is_persistent is False
    assert [result["id"] for result in engine.search("project", ids=["recording"])] == ["recording"]
    assert [result["id"] for result in engine.search("project", where_clause={"kind": "note"})] == ["note"]

    engine.delete_document("recording")

    assert engine.search("project", ids=["recording"]) == []


def test_windows_engine_switches_once_to_keyword_fallback(monkeypatch):
    engine = RAGEngine(
        runtime_policy=RAGRuntimePolicy.resolve("Windows", {}),
        store_factory=_fallback_store,
    )
    calls = []
    monkeypatch.setattr(
        "src.rag.engine.rag_query_in_subprocess",
        lambda **_kwargs: calls.append("semantic") or None,
    )
    monkeypatch.setattr(
        "src.rag.engine.rag_keyword_search_in_subprocess",
        lambda **_kwargs: calls.append("keyword") or [{"id": "fallback"}],
    )

    assert engine.search("project") == [{"id": "fallback"}]
    assert engine.search("project") == [{"id": "fallback"}]
    assert calls == ["semantic", "keyword", "keyword"]
