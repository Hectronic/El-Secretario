# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for the Local REST API Server."""

import os
import json
import time
import socket
import urllib.request
import urllib.error
import pytest
from unittest.mock import MagicMock, patch

from src.api.server import LocalAPIServerThread


@pytest.fixture
def api_thread(qtbot):
    """Fixture to start and manage the Local REST API Thread."""
    thread = LocalAPIServerThread()
    # Mock databases and RAG dependencies to isolate the HTTP server
    thread.db = MagicMock()
    thread.rag = MagicMock()
    
    # Mock some default database fetch outputs
    thread.db.fetch_all.return_value = [
        {"id": 42, "title": "Mock Meeting", "created_at": "2026-09-15 10:00:00", "duration": 120, "summary": "Some summary", "tags": "sync,test"}
    ]
    thread.db.fetch_record.return_value = {
        "id": 42, "title": "Mock Meeting", "created_at": "2026-09-15 10:00:00", "duration": 120, "transcription": "Hello", "recording_notes": "None", "summary": "Some summary", "tags": "sync,test"
    }
    thread.db.get_tasks_for_board.return_value = [
        {"id": 1, "content": "Complete Spec 24", "notes": "Write tests", "day_date": "2026-09-15", "completed": 0}
    ]
    thread.db.save_task.return_value = 100
    
    thread.rag.search.return_value = [
        {"id": "42", "text": "RAG matching snippet", "distance": 0.1, "metadata": {"title": "Mock Meeting"}}
    ]

    # Run the QThread's run() method inside a standard Python threading.Thread.
    # This completely bypasses macOS-specific PyQt6 QThread scheduling deadlocks in headless/offscreen CI environments
    # while maintaining 100% of the PyQt signal and network functionalities.
    import threading
    t = threading.Thread(target=thread.run)
    t.daemon = True
    
    # Override stop() to close the server and wait for the Python thread cleanly
    original_stop = thread.stop
    def mock_stop():
        original_stop()
        t.join(2.0)
    thread.stop = mock_stop
    
    t.start()
    
    # Wait for the native thread to bind the socket and assign the port.
    # We use a 60-second limit (1200 * 0.05s) because macOS CI runners frequently suffer 
    # from a known ~30-second DNS lookup stall (socket.getaddrinfo) on the very first bind.
    attempts = 0
    while thread.port == 0 and attempts < 1200:
        time.sleep(0.05)
        attempts += 1
        
    assert thread.port > 0, f"Local REST API failed to start after 60s. Error: {getattr(thread, 'start_error', 'None')}"
    yield thread
    
    # Stop thread and cleanup
    thread.stop()


def _make_request(port: int, path: str, token: str = None, method: str = "GET", payload: dict = None) -> tuple[int, dict]:
    """Helper to perform localhost HTTP requests."""
    url = f"http://127.0.0.1:{port}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None

    # EXPLICITLY DISABLE PROXIES TO PREVENT CI/CD TIMEOUTS ON MACOS/WINDOWS RUNNERS!
    proxy_handler = urllib.request.ProxyHandler({})  # Bypasses any environment HTTP_PROXY
    opener = urllib.request.build_opener(proxy_handler)

    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with opener.open(req, timeout=5.0) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 599, {"error": str(e)}


