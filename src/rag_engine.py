# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import platform
import logging
from typing import List, Dict, Any, Optional

from src.rag.chroma_compat import suppress_sentencepiece_swig_deprecation_warnings
from src.rag.chroma_store import create_chroma_store
from src.rag.filters import build_search_where_clause
from src.rag.results import parse_semantic_query_results
from src.rag.subprocess_tasks import (
    rag_keyword_search_in_subprocess,
    rag_query_in_subprocess,
    rag_upsert_in_subprocess,
)

# Reduce odds of PostHog/background telemetry crashes in desktop environments.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")


suppress_sentencepiece_swig_deprecation_warnings()

import chromadb

class RAGEngine:
    def __init__(self, persist_directory: str = "chroma_db"):
        self.persist_directory = persist_directory
        self._is_windows = platform.system() == "Windows"
        # Enable safe delete by default on Windows due to native crashes in chroma rust delete path.
        self._safe_delete_mode = (
            self._is_windows
            and os.environ.get("EL_SECRETARIO_CHROMA_SAFE_DELETE", "1").strip().lower() in {"1", "true", "yes"}
        )
        self._subprocess_upsert_mode = (
            self._is_windows
            and os.environ.get("EL_SECRETARIO_RAG_SUBPROCESS_UPSERT", "1").strip().lower() in {"1", "true", "yes"}
        )
        self._subprocess_query_mode = (
            self._is_windows
            and os.environ.get("EL_SECRETARIO_RAG_SUBPROCESS_QUERY", "1").strip().lower() in {"1", "true", "yes"}
        )
        self._semantic_query_disabled = False
        store = create_chroma_store(
            self.persist_directory,
            chromadb_module=chromadb,
        )
        self.client = store.client
        self.is_persistent = store.is_persistent
        self.embedding_fn = store.embedding_fn
        self.collection = store.collection

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add or update a document in the vector store.
        doc_id: Unique ID (string)
        text: The transcription text
        metadata: Dict with extra info (e.g., title, date)
        """
        if not text:
            return

        # Ensure ID is in metadata for filtering
        if metadata is None:
            metadata = {}
        metadata['id'] = str(doc_id)
        metadata['deleted'] = "0"

        # ChromaDB upsert handles both add and update
        if self._subprocess_upsert_mode:
            ok = rag_upsert_in_subprocess(
                persist_directory=self.persist_directory,
                doc_id=str(doc_id),
                text=text,
                metadata=metadata,
                timeout_seconds=30,
            )
            if not ok:
                logging.error(
                    "RAG subprocess upsert failed for doc_id=%s. Skipping in-process fallback on Windows for stability.",
                    doc_id,
                )
                return
            return

        self.collection.upsert(
            ids=[str(doc_id)],
            documents=[text],
            metadatas=[metadata]
        )

    def search(self, query: str, n_results: int = 5, tag_filter: Optional[str] = None, where_clause: Optional[Dict[str, Any]] = None, ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for documents relevant to the query.
        Returns a list of results (id, text, metadata, distance).
        ids: Optional list of document IDs to restrict search to.
        """
        # If explicit where_clause is provided, use it.
        # Tag filter - REMOVED because $contains is not supported by ChromaDB
        # Caller should resolve tags to IDs and pass them in 'ids' argument
        # if tag_filter and tag_filter != "All":
        #     final_where["tags"] = {"$contains": tag_filter}
        final_where = build_search_where_clause(where_clause, ids)

        if self._subprocess_query_mode:
            if not self._semantic_query_disabled:
                results = rag_query_in_subprocess(
                    persist_directory=self.persist_directory,
                    query=query,
                    n_results=n_results,
                    where=final_where,
                    timeout_seconds=30,
                )
                if results is None:
                    self._semantic_query_disabled = True
                    logging.error(
                        "RAG subprocess query failed. Disabling semantic query for this session and using keyword fallback."
                    )
                    return rag_keyword_search_in_subprocess(
                        persist_directory=self.persist_directory,
                        query=query,
                        n_results=n_results,
                        where=final_where,
                        timeout_seconds=30,
                    )
            else:
                return rag_keyword_search_in_subprocess(
                    persist_directory=self.persist_directory,
                    query=query,
                    n_results=n_results,
                    where=final_where,
                    timeout_seconds=30,
                )
        else:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=final_where
            )
        
        return parse_semantic_query_results(results)


    def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID."""
        try:
            sid = str(doc_id)
            if self._safe_delete_mode:
                # Windows workaround: avoid native rust delete path that can crash the process.
                if self._subprocess_upsert_mode:
                    ok = rag_upsert_in_subprocess(
                        persist_directory=self.persist_directory,
                        doc_id=sid,
                        text="",
                        metadata={"id": sid, "deleted": "1"},
                        timeout_seconds=30,
                    )
                    if ok:
                        logging.info("RAG soft-delete applied for doc_id=%s (safe_delete_mode, subprocess)", sid)
                    else:
                        logging.error("RAG soft-delete failed for doc_id=%s (safe_delete_mode, subprocess)", sid)
                else:
                    self.collection.upsert(
                        ids=[sid],
                        documents=[""],
                        metadatas=[{"id": sid, "deleted": "1"}],
                    )
                    logging.info("RAG soft-delete applied for doc_id=%s (safe_delete_mode)", sid)
                return

            self.collection.delete(ids=[sid])
            logging.info("RAG hard-delete applied for doc_id=%s", sid)
        except Exception as e:
            logging.error("Error deleting document %s: %s", doc_id, e, exc_info=True)
