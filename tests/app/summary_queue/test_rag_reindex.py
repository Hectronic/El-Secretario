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

import pytest

from src.app.summary_queue.rag_reindex import (
    build_rag_metadata,
    collect_reindex_candidates,
    is_indexed_in_rag,
    normalize_reindex_scope,
    run_rag_reindex,
)


class _FakeDb:
    def __init__(self, records, ai_text_by_id):
        self.records = records
        self.ai_text_by_id = ai_text_by_id

    def fetch_all(self):
        return list(self.records)

    def get_record_ai_text(self, record_id):
        return self.ai_text_by_id.get(record_id, "")


class _FakeCollection:
    def __init__(self, indexed_ids):
        self.indexed_ids = {str(item) for item in indexed_ids}

    def get(self, ids, where=None):  # noqa: ARG002
        return {"ids": [item for item in ids if str(item) in self.indexed_ids]}


class _FakeRag:
    def __init__(self, indexed_ids=None, fail_ids=None):
        self.indexed_ids = {str(item) for item in (indexed_ids or [])}
        self.collection = _FakeCollection(self.indexed_ids)
        self.fail_ids = set(fail_ids or [])
        self.indexed = []

    def search(self, *_args, ids=None, **_kwargs):
        return [item for item in (ids or []) if str(item) in self.indexed_ids]

    def add_document(self, record_id, text, metadata=None):
        if record_id in self.fail_ids:
            raise RuntimeError("index failed")
        self.indexed.append((record_id, text, dict(metadata or {})))


def test_normalize_reindex_scope_accepts_only_supported_values():
    assert normalize_reindex_scope("missing") == "missing"
    assert normalize_reindex_scope("ALL") == "all"
    assert normalize_reindex_scope("bad") == "all"


def test_build_rag_metadata_uses_record_defaults():
    assert build_rag_metadata({"id": 3}) == {
        "title": "Record 3",
        "date": "",
        "tags": "",
        "type": "recording",
    }


def test_is_indexed_in_rag_uses_collection_then_search_fallback():
    assert is_indexed_in_rag(_FakeRag(indexed_ids=[1]), 1) is True

    rag = _FakeRag(indexed_ids=[2])
    rag.collection = None
    assert is_indexed_in_rag(rag, 2) is True


def test_collect_reindex_candidates_filters_invalid_empty_and_indexed_records():
    db = _FakeDb(
        [
            {"id": 1, "type": "recording", "title": "Ready"},
            {"id": 2, "type": "note", "title": "Already indexed"},
            {"id": 3, "type": "other", "title": "Ignored type"},
            {"id": "4", "type": "recording", "title": "Ignored id"},
            {"id": 5, "type": "recording", "title": "Empty text"},
        ],
        {1: "Text 1", 2: "Text 2", 5: ""},
    )

    candidates = collect_reindex_candidates(db, _FakeRag(indexed_ids=[2]), scope="missing")

    assert [(record["id"], text) for record, text in candidates] == [(1, "Text 1")]


def test_run_rag_reindex_indexes_candidates_and_reports_progress():
    db = _FakeDb(
        [
            {"id": 1, "type": "recording", "title": "One", "tags": "a"},
            {"id": 2, "type": "note", "title": "Two", "tags": "b"},
        ],
        {1: "Text 1", 2: "Text 2"},
    )
    rag = _FakeRag()
    statuses = []
    progress = []

    result = run_rag_reindex(db, rag, on_status=statuses.append, on_progress=progress.append)

    assert result == {"indexed": 2, "skipped": 0, "total": 2}
    assert [item[0] for item in rag.indexed] == [1, 2]
    assert progress[-1] == 100
    assert statuses == ["RAG reindex: 1/2", "RAG reindex: 2/2"]


def test_run_rag_reindex_reports_empty_and_missing_engine():
    db = _FakeDb([], {})
    statuses = []
    progress = []

    assert run_rag_reindex(db, _FakeRag(), on_status=statuses.append, on_progress=progress.append) == {
        "indexed": 0,
        "skipped": 0,
        "total": 0,
    }
    assert statuses == ["RAG reindex: no eligible records found."]
    assert progress == [100]

    with pytest.raises(RuntimeError, match="RAG engine is not initialized"):
        run_rag_reindex(db, None)


def test_run_rag_reindex_counts_failures_and_honors_interruption():
    db = _FakeDb(
        [
            {"id": 1, "type": "recording"},
            {"id": 2, "type": "recording"},
            {"id": 3, "type": "recording"},
        ],
        {1: "Text 1", 2: "Text 2", 3: "Text 3"},
    )
    rag = _FakeRag(fail_ids=[2])
    calls = {"count": 0}

    def is_interrupted():
        calls["count"] += 1
        return calls["count"] > 2

    result = run_rag_reindex(db, rag, is_interrupted=is_interrupted)

    assert result == {"indexed": 1, "skipped": 1, "total": 3}
    assert [item[0] for item in rag.indexed] == [1]
