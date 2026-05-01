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
import json
import platform
import logging
import tempfile
import multiprocessing as mp
import warnings
from typing import List, Dict, Any, Optional

# Reduce odds of PostHog/background telemetry crashes in desktop environments.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("POSTHOG_DISABLED", "1")


_SENTENCEPIECE_SWIG_DEPRECATION_MESSAGES = (
    r"builtin type SwigPyPacked has no __module__ attribute",
    r"builtin type SwigPyObject has no __module__ attribute",
    r"builtin type swigvarlink has no __module__ attribute",
)


def _suppress_sentencepiece_swig_deprecation_warnings() -> None:
    """Hide known Python 3.12 SWIG warnings emitted by sentencepiece."""
    for message in _SENTENCEPIECE_SWIG_DEPRECATION_MESSAGES:
        warnings.filterwarnings(
            "ignore",
            message=message,
            category=DeprecationWarning,
        )


_suppress_sentencepiece_swig_deprecation_warnings()

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions


class _InMemoryCollection:
    """Minimal in-memory collection fallback compatible with the Chroma API we use."""

    def __init__(self):
        self._docs: Dict[str, Dict[str, Any]] = {}

    def upsert(self, ids, documents, metadatas):
        for doc_id, text, metadata in zip(ids, documents, metadatas):
            self._docs[str(doc_id)] = {
                "id": str(doc_id),
                "document": text or "",
                "metadata": dict(metadata or {}),
            }

    def delete(self, ids):
        for doc_id in ids:
            self._docs.pop(str(doc_id), None)

    def query(self, query_texts, n_results=5, where=None):
        query = (query_texts[0] if query_texts else "") or ""
        q_lower = query.lower()

        candidates = []
        for doc_id, entry in self._docs.items():
            if not self._matches_where(entry, where):
                continue

            text = entry.get("document", "") or ""
            text_lower = text.lower()
            # Prefer explicit term hits; fallback to deterministic tie-break by id.
            score = text_lower.count(q_lower) if q_lower else 0
            if q_lower and score == 0 and q_lower not in text_lower:
                continue
            candidates.append((score, doc_id, entry))

        candidates.sort(key=lambda item: (-item[0], item[1]))
        selected = candidates[: max(0, int(n_results or 0))]

        return {
            "ids": [[item[1] for item in selected]],
            "documents": [[item[2].get("document", "") for item in selected]],
            "metadatas": [[item[2].get("metadata", {}) for item in selected]],
            "distances": [[float(1.0 / (1 + item[0])) for item in selected]],
        }

    def _matches_where(self, entry: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
        if not where:
            return True
        if "$and" in where:
            return all(self._matches_where(entry, clause) for clause in where.get("$and", []))

        for key, expected in where.items():
            if key == "$and":
                continue
            actual = entry["id"] if key == "id" else (entry.get("metadata", {}) or {}).get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
            else:
                if actual != expected:
                    return False
        return True


class _InMemoryChromaClient:
    """Minimal client fallback exposing get_or_create_collection."""

    def __init__(self):
        self._collections: Dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(self, name, embedding_function=None):  # noqa: ARG002
        if name not in self._collections:
            self._collections[name] = _InMemoryCollection()
        return self._collections[name]


def _get_or_create_collection_compatible(client, name: str, embedding_fn):
    """
    Open/create a collection while tolerating embedding-function conflicts
    with previously persisted Chroma configurations.
    """
    try:
        return client.get_or_create_collection(
            name=name,
            embedding_function=embedding_fn,
        )
    except ValueError as e:
        msg = str(e).lower()
        if "embedding function" in msg and ("conflict" in msg or "already exists" in msg):
            logging.warning(
                "Embedding function conflict for collection '%s'. Reusing existing collection configuration.",
                name,
            )
            return client.get_or_create_collection(name=name)
        raise


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
        os.makedirs(self.persist_directory, exist_ok=True)
        chroma_settings = Settings(anonymized_telemetry=False)

        logging.info(
            "Initializing RAGEngine: persist_dir=%s windows=%s safe_delete_mode=%s subprocess_upsert_mode=%s telemetry_disabled=%s",
            self.persist_directory,
            self._is_windows,
            self._safe_delete_mode,
            self._subprocess_upsert_mode,
            True,
        )
        # Initialize ChromaDB client. Fall back to in-memory client when
        # persistence is unavailable in the current environment.
        try:
            self.client = chromadb.PersistentClient(path=persist_directory, settings=chroma_settings)
            self.is_persistent = True
        except Exception as e:
            logging.warning(f"Persistent Chroma init failed, using in-memory fallback: {e}")
            self.client = _InMemoryChromaClient()
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
        self.collection = _get_or_create_collection_compatible(
            self.client,
            name="transcriptions",
            embedding_fn=self.embedding_fn,
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
        if self._subprocess_upsert_mode:
            ok = _rag_upsert_in_subprocess(
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

        if self._subprocess_query_mode:
            if not self._semantic_query_disabled:
                results = _rag_query_in_subprocess(
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
                    return _rag_keyword_search_in_subprocess(
                        persist_directory=self.persist_directory,
                        query=query,
                        n_results=n_results,
                        where=final_where,
                        timeout_seconds=30,
                    )
            else:
                return _rag_keyword_search_in_subprocess(
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
                if self._subprocess_upsert_mode:
                    ok = _rag_upsert_in_subprocess(
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


def _rag_upsert_subprocess_entry(payload: Dict[str, Any], result_path: str):
    result = {"ok": False, "error": "unknown error"}
    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions

        chroma_settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=payload["persist_directory"], settings=chroma_settings)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        collection = _get_or_create_collection_compatible(
            client,
            name="transcriptions",
            embedding_fn=embedding_fn,
        )
        collection.upsert(
            ids=[payload["doc_id"]],
            documents=[payload["text"]],
            metadatas=[payload["metadata"]],
        )
        result = {"ok": True}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    finally:
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            # Parent process will treat missing result file as failure.
            pass


def _rag_upsert_in_subprocess(
    *,
    persist_directory: str,
    doc_id: str,
    text: str,
    metadata: Dict[str, Any],
    timeout_seconds: int = 30,
) -> bool:
    try:
        ctx = mp.get_context("spawn")
        payload = {
            "persist_directory": persist_directory,
            "doc_id": doc_id,
            "text": text,
            "metadata": metadata,
        }
        fd, result_path = tempfile.mkstemp(prefix="rag_upsert_", suffix=".json")
        os.close(fd)
        proc = ctx.Process(
            target=_rag_upsert_subprocess_entry,
            args=(payload, result_path),
            daemon=False,
        )
        proc.start()
        proc.join(timeout=timeout_seconds)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            logging.error("RAG subprocess upsert timed out for doc_id=%s", doc_id)
            return False
        if proc.exitcode != 0:
            logging.error("RAG subprocess upsert crashed for doc_id=%s with exitcode=%s", doc_id, proc.exitcode)
            return False
        if not os.path.exists(result_path):
            logging.error("RAG subprocess upsert finished without result for doc_id=%s", doc_id)
            return False
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        if not result.get("ok"):
            logging.error("RAG subprocess upsert error for doc_id=%s: %s", doc_id, result.get("error"))
            return False
        return True
    except Exception as e:
        logging.error("RAG subprocess upsert setup failed for doc_id=%s: %s", doc_id, e, exc_info=True)
        return False
    finally:
        if "result_path" in locals():
            try:
                os.remove(result_path)
            except OSError:
                pass


def _rag_query_subprocess_entry(payload: Dict[str, Any], result_path: str):
    result = {"ok": False, "error": "unknown error"}
    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions

        chroma_settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=payload["persist_directory"], settings=chroma_settings)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        collection = _get_or_create_collection_compatible(
            client,
            name="transcriptions",
            embedding_fn=embedding_fn,
        )
        query_result = collection.query(
            query_texts=[payload["query"]],
            n_results=payload["n_results"],
            where=payload["where"],
        )
        result = {"ok": True, "result": query_result}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    finally:
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass


def _rag_query_in_subprocess(
    *,
    persist_directory: str,
    query: str,
    n_results: int,
    where: Dict[str, Any],
    timeout_seconds: int = 30,
) -> Optional[Dict[str, Any]]:
    try:
        ctx = mp.get_context("spawn")
        payload = {
            "persist_directory": persist_directory,
            "query": query,
            "n_results": n_results,
            "where": where,
        }
        fd, result_path = tempfile.mkstemp(prefix="rag_query_", suffix=".json")
        os.close(fd)
        proc = ctx.Process(
            target=_rag_query_subprocess_entry,
            args=(payload, result_path),
            daemon=False,
        )
        proc.start()
        proc.join(timeout=timeout_seconds)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            logging.error("RAG subprocess query timed out")
            return None
        if proc.exitcode != 0:
            logging.error("RAG subprocess query crashed with exitcode=%s", proc.exitcode)
            return None
        if not os.path.exists(result_path):
            logging.error("RAG subprocess query finished without result file")
            return None
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        if not result.get("ok"):
            logging.error("RAG subprocess query error: %s", result.get("error"))
            return None
        return result.get("result")
    except Exception as e:
        logging.error("RAG subprocess query setup failed: %s", e, exc_info=True)
        return None
    finally:
        if "result_path" in locals():
            try:
                os.remove(result_path)
            except OSError:
                pass


def _rag_keyword_search_subprocess_entry(payload: Dict[str, Any], result_path: str):
    result = {"ok": False, "error": "unknown error"}
    try:
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions

        chroma_settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=payload["persist_directory"], settings=chroma_settings)
        embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        collection = _get_or_create_collection_compatible(
            client,
            name="transcriptions",
            embedding_fn=embedding_fn,
        )
        raw = collection.get(
            where=payload["where"],
            include=["documents", "metadatas"],
        )
        result = {"ok": True, "result": raw}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    finally:
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f)
        except Exception:
            pass


def _rag_keyword_search_in_subprocess(
    *,
    persist_directory: str,
    query: str,
    n_results: int,
    where: Dict[str, Any],
    timeout_seconds: int = 30,
) -> List[Dict[str, Any]]:
    try:
        ctx = mp.get_context("spawn")
        payload = {
            "persist_directory": persist_directory,
            "query": query,
            "n_results": n_results,
            "where": where,
        }
        fd, result_path = tempfile.mkstemp(prefix="rag_kw_query_", suffix=".json")
        os.close(fd)
        proc = ctx.Process(
            target=_rag_keyword_search_subprocess_entry,
            args=(payload, result_path),
            daemon=False,
        )
        proc.start()
        proc.join(timeout=timeout_seconds)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            logging.error("RAG keyword subprocess query timed out")
            return []
        if proc.exitcode != 0:
            logging.error("RAG keyword subprocess query crashed with exitcode=%s", proc.exitcode)
            return []
        if not os.path.exists(result_path):
            logging.error("RAG keyword subprocess query finished without result file")
            return []
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        if not result.get("ok"):
            logging.error("RAG keyword subprocess query error: %s", result.get("error"))
            return []
        raw = result.get("result") or {}
        ids = raw.get("ids") or []
        docs = raw.get("documents") or []
        metas = raw.get("metadatas") or []
        terms = [t for t in query.lower().split() if t]
        scored = []
        for idx, doc_id in enumerate(ids):
            text = docs[idx] if idx < len(docs) else ""
            metadata = metas[idx] if idx < len(metas) else {}
            if str((metadata or {}).get("deleted", "0")) == "1":
                continue
            text_l = (text or "").lower()
            score = sum(text_l.count(term) for term in terms) if terms else 0
            scored.append({
                "id": doc_id,
                "text": text or "",
                "metadata": metadata or {},
                "distance": float(-score),
            })
        scored.sort(key=lambda r: r["distance"])
        return scored[:n_results]
    except Exception as e:
        logging.error("RAG keyword subprocess query setup failed: %s", e, exc_info=True)
        return []
    finally:
        if "result_path" in locals():
            try:
                os.remove(result_path)
            except OSError:
                pass
