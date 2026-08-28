# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import warnings

import pytest

from src.rag.chroma_compat import (
    get_or_create_collection_compatible,
    suppress_sentencepiece_swig_deprecation_warnings,
)


def test_sentencepiece_swig_warning_filter_is_specific():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        suppress_sentencepiece_swig_deprecation_warnings()

        warnings.warn(
            "builtin type SwigPyPacked has no __module__ attribute",
            DeprecationWarning,
        )
        warnings.warn("application deprecation", DeprecationWarning)

    assert [str(w.message) for w in caught] == ["application deprecation"]


def test_get_or_create_collection_compatible_retries_without_embedding_on_conflict():
    class MockClient:
        def __init__(self):
            self.calls = []

        def get_or_create_collection(self, name, embedding_function=None):
            self.calls.append((name, embedding_function))
            if embedding_function is not None:
                raise ValueError("Embedding function conflict")
            return "fallback_col"

    client = MockClient()

    assert get_or_create_collection_compatible(client, "test", "some_fn") == "fallback_col"
    assert client.calls == [("test", "some_fn"), ("test", None)]


def test_get_or_create_collection_compatible_reraises_non_conflict_errors():
    class MockClient:
        def get_or_create_collection(self, name, embedding_function=None):
            raise ValueError("other configuration problem")

    with pytest.raises(ValueError, match="other configuration"):
        get_or_create_collection_compatible(MockClient(), "test", "some_fn")
