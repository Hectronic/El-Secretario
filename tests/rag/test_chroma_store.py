# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
from pathlib import Path

from src.rag.chroma_store import create_chroma_store, create_embedding_function
from src.rag.fallback_store import InMemoryChromaClient


class FakeSettings:
    def __init__(self, anonymized_telemetry):
        self.anonymized_telemetry = anonymized_telemetry


class FakeCollectionClient:
    def __init__(self):
        self.calls = []

    def get_or_create_collection(self, name, embedding_function=None):
        self.calls.append((name, embedding_function))
        return {"name": name, "embedding": embedding_function}


class FakeChromaModule:
    def __init__(self, client=None, error=None):
        self.client = client or FakeCollectionClient()
        self.error = error
        self.calls = []

    def PersistentClient(self, path, settings):
        self.calls.append((path, settings))
        if self.error:
            raise self.error
        return self.client


class FakeEmbeddingModule:
    class SentenceTransformerEmbeddingFunction:
        def __init__(self, model_name):
            self.model_name = model_name

    class DefaultEmbeddingFunction:
        pass


class SentenceFailsEmbeddingModule:
    class SentenceTransformerEmbeddingFunction:
        def __init__(self, model_name):
            raise RuntimeError("sentence failed")

    class DefaultEmbeddingFunction:
        pass


class AllFailEmbeddingModule:
    class SentenceTransformerEmbeddingFunction:
        def __init__(self, model_name):
            raise RuntimeError("sentence failed")

    class DefaultEmbeddingFunction:
        def __init__(self):
            raise RuntimeError("default failed")


def test_create_embedding_function_prefers_sentence_transformer():
    embedding_fn = create_embedding_function(FakeEmbeddingModule)

    assert isinstance(embedding_fn, FakeEmbeddingModule.SentenceTransformerEmbeddingFunction)
    assert embedding_fn.model_name == "all-MiniLM-L6-v2"


def test_create_embedding_function_falls_back_to_default():
    embedding_fn = create_embedding_function(SentenceFailsEmbeddingModule)

    assert isinstance(embedding_fn, SentenceFailsEmbeddingModule.DefaultEmbeddingFunction)


def test_create_embedding_function_returns_none_when_all_embeddings_fail():
    assert create_embedding_function(AllFailEmbeddingModule) is None


def test_create_chroma_store_uses_persistent_client_and_collection(tmp_path):
    chroma = FakeChromaModule()

    store = create_chroma_store(
        str(tmp_path / "db"),
        chromadb_module=chroma,
        embedding_module=FakeEmbeddingModule,
        settings_factory=FakeSettings,
    )

    assert store.client is chroma.client
    assert store.collection["name"] == "transcriptions"
    assert store.collection["embedding"] is store.embedding_fn
    assert store.is_persistent is True
    assert Path(chroma.calls[0][0]).name == "db"
    assert chroma.calls[0][1].anonymized_telemetry is False


def test_create_chroma_store_falls_back_to_in_memory_client(tmp_path):
    chroma = FakeChromaModule(error=RuntimeError("cannot persist"))

    store = create_chroma_store(
        str(tmp_path / "db"),
        chromadb_module=chroma,
        embedding_module=FakeEmbeddingModule,
        settings_factory=FakeSettings,
    )

    assert isinstance(store.client, InMemoryChromaClient)
    assert store.is_persistent is False
    assert store.collection is store.client.get_or_create_collection("transcriptions")
