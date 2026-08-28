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

from typing import Any, Dict, Optional


class InMemoryCollection:
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


class InMemoryChromaClient:
    """Minimal client fallback exposing get_or_create_collection."""

    def __init__(self):
        self._collections: Dict[str, InMemoryCollection] = {}

    def get_or_create_collection(self, name, embedding_function=None):  # noqa: ARG002
        if name not in self._collections:
            self._collections[name] = InMemoryCollection()
        return self._collections[name]
