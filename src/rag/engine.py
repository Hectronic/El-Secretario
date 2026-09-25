"""Public RAG facade composed from focused storage and operation modules."""

import os
import platform
from typing import Any, Callable, Dict, List, Mapping, Optional

# Reduce odds of PostHog/background telemetry crashes in desktop environments.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")

from src.rag.chroma_compat import suppress_sentencepiece_swig_deprecation_warnings

suppress_sentencepiece_swig_deprecation_warnings()

from src.rag.chroma_store import create_chroma_store
from src.rag.documents import add_document as index_document
from src.rag.documents import delete_document as remove_document
from src.rag.embeddings_cache import EmbeddingsCache
from src.rag.runtime_policy import RAGRuntimePolicy
from src.rag.search import search_documents
from src.rag.subprocess_tasks import (
    rag_keyword_search_in_subprocess,
    rag_query_in_subprocess,
    rag_upsert_in_subprocess,
)
from src.resource_cleanup import release_local_inference_resources


class RAGEngine:
    """Stable API for indexing, searching, and deleting RAG documents."""

    def __init__(
        self,
        persist_directory: str = "chroma_db",
        *,
        runtime_policy: Optional[RAGRuntimePolicy] = None,
        platform_name: Optional[str] = None,
        environment: Optional[Mapping[str, str]] = None,
        store_factory: Callable[..., Any] = create_chroma_store,
        chromadb_module: Any = None,
        db: Any = None,
        embeddings_cache: Any = None,
    ):
        self.persist_directory = persist_directory
        self.db = db
        policy = runtime_policy or RAGRuntimePolicy.resolve(
            platform_name or platform.system(), environment if environment is not None else os.environ
        )
        self._is_windows = policy.is_windows
        self._safe_delete_mode = policy.safe_delete_mode
        self._subprocess_upsert_mode = policy.subprocess_upsert_mode
        self._subprocess_query_mode = policy.subprocess_query_mode
        self._semantic_query_disabled = False

        store = store_factory(self.persist_directory, chromadb_module=chromadb_module)
        self.client = store.client
        self.is_persistent = store.is_persistent
        self.embedding_fn = store.embedding_fn
        self.collection = store.collection
        self.embeddings_cache = embeddings_cache or EmbeddingsCache(
            os.path.join(self.persist_directory, "embeddings_cache.sqlite")
        )

    def add_document(
        self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add or update a document in the configured vector store."""
        try:
            embeddings = self._cached_embeddings(text)
            index_document(
                self.collection,
                persist_directory=self.persist_directory,
                doc_id=doc_id,
                text=text,
                metadata=metadata,
                use_subprocess=self._subprocess_upsert_mode,
                upsert_in_subprocess=rag_upsert_in_subprocess,
                embeddings=embeddings,
            )
            if hasattr(self, 'db') and self.db is not None:
                import hashlib
                fingerprint = hashlib.sha256(text.encode('utf-8')).hexdigest()
                try:
                    self.db.upsert_rag_index_status(str(doc_id), fingerprint, 'indexed')
                except Exception as e:
                    import logging
                    logging.error(f"Failed to update rag_index_status for {doc_id}: {e}")
        finally:
            release_local_inference_resources()

    def _cached_embeddings(self, text):
        if not text or self.embedding_fn is None or self._subprocess_upsert_mode:
            return None
        model_name = getattr(self.embedding_fn, "model_name", None) or (
            f"{type(self.embedding_fn).__module__}.{type(self.embedding_fn).__qualname__}"
        )
        vector = self.embeddings_cache.get_or_create(
            text, str(model_name), lambda value: self.embedding_fn([value])[0]
        )
        return [vector]

    def search(
        self,
        query: str,
        n_results: int = 5,
        tag_filter: Optional[str] = None,  # noqa: ARG002 - retained public API.
        where_clause: Optional[Dict[str, Any]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Search documents, falling back to keyword ranking after Windows failures."""
        try:
            results, semantic_enabled = search_documents(
                self.collection,
                persist_directory=self.persist_directory,
                query=query,
                n_results=n_results,
                where_clause=where_clause,
                ids=ids,
                use_subprocess=self._subprocess_query_mode,
                semantic_query_enabled=not self._semantic_query_disabled,
                query_in_subprocess=rag_query_in_subprocess,
                keyword_search_in_subprocess=rag_keyword_search_in_subprocess,
            )
            self._semantic_query_disabled = not semantic_enabled
            return results
        finally:
            release_local_inference_resources()

    def delete_document(self, doc_id: str) -> None:
        """Delete a document through the safe operation selected by runtime policy."""
        remove_document(
            self.collection,
            persist_directory=self.persist_directory,
            doc_id=doc_id,
            safe_delete_mode=self._safe_delete_mode,
            use_subprocess=self._subprocess_upsert_mode,
            upsert_in_subprocess=rag_upsert_in_subprocess,
        )
