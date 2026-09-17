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

"""Tests for the Model Context Protocol (MCP) Server Integration."""

import os
import sys
import json
import subprocess
import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QSettings

# Ensure mcp server is enabled in settings before import so the startup check doesn't sys.exit(1)
settings = QSettings("Hectronic", "Secretario")
settings.setValue("enable_mcp_server", True)

# Now we can import mcp_server safely
from src.api.mcp_server import (
    list_transcriptions,
    read_transcription,
    list_active_tasks,
    search_knowledge,
    start_recording,
    stop_recording,
    create_task,
)


def test_mcp_server_terminated_when_disabled():
    """Test that the MCP server process exits cleanly with error code 1 when disabled in settings."""
    # Force settings value to False and flush to disk
    settings.setValue("enable_mcp_server", False)
    settings.sync()
    
    # Run mcp_server.py as a separate process in the virtual environment
    proc = subprocess.run(
        [sys.executable, "src/api/mcp_server.py"],
        capture_output=True,
        text=True,
        timeout=5.0
    )
    
    assert proc.returncode == 1
    assert "Server Integration is disabled" in proc.stderr
    
    # Re-enable so other tests have clean environment
    settings.setValue("enable_mcp_server", True)
    settings.sync()


@patch("src.api.mcp_server.make_api_request")
def test_list_transcriptions_resource(mock_request):
    """Test list_transcriptions formats JSON correctly from local API payload."""
    mock_request.return_value = [
        {"id": 42, "title": "Team Sync", "date": "2026-09-15 10:00:00", "duration_seconds": 60, "summary_generated": True, "tags": ["test"]}
    ]
    
    output = list_transcriptions()
    data = json.loads(output)
    
    assert len(data) == 1
    assert data[0]["id"] == 42
    assert data[0]["title"] == "Team Sync"
    mock_request.assert_called_with("/recordings")


@patch("src.api.mcp_server.make_api_request")
def test_read_transcription_resource(mock_request):
    """Test read_transcription displays prettified layout of transcript details."""
    mock_request.return_value = {
        "id": 42,
        "title": "Team Sync",
        "date": "2026-09-15 10:00:00",
        "duration_seconds": 60,
        "transcript": "Hello World",
        "notes": "Some notes",
        "summary": "Meeting summary",
        "tags": ["sync"]
    }
    
    output = read_transcription(42)
    
    assert "=== Team Sync ===" in output
    assert "Meeting summary" in output
    assert "Some notes" in output
    assert "Hello World" in output
    mock_request.assert_called_with("/recordings/42")


@patch("src.api.mcp_server.make_api_request")
def test_list_active_tasks_resource(mock_request):
    """Test list_active_tasks successfully filters out completed task cards."""
    mock_request.return_value = [
        {"id": 1, "title": "Task A", "completed": False},
        {"id": 2, "title": "Task B", "completed": True}
    ]
    
    output = list_active_tasks()
    data = json.loads(output)
    
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["title"] == "Task A"
    mock_request.assert_called_with("/tasks")


@patch("src.api.mcp_server.make_api_request")
def test_search_knowledge_tool(mock_request):
    """Test search_knowledge formats relevance scores as percentages."""
    mock_request.return_value = {
        "results": [
            {"title": "Dev Sync", "text": "We discussed installers...", "relevance_score": 0.89}
        ]
    }
    
    output = search_knowledge("installers")
    
    assert "Dev Sync" in output
    assert "Relevance: 89.0%" in output
    assert "Snippet: \"We discussed installers...\"" in output
    mock_request.assert_called_with("/search?query=installers")


@patch("src.api.mcp_server.make_api_request")
def test_record_actions_tools(mock_request):
    """Test that start/stop recording tools call correct REST POST routes."""
    mock_request.return_value = {"message": "Success"}
    
    out_start = start_recording()
    assert out_start == "Success"
    mock_request.assert_any_call("/record/start", method="POST")
    
    out_stop = stop_recording()
    assert out_stop == "Success"
    mock_request.assert_any_call("/record/stop", method="POST")


@patch("src.api.mcp_server.make_api_request")
def test_create_task_tool(mock_request):
    """Test create_task maps tool arguments to correct POST API payload."""
    mock_request.return_value = {"task_id": 105}
    
    output = create_task(title="New Task", description="Notes", due_date="2026-09-18")
    
    assert "Task created on board with ID: 105" in output
    mock_request.assert_called_with(
        "/tasks",
        method="POST",
        payload={"title": "New Task", "description": "Notes", "due_date": "2026-09-18"}
    )