def test_api_port_discovery(api_thread):
    """Test that app.port file is created with correct syntax."""
    port_filepath = os.path.abspath("app.port")
    assert os.path.exists(port_filepath)
    
    with open(port_filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        
    assert len(lines) == 2
    assert lines[0] == f"port={api_thread.port}"
    assert lines[1] == f"token={api_thread.token}"


def test_api_unauthorized_missing_token(api_thread):
    """Test that missing authorization headers return 401."""
    status, body = _make_request(api_thread.port, "/api/v1/status")
    assert status == 401
    assert "error" in body
    assert "Missing Bearer token" in body["error"]


def test_api_unauthorized_invalid_token(api_thread):
    """Test that invalid Bearer tokens return 401."""
    status, body = _make_request(api_thread.port, "/api/v1/status", token="invalid_token")
    assert status == 401
    assert "error" in body
    assert "Invalid Bearer token" in body["error"]


def test_api_get_status_idle(api_thread):
    """Test retrieving status when application is idle."""
    status, body = _make_request(api_thread.port, "/api/v1/status", token=api_thread.token)
    assert status == 200
    assert body["app_name"] == "El Secretario"
    assert body["status"] == "idle"
    assert body["active_recording"] is None


def test_api_get_status_recording(api_thread):
    """Test status values update correctly when recording is active."""
    api_thread.set_recording_status(True, mic_name="Blue Yeti", elapsed=30)
    
    status, body = _make_request(api_thread.port, "/api/v1/status", token=api_thread.token)
    assert status == 200
    assert body["status"] == "recording"
    assert body["active_recording"]["audio_device"] == "Blue Yeti"
    assert body["active_recording"]["elapsed_seconds"] == 30


def test_api_get_recordings_list(api_thread):
    """Test getting paginated historical recordings list."""
    status, body = _make_request(api_thread.port, "/api/v1/recordings", token=api_thread.token)
    assert status == 200
    assert len(body) == 1
    assert body[0]["id"] == 42
    assert body[0]["title"] == "Mock Meeting"
    assert "sync" in body[0]["tags"]


def test_api_get_recording_detail_by_id(api_thread):
    """Test getting full transcript and details for specific recording."""
    status, body = _make_request(api_thread.port, "/api/v1/recordings/42", token=api_thread.token)
    assert status == 200
    assert body["id"] == 42
    assert body["title"] == "Mock Meeting"
    assert body["transcript"] == "Hello"


def test_api_get_tasks(api_thread):
    """Test getting task board cards."""
    status, body = _make_request(api_thread.port, "/api/v1/tasks", token=api_thread.token)
    assert status == 200
    assert len(body) == 1
    assert body[0]["id"] == 1
    assert body[0]["title"] == "Complete Spec 24"


def test_api_post_task_create(api_thread, qtbot):
    """Test creating a task programmatically emits correctly and saves to DB."""
    # Listen to sig_create_task signal using qtbot
    with qtbot.wait_signal(api_thread.signals.sig_create_task) as blocker:
        status, body = _make_request(
            api_thread.port,
            "/api/v1/tasks",
            token=api_thread.token,
            method="POST",
            payload={"title": "External Task", "description": "Notes", "due_date": "2026-09-18"}
        )
        
    assert status == 201
    assert body["success"] is True
    assert body["task_id"] == 100
    
    # Verify database was called with matching values
    api_thread.db.save_task.assert_called_with(
        record_id=None,
        content="External Task",
        notes="Notes",
        day_date="2026-09-18",
        task_origin="local_api"
    )
    
    # Verify PyQt signal emitted details
    assert blocker.args[0]["title"] == "External Task"
    assert blocker.args[0]["description"] == "Notes"


def test_api_post_record_start_signal(api_thread, qtbot):
    """Test that POST /api/v1/record/start safely triggers the start_recording signal."""
    with qtbot.wait_signal(api_thread.signals.sig_start_recording):
        status, body = _make_request(
            api_thread.port,
            "/api/v1/record/start",
            token=api_thread.token,
            method="POST"
        )
        
    assert status == 200
    assert body["success"] is True


def test_api_post_record_stop_signal(api_thread, qtbot):
    """Test that POST /api/v1/record/stop safely triggers the stop_recording signal."""
    # Set recording status so stop is allowed
    api_thread.set_recording_status(True)
    
    with qtbot.wait_signal(api_thread.signals.sig_stop_recording):
        status, body = _make_request(
            api_thread.port,
            "/api/v1/record/stop",
            token=api_thread.token,
            method="POST"
        )
        
    assert status == 200
    assert body["success"] is True


def test_api_get_search(api_thread):
    """Test getting semantic search query results."""
    status, body = _make_request(
        api_thread.port,
        "/api/v1/search?query=hello",
        token=api_thread.token
    )
    assert status == 200
    assert body["query"] == "hello"
    assert len(body["results"]) == 1
    assert body["results"][0]["text"] == "RAG matching snippet"
    assert body["results"][0]["relevance_score"] == 0.9


def test_api_get_recording_invalid_id_type(api_thread):
    """Test retrieving a recording with an invalid non-integer ID returns 500 error."""
    status, body = _make_request(api_thread.port, "/api/v1/recordings/not-an-integer", token=api_thread.token)
    assert status == 500
    assert body["success"] is False
    assert "error" in body


def test_api_post_task_missing_title(api_thread):
    """Test that creating a task with a missing title returns 400 error."""
    status, body = _make_request(
        api_thread.port,
        "/api/v1/tasks",
        token=api_thread.token,
        method="POST",
        payload={"description": "No title given"}
    )
    assert status == 400
    assert body["success"] is False
    assert "title is required" in body["error"]


def test_api_post_task_malformed_json(api_thread):
    """Test that submitting malformed/invalid JSON syntax returns 400 error."""
    url = f"http://127.0.0.1:{api_thread.port}/api/v1/tasks"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_thread.token}", "Content-Type": "application/json"},
        method="POST",
        data=b"invalid { json string"
    )
    try:
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(req) as res:
            pytest.fail("Should have failed")
    except urllib.error.HTTPError as e:
        assert e.code == 400
        body = json.loads(e.read().decode("utf-8"))
        assert body["success"] is False
        assert "Invalid JSON" in body["error"]


def test_api_not_found_route(api_thread):
    """Test that calling a non-existent path returns a 404 error."""
    status, body = _make_request(api_thread.port, "/api/v1/non-existent-endpoint", token=api_thread.token)
    assert status == 404
    assert body["success"] is False
    assert "not found" in body["error"]


def test_api_options_preflight(api_thread):
    """Test that OPTIONS CORS preflight queries return 200 OK and headers."""
    url = f"http://127.0.0.1:{api_thread.port}/api/v1/status"
    req = urllib.request.Request(url, method="OPTIONS")
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    with opener.open(req) as res:
        assert res.status == 200
        assert res.headers.get("Access-Control-Allow-Origin") == "*"
        assert "GET" in res.headers.get("Access-Control-Allow-Methods")


@patch("src.api.server.ThreadingHTTPServer")
def test_api_port_collision_and_retries(mock_server):
    """Test that port collisions (e.g. Address already in use) set start_error and terminate cleanly."""
    mock_server.side_effect = OSError(98, "Address already in use")
    
    thread = LocalAPIServerThread()
    thread.db = MagicMock()
    thread.rag = MagicMock()
    
    # Execute run directly to capture outcomes instantly in the main thread
    thread.run()
    
    assert thread.port == 0
    assert "Address already in use" in getattr(thread, "start_error", "")

