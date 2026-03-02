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

# Reduce odds of PostHog/background telemetry crashes in desktop environments.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

class RAGEngine:
    def __init__(self, persist_directory: str = "chroma_db"):
        self.persist_directory = persist_directory
        self._is_windows = platform.system() == "Windows"
        # Enable safe delete by default on Windows due to native crashes in chroma rust delete path.
        self._safe_delete_mode = (
            self._is_windows
            and os.environ.get("EL_SECRETARIO_CHROMA_SAFE_DELETE", "1").strip().lower() in {"1", "true", "yes"}
        )
        os.makedirs(self.persist_directory, exist_ok=True)
        chroma_settings = Settings(anonymized_telemetry=False)

        logging.info(
            "Initializing RAGEngine: persist_dir=%s windows=%s safe_delete_mode=%s telemetry_disabled=%s",
            self.persist_directory,
            self._is_windows,
            self._safe_delete_mode,
            True,
        )
        # Initialize ChromaDB client. Fall back to in-memory client when
        # persistence is unavailable in the current environment.
        try:
            self.client = chromadb.PersistentClient(path=persist_directory, settings=chroma_settings)
            self.is_persistent = True
        except Exception as e:
            logging.warning(f"Persistent Chroma init failed, using in-memory fallback: {e}")
            self.client = chromadb.Client(settings=chroma_settings)
            self.is_persistent = False
        
        # Use SentenceTransformer if available, fallback to default.
        # DefaultEmbeddingFunction (ONNX) can fail to load DLLs on some Windows setups.
        try:
            logging.info("Initializing embedding function (SentenceTransformer)...")
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        except Exception as e:
            logging.warning(f"SentenceTransformer init failed, falling back to default: {e}")
            try:
                self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
                logging.info("Fallback: Using DefaultEmbeddingFunction (ONNX).")
            except Exception as e2:
                logging.error(f"All embedding functions failed to initialize: {e2}")
                self.embedding_fn = None
        
        logging.info("RAG Engine embedding function initialized: %s", 
                     type(self.embedding_fn).__name__ if self.embedding_fn else "None")
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="transcriptions",
            embedding_function=self.embedding_fn
        )

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
        final_where = {}
        
        # If explicit where_clause is provided, use it
        if where_clause:
            final_where = where_clause.copy()
        
        # Tag filter - REMOVED because $contains is not supported by ChromaDB
        # Caller should resolve tags to IDs and pass them in 'ids' argument
        # if tag_filter and tag_filter != "All":
        #     final_where["tags"] = {"$contains": tag_filter}
            
        # ID filter (if provided)
        if ids:
            if len(ids) == 1:
                final_where["id"] = ids[0]
            else:
                final_where["id"] = {"$in": ids}
                
        # Always ignore soft-deleted documents.
        deleted_filter = {"deleted": {"$ne": "1"}}
        if final_where:
            final_where = {"$and": [final_where, deleted_filter]}
        else:
            final_where = deleted_filter

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=final_where
        )
        
        # Parse results into a cleaner format
        parsed_results = []
        if results['ids']:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                if str((metadata or {}).get("deleted", "0")) == "1":
                    continue
                parsed_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': metadata,
                    'distance': results['distances'][0][i] if results['distances'] else 0.0
                })
                
        return parsed_results


    def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID."""
        try:
            sid = str(doc_id)
            if self._safe_delete_mode:
                # Windows workaround: avoid native rust delete path that can crash the process.
                try:
                    self.collection.upsert(
                        ids=[sid],
                        documents=[""],
                        metadatas=[{"id": sid, "deleted": "1"}],
                    )
                    logging.info("RAG soft-delete applied for doc_id=%s (safe_delete_mode)", sid)
                except Exception as upsert_error:
                    logging.warning(
                        "RAG soft-delete via upsert failed for doc_id=%s: %s. Falling back to direct delete.",
                        sid, upsert_error
                    )
                    self.collection.delete(ids=[sid])
                    logging.info("RAG hard-delete fallback applied for doc_id=%s", sid)
                return

            self.collection.delete(ids=[sid])
            logging.info("RAG hard-delete applied for doc_id=%s", sid)
        except Exception as e:
            logging.error("Error deleting document %s: %s", doc_id, e, exc_info=True)
