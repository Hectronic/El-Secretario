from src.rag.embeddings_cache import EmbeddingsCache
from src.rag.engine import RAGEngine
from src.rag.fallback_store import InMemoryChromaClient
from src.rag.chroma_store import ChromaStore


class CountingEmbeddings:
    model_name = "test-model"

    def __init__(self):
        self.calls = 0

    def __call__(self, texts):
        self.calls += len(texts)
        return [[float(len(text)), 0.5] for text in texts]


def _store(_path, **_kwargs):
    client = InMemoryChromaClient()
    embedding = CountingEmbeddings()
    return ChromaStore(client, client.get_or_create_collection("test"), embedding, False)


def test_cache_serializes_vectors_and_invalidates_corrupt_rows(tmp_path):
    cache = EmbeddingsCache(tmp_path / "embeddings_cache.sqlite")
    cache.put("same", "model", [1.25, -2.5])
    assert cache.get("same", "model") == [1.25, -2.5]
    with cache._connection() as connection:
        connection.execute("UPDATE embeddings_cache SET vector_data = ?", (b"bad",))
        connection.commit()
    assert cache.get("same", "model") is None


def test_rag_engine_reuses_cached_vector_without_model_call(tmp_path):
    engine = RAGEngine(str(tmp_path / "chroma"), store_factory=_store)
    embedding = engine.embedding_fn

    engine.add_document("one", "unchanged paragraph")
    engine.add_document("two", "unchanged paragraph")
    engine.add_document("three", "changed paragraph")

    assert embedding.calls == 2
    assert engine.collection._docs["one"]["embedding"] == engine.collection._docs["two"]["embedding"]
