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

from typing import Any, Dict, List


def parse_semantic_query_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    parsed_results = []
    ids_outer = results.get("ids") or []
    docs_outer = results.get("documents") or []
    metas_outer = results.get("metadatas") or []
    dists_outer = results.get("distances") or []
    if not ids_outer:
        return parsed_results

    ids = ids_outer[0] or []
    docs = docs_outer[0] if docs_outer else []
    metas = metas_outer[0] if metas_outer else []
    dists = dists_outer[0] if dists_outer else []

    for i in range(len(ids)):
        metadata = metas[i] if i < len(metas) else {}
        if str((metadata or {}).get("deleted", "0")) == "1":
            continue
        parsed_results.append(
            {
                "id": ids[i],
                "text": docs[i] if i < len(docs) else "",
                "metadata": metadata or {},
                "distance": dists[i] if i < len(dists) else 0.0,
            }
        )
    return parsed_results


def keyword_rank_raw_results(raw: Dict[str, Any], query: str, n_results: int) -> List[Dict[str, Any]]:
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
        scored.append(
            {
                "id": doc_id,
                "text": text or "",
                "metadata": metadata or {},
                "distance": float(-score),
            }
        )
    scored.sort(key=lambda r: r["distance"])
    return scored[:n_results]
