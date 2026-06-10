# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import logging

from src.rag import subprocess_tasks
from src.rag.subprocess_tasks import (
    rag_keyword_search_in_subprocess,
    rag_query_in_subprocess,
    rag_upsert_in_subprocess,
    run_json_subprocess_task,
)
from tests.rag import subprocess_targets


def _run_task(target, payload=None, timeout_seconds=2):
    return run_json_subprocess_task(
        target=target,
        payload=payload or {},
        timeout_seconds=timeout_seconds,
        temp_prefix="rag_subprocess_test_",
        timeout_error="timeout happened",
        crash_error="crash happened exitcode=%s",
        missing_result_error="missing result happened",
        operation_error="operation happened: %s",
        setup_error="setup happened: %s",
    )


def test_run_json_subprocess_task_returns_success_result():
    assert _run_task(subprocess_targets.write_success, {"result": {"value": 1}}) == {
        "ok": True,
        "result": {"value": 1},
    }


def test_run_json_subprocess_task_reports_operation_error(caplog):
    with caplog.at_level(logging.ERROR):
        result = _run_task(subprocess_targets.write_operation_error, {"error": "bad op"})

    assert result is None
    assert "operation happened: bad op" in caplog.text


def test_run_json_subprocess_task_reports_missing_result(caplog):
    with caplog.at_level(logging.ERROR):
        result = _run_task(subprocess_targets.remove_result_file)

    assert result is None
    assert "missing result happened" in caplog.text


def test_run_json_subprocess_task_reports_crash(caplog):
    with caplog.at_level(logging.ERROR):
        result = _run_task(subprocess_targets.crash_process)

    assert result is None
    assert "crash happened exitcode=" in caplog.text


def test_run_json_subprocess_task_reports_timeout(caplog):
    with caplog.at_level(logging.ERROR):
        result = _run_task(subprocess_targets.sleep_past_timeout, timeout_seconds=0.1)

    assert result is None
    assert "timeout happened" in caplog.text


def test_rag_upsert_in_subprocess_returns_boolean_from_runner(monkeypatch):
    calls = []

    def fake_run_json_subprocess_task(**kwargs):
        calls.append(kwargs)
        return {"ok": True}

    monkeypatch.setattr(subprocess_tasks, "run_json_subprocess_task", fake_run_json_subprocess_task)

    assert rag_upsert_in_subprocess(
        persist_directory="db",
        doc_id="doc1",
        text="hello",
        metadata={"id": "doc1"},
        timeout_seconds=7,
    )
    assert calls[0]["payload"] == {
        "persist_directory": "db",
        "doc_id": "doc1",
        "text": "hello",
        "metadata": {"id": "doc1"},
    }
    assert calls[0]["timeout_seconds"] == 7


def test_rag_query_in_subprocess_returns_nested_query_result(monkeypatch):
    monkeypatch.setattr(
        subprocess_tasks,
        "run_json_subprocess_task",
        lambda **_kwargs: {"ok": True, "result": {"ids": [["1"]]}},
    )

    assert rag_query_in_subprocess(
        persist_directory="db",
        query="hello",
        n_results=3,
        where={"deleted": {"$ne": "1"}},
    ) == {"ids": [["1"]]}


def test_rag_keyword_search_in_subprocess_ranks_runner_raw_results(monkeypatch):
    monkeypatch.setattr(
        subprocess_tasks,
        "run_json_subprocess_task",
        lambda **_kwargs: {
            "ok": True,
            "result": {
                "ids": ["a", "b"],
                "documents": ["apple", "apple apple"],
                "metadatas": [{}, {}],
            },
        },
    )

    ranked = rag_keyword_search_in_subprocess(
        persist_directory="db",
        query="apple",
        n_results=2,
        where={"deleted": {"$ne": "1"}},
    )

    assert [result["id"] for result in ranked] == ["b", "a"]

