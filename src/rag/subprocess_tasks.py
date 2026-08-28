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

import json
import logging
import multiprocessing as mp
import os
import tempfile
from typing import Any, Dict, List, Optional

from src.rag.chroma_compat import (
    get_or_create_collection_compatible,
    suppress_sentencepiece_swig_deprecation_warnings,
)
from src.rag.results import keyword_rank_raw_results


def rag_upsert_subprocess_entry(payload: Dict[str, Any], result_path: str):
    result = {"ok": False, "error": "unknown error"}
    try:
        collection = init_subprocess_collection(payload["persist_directory"])
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


def run_json_subprocess_task(
    *,
    target,
    payload: Dict[str, Any],
    timeout_seconds: int,
    temp_prefix: str,
    timeout_error: str,
    crash_error: str,
    missing_result_error: str,
    operation_error: str,
    setup_error: str,
    setup_error_arg: Any = None,
) -> Optional[Dict[str, Any]]:
    try:
        ctx = mp.get_context("spawn")
        fd, result_path = tempfile.mkstemp(prefix=temp_prefix, suffix=".json")
        os.close(fd)
        proc = ctx.Process(
            target=target,
            args=(payload, result_path),
            daemon=False,
        )
        proc.start()
        proc.join(timeout=timeout_seconds)
        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=5)
            logging.error(timeout_error)
            return None
        if proc.exitcode != 0:
            logging.error(crash_error, proc.exitcode)
            return None
        if not os.path.exists(result_path):
            logging.error(missing_result_error)
            return None
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        if not result.get("ok"):
            logging.error(operation_error, result.get("error"))
            return None
        return result
    except Exception as e:
        if setup_error_arg is None:
            logging.error(setup_error, e, exc_info=True)
        else:
            logging.error(setup_error, setup_error_arg, e, exc_info=True)
        return None
    finally:
        if "result_path" in locals():
            try:
                os.remove(result_path)
            except OSError:
                pass


def rag_upsert_in_subprocess(
    *,
    persist_directory: str,
    doc_id: str,
    text: str,
    metadata: Dict[str, Any],
    timeout_seconds: int = 30,
) -> bool:
    payload = {
        "persist_directory": persist_directory,
        "doc_id": doc_id,
        "text": text,
        "metadata": metadata,
    }
    result = run_json_subprocess_task(
        target=rag_upsert_subprocess_entry,
        payload=payload,
        timeout_seconds=timeout_seconds,
        temp_prefix="rag_upsert_",
        timeout_error=f"RAG subprocess upsert timed out for doc_id={doc_id}",
        crash_error=f"RAG subprocess upsert crashed for doc_id={doc_id} with exitcode=%s",
        missing_result_error=f"RAG subprocess upsert finished without result for doc_id={doc_id}",
        operation_error=f"RAG subprocess upsert error for doc_id={doc_id}: %s",
        setup_error="RAG subprocess upsert setup failed for doc_id=%s: %s",
        setup_error_arg=doc_id,
    )
    return result is not None


def rag_query_subprocess_entry(payload: Dict[str, Any], result_path: str):
    result = {"ok": False, "error": "unknown error"}
    try:
        collection = init_subprocess_collection(payload["persist_directory"])
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


def rag_query_in_subprocess(
    *,
    persist_directory: str,
    query: str,
    n_results: int,
    where: Dict[str, Any],
    timeout_seconds: int = 30,
) -> Optional[Dict[str, Any]]:
    payload = {
        "persist_directory": persist_directory,
        "query": query,
        "n_results": n_results,
        "where": where,
    }
    result = run_json_subprocess_task(
        target=rag_query_subprocess_entry,
        payload=payload,
        timeout_seconds=timeout_seconds,
        temp_prefix="rag_query_",
        timeout_error="RAG subprocess query timed out",
        crash_error="RAG subprocess query crashed with exitcode=%s",
        missing_result_error="RAG subprocess query finished without result file",
        operation_error="RAG subprocess query error: %s",
        setup_error="RAG subprocess query setup failed: %s",
    )
    return result.get("result") if result else None


def rag_keyword_search_subprocess_entry(payload: Dict[str, Any], result_path: str):
    result = {"ok": False, "error": "unknown error"}
    try:
        collection = init_subprocess_collection(payload["persist_directory"])
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


def rag_keyword_search_in_subprocess(
    *,
    persist_directory: str,
    query: str,
    n_results: int,
    where: Dict[str, Any],
    timeout_seconds: int = 30,
) -> List[Dict[str, Any]]:
    payload = {
        "persist_directory": persist_directory,
        "query": query,
        "n_results": n_results,
        "where": where,
    }
    result = run_json_subprocess_task(
        target=rag_keyword_search_subprocess_entry,
        payload=payload,
        timeout_seconds=timeout_seconds,
        temp_prefix="rag_kw_query_",
        timeout_error="RAG keyword subprocess query timed out",
        crash_error="RAG keyword subprocess query crashed with exitcode=%s",
        missing_result_error="RAG keyword subprocess query finished without result file",
        operation_error="RAG keyword subprocess query error: %s",
        setup_error="RAG keyword subprocess query setup failed: %s",
    )
    if not result:
        return []
    raw = result.get("result") or {}
    return keyword_rank_raw_results(raw, query, n_results)


def init_subprocess_collection(persist_directory: str):
    suppress_sentencepiece_swig_deprecation_warnings()

    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions

    chroma_settings = Settings(anonymized_telemetry=False)
    client = chromadb.PersistentClient(path=persist_directory, settings=chroma_settings)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return get_or_create_collection_compatible(
        client,
        name="transcriptions",
        embedding_fn=embedding_fn,
    )
