"""Document write and delete operations for the RAG collection."""

import logging
from typing import Any, Callable, Dict, Optional


def add_document(
    collection: Any,
    *,
    persist_directory: str,
    doc_id: str,
    text: str,
    metadata: Optional[Dict[str, Any]],
    use_subprocess: bool,
    upsert_in_subprocess: Callable[..., bool],
) -> None:
    """Index a document, preserving the Windows-safe subprocess path."""
    if not text:
        return

    stored_metadata = dict(metadata or {})
    stored_metadata["id"] = str(doc_id)
    stored_metadata["deleted"] = "0"

    if use_subprocess:
        ok = upsert_in_subprocess(
            persist_directory=persist_directory,
            doc_id=str(doc_id),
            text=text,
            metadata=stored_metadata,
            timeout_seconds=30,
        )
        if not ok:
            logging.error(
                "RAG subprocess upsert failed for doc_id=%s. "
                "Skipping in-process fallback on Windows for stability.",
                doc_id,
            )
        return

    collection.upsert(
        ids=[str(doc_id)],
        documents=[text],
        metadatas=[stored_metadata],
    )


def delete_document(
    collection: Any,
    *,
    persist_directory: str,
    doc_id: str,
    safe_delete_mode: bool,
    use_subprocess: bool,
    upsert_in_subprocess: Callable[..., bool],
) -> None:
    """Delete a document, using soft deletion where native delete is unsafe."""
    sid = str(doc_id)
    try:
        if safe_delete_mode:
            if use_subprocess:
                ok = upsert_in_subprocess(
                    persist_directory=persist_directory,
                    doc_id=sid,
                    text="",
                    metadata={"id": sid, "deleted": "1"},
                    timeout_seconds=30,
                )
                message = "RAG soft-delete %s for doc_id=%s (safe_delete_mode, subprocess)"
            else:
                collection.upsert(
                    ids=[sid],
                    documents=[""],
                    metadatas=[{"id": sid, "deleted": "1"}],
                )
                ok = True
                message = "RAG soft-delete %s for doc_id=%s (safe_delete_mode)"

            logging.log(
                logging.INFO if ok else logging.ERROR,
                message,
                "applied" if ok else "failed",
                sid,
            )
            return

        collection.delete(ids=[sid])
        logging.info("RAG hard-delete applied for doc_id=%s", sid)
    except Exception as error:
        logging.error("Error deleting document %s: %s", doc_id, error, exc_info=True)
