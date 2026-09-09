"""Semantic and keyword search orchestration for the RAG collection."""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.rag.filters import build_search_where_clause
from src.rag.results import parse_semantic_query_results


def search_documents(
    collection: Any,
    *,
    persist_directory: str,
    query: str,
    n_results: int,
    where_clause: Optional[Dict[str, Any]],
    ids: Optional[List[str]],
    use_subprocess: bool,
    semantic_query_enabled: bool,
    query_in_subprocess: Callable[..., Optional[Dict[str, Any]]],
    keyword_search_in_subprocess: Callable[..., List[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], bool]:
    """Return results and whether semantic subprocess search remains enabled."""
    final_where = build_search_where_clause(where_clause, ids)

    if not use_subprocess:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=final_where,
        )
        return parse_semantic_query_results(results), semantic_query_enabled

    if semantic_query_enabled:
        results = query_in_subprocess(
            persist_directory=persist_directory,
            query=query,
            n_results=n_results,
            where=final_where,
            timeout_seconds=30,
        )
        if results is not None:
            return parse_semantic_query_results(results), True

        logging.error(
            "RAG subprocess query failed. Disabling semantic query for this session "
            "and using keyword fallback."
        )
        semantic_query_enabled = False

    return (
        keyword_search_in_subprocess(
            persist_directory=persist_directory,
            query=query,
            n_results=n_results,
            where=final_where,
            timeout_seconds=30,
        ),
        semantic_query_enabled,
    )
