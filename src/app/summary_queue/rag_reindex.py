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

from typing import Any, Callable, Dict, List, Tuple


def normalize_reindex_scope(scope: str = "all") -> str:
    normalized = (scope or "all").strip().lower()
    return normalized if normalized in {"all", "missing"} else "all"


def is_indexed_in_rag(rag_engine, record_id: int) -> bool:
    sid = str(record_id)
    try:
        collection = getattr(rag_engine, "collection", None)
        if collection is not None and hasattr(collection, "get"):
            raw = collection.get(ids=[sid], where={"deleted": {"$ne": "1"}})
            return bool(raw and raw.get("ids"))
    except Exception:
        pass

    try:
        hits = rag_engine.search("", n_results=1, ids=[sid])
        return bool(hits)
    except Exception:
        return False


def build_rag_metadata(record: Dict[str, Any]) -> Dict[str, Any]:
    rec_id = record.get("id")
    title = (record.get("title") or f"Record {rec_id}").strip()
    return {
        "title": title,
        "date": record.get("created_at") or "",
        "tags": record.get("tags") or "",
        "type": record.get("type") or "recording",
    }


def collect_reindex_candidates(db, rag_engine, scope: str = "all") -> List[Tuple[Dict[str, Any], str]]:
    normalized_scope = normalize_reindex_scope(scope)
    candidates = []
    for rec in db.fetch_all():
        rec_id = rec.get("id")
        if not isinstance(rec_id, int):
            continue
        rec_type = str(rec.get("type") or "recording")
        if rec_type not in {"recording", "note"}:
            continue
        ai_text = db.get_record_ai_text(rec_id)
        if not str(ai_text or "").strip():
            continue
        if normalized_scope == "missing" and is_indexed_in_rag(rag_engine, rec_id):
            continue
        candidates.append((rec, ai_text))
    return candidates


def run_rag_reindex(
    db,
    rag_engine,
    scope: str = "all",
    *,
    is_interrupted: Callable[[], bool] = lambda: False,
    on_status: Callable[[str], None] = lambda _message: None,
    on_progress: Callable[[int], None] = lambda _value: None,
) -> Dict[str, int]:
    if rag_engine is None:
        raise RuntimeError("RAG engine is not initialized.")

    candidates = collect_reindex_candidates(db, rag_engine, scope)
    total = len(candidates)
    if total == 0:
        on_status("RAG reindex: no eligible records found.")
        on_progress(100)
        return {"indexed": 0, "skipped": 0, "total": 0}

    indexed = 0
    skipped = 0
    for idx, (rec, ai_text) in enumerate(candidates, start=1):
        if is_interrupted():
            on_status("RAG reindex interrupted.")
            break

        rec_id = rec.get("id")
        try:
            rag_engine.add_document(rec_id, ai_text, metadata=build_rag_metadata(rec))
            indexed += 1
        except Exception:
            skipped += 1

        if idx == 1 or idx % 25 == 0 or idx == total:
            on_status(f"RAG reindex: {idx}/{total}")
        on_progress(int((idx / total) * 100))

    return {"indexed": indexed, "skipped": skipped, "total": total}

