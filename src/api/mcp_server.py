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

"""Model Context Protocol (MCP) Server Integration for El Secretario."""

import os
import sys
import json
import logging
import urllib.request
import urllib.error

# Ensure PyQt settings are checkable on startup
try:
    from PyQt6.QtCore import QSettings
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

# Enforce strict privacy: check if MCP integration is enabled in settings
mcp_enabled = False
if HAS_PYQT:
    try:
        settings = QSettings("Hectronic", "Secretario")
        val = settings.value("enable_mcp_server", False)
        if isinstance(val, str):
            mcp_enabled = val.lower() == "true"
        else:
            mcp_enabled = bool(val)
    except Exception:
        pass

if not mcp_enabled:
    sys.stderr.write("[ERROR] Model Context Protocol (MCP) Server Integration is disabled in El Secretario Settings.\n")
    sys.stderr.write("[INFO] Please enable it in Settings -> Local REST API / MCP to use this feature.\n")
    sys.exit(1)


# Import FastMCP now that privacy check has succeeded
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.stderr.write("[ERROR] Official Python MCP SDK 'mcp' is not installed in the virtual environment.\n")
    sys.exit(1)

# Initialize FastMCP Server
mcp = FastMCP("El Secretario")


def discover_api_credentials() -> tuple[int, str]:
    """Reads the dynamic app.port file in the project directory to retrieve port and token."""
    # Find app.port in current folder, or go up 2 directories if started from src/api
    candidates = [
        os.path.abspath("app.port"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app.port")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.port")),
    ]
    
    port_filepath = None
    for path in candidates:
        if os.path.exists(path):
            port_filepath = path
            break
            
    if not port_filepath:
        raise RuntimeError("El Secretario REST API port-discovery file 'app.port' not found. Is El Secretario running with Local API enabled?")
        
    port = 0
    token = ""
    with open(port_filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("port="):
                port = int(line.split("=")[1].strip())
            elif line.startswith("token="):
                token = line.split("=")[1].strip()
                
    if port == 0 or not token:
        raise RuntimeError("Incomplete port discovery parameters found in app.port.")
        
    return port, token


def make_api_request(path: str, method: str = "GET", payload: dict = None) -> dict:
    """Performs an authorized HTTP loopback request to El Secretario Local API (SPEC-024)."""
    port, token = discover_api_credentials()
    url = f"http://127.0.0.1:{port}/api/v1{path}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None
        
    # Strictly bypass any system/environment HTTP_PROXY settings
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        with opener.open(req, timeout=5.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            raise RuntimeError(f"API Error ({e.code}): {err_body.get('error', e.reason)}")
        except Exception:
            raise RuntimeError(f"API Error ({e.code}): {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to local API: {e}")


# =====================================================================
# MCP Resources
# =====================================================================

@mcp.resource("secretario://transcriptions")
def list_transcriptions() -> str:
    """Lists all available meeting recordings and transcripts with metadata."""
    try:
        recordings = make_api_request("/recordings")
        if not recordings:
            return "No transcriptions available."
        return json.dumps(recordings, indent=2)
    except Exception as e:
        return f"Error listing transcriptions: {e}"


@mcp.resource("secretario://transcriptions/{id}")
def read_transcription(id: int) -> str:
    """Reads the raw text transcript, notes, and generated summary of a specific meeting."""
    try:
        rec = make_api_request(f"/recordings/{id}")
        
        output = [
            f"=== {rec.get('title', 'Untitled Meeting')} ===",
            f"Date: {rec.get('date', 'Unknown')}",
            f"Duration: {rec.get('duration_seconds', 0)} seconds",
            f"Tags: {', '.join(rec.get('tags', []))}\n",
            "--- Summary ---",
            rec.get("summary", "No summary generated.") or "No summary generated.",
            "\n--- Notes ---",
            rec.get("notes", "No notes saved.") or "No notes saved.",
            "\n--- Raw Transcript ---",
            rec.get("transcript", "No transcript text.") or "No transcript text."
        ]
        return "\n".join(output)
    except Exception as e:
        return f"Error reading transcription {id}: {e}"


@mcp.resource("secretario://tasks/active")
def list_active_tasks() -> str:
    """Lists all active task cards from El Secretario's task board."""
    try:
        tasks = make_api_request("/tasks")
        active_tasks = [t for t in tasks if not t.get("completed")]
        if not active_tasks:
            return "No active tasks on the board."
        return json.dumps(active_tasks, indent=2)
    except Exception as e:
        return f"Error listing active tasks: {e}"


# =====================================================================
# MCP Tools
# =====================================================================

@mcp.tool()
def search_knowledge(query: str) -> str:
    """Queries El Secretario's transcriptions, notes, and summaries using semantic (RAG) and keyword search.

    Args:
        query: The semantic or keyword text to search for (e.g. 'project timeline discussions').
    """
    try:
        res = make_api_request(f"/search?query={urllib.parse.quote(query)}")
        results = res.get("results", [])
        if not results:
            return f"No search results matched query: '{query}'"
            
        output = [f"Search Results for query: '{query}'\n"]
        for i, doc in enumerate(results, 1):
            score = doc.get("relevance_score", 1.0)
            output.append(
                f"{i}. [{doc.get('title', 'Untitled')}] (Relevance: {score * 100:.1f}%)\n"
                f"   Snippet: \"{doc.get('text', '')}\"\n"
            )
        return "\n".join(output)
    except Exception as e:
        return f"Error searching knowledge: {e}"


@mcp.tool()
def start_recording() -> str:
    """Remotely starts a new live microphone audio recording session in El Secretario's UI."""
    try:
        res = make_api_request("/record/start", method="POST")
        return res.get("message", "Recording started successfully.")
    except Exception as e:
        return f"Error starting recording: {e}"


@mcp.tool()
def stop_recording() -> str:
    """Remotely stops the active audio recording session, saving and sending it to the transcription queue."""
    try:
        res = make_api_request("/record/stop", method="POST")
        return res.get("message", "Recording stopped successfully.")
    except Exception as e:
        return f"Error stopping recording: {e}"


@mcp.tool()
def create_task(title: str, description: str = "", due_date: str = "") -> str:
    """Programmatically appends a new task card onto El Secretario's task board database.

    Args:
        title: Short summary or title of the task.
        description: Optional detailed notes or description.
        due_date: Optional due date in format 'YYYY-MM-DD'.
    """
    try:
        payload = {
            "title": title,
            "description": description,
            "due_date": due_date
        }
        res = make_api_request("/tasks", method="POST", payload=payload)
        return f"Success: Task created on board with ID: {res.get('task_id')}."
    except Exception as e:
        return f"Error creating task: {e}"


if __name__ == "__main__":
    # FastMCP starts the stdio server automatically when executed
    mcp.run()
