# SPEC-025: Model Context Protocol (MCP) Server Integration

Status: Implemented
Owner: Héctor Álvarez López <hectoralvarez.me>
Last updated: 2026-09-15

## Problem

Users of advanced AI agents and developer-focused chat clients (such as Claude Desktop, Cursor, or other MCP-compatible orchestration environments) want to directly interact with the rich meeting transcriptions, summaries, RAG-indexed knowledge, and task boards accumulated inside "El Secretario".

Rather than forcing the user to manually export data or copy-paste text, "El Secretario" needs to operate as a standardized Model Context Protocol (MCP) server. Exposing its data and actions as standard MCP Resources and Tools allows external local LLMs to reason with and trigger actions inside the app in real-time.

## Scope

- **In scope:**
  - A standalone, stdio-transport Python script `src/api/mcp_server.py` that utilizes the official Python Model Context Protocol SDK.
  - Integration with the Local REST API (SPEC-024) acting as a secure, fast, and loopback HTTP client proxy, completely preventing direct SQLite file locks, race conditions, or Qt thread memory corruption.
  - **Exposing Resources:**
    - `secretario://transcriptions` (List of metadata for all saved recordings).
    - `secretario://transcriptions/{id}` (Raw text content, notes, and summaries of a specific meeting).
    - `secretario://tasks/active` (Detailed list of active tasks on the board).
  - **Exposing Tools:**
    - `search_knowledge(query)` (Queries the semantic RAG database and keyword search via the API).
    - `start_recording()` (Remotely starts recording in the active GUI).
    - `stop_recording()` (Stops recording, initiates transcription, and saves the file).
    - `create_task(title, description, due_date)` (Remotely inserts a task card on the board).
  - A settings general panel checkbox toggle (`enable_mcp_integration`) with QSettings persistence.
  - A UX utility button "Copy Claude Desktop Config" that automatically copies the required JSON configuration snippet to the clipboard for frictionless user setup.
- **Out of scope:**
  - Standard MCP over SSE (Server-Sent Events) network transports (stdio transport is preferred and standard for local desktop integration).
  - Audio streaming or diarization processing over the MCP protocol (only text metadata, transcripts, and JSON states are exchanged).

## Architecture & Integration Strategy

```
 +------------------------+              +------------------------+
 |     Claude Desktop     |              |     El Secretario      |
 |  (or other MCP Client) |              |  (Local REST API Thread)|
 |           |            |              |           |            |
 |    STDIO (JSON-RPC)    |              |       HTTP Local       |
 |           |            |              |       Loopback         |
 |           v            |              |           v            |
 |  src/api/mcp_server.py |=============| GET/POST localhost:port|
 |   (MCP Server Process) |  (REST client)                      |
 +------------------------+              +------------------------+
```

### 1. Standalone Proxy Pattern
To protect the desktop app's memory and ensure absolute stability:
- The MCP Server runs as an isolated, standalone Python process spawned on-demand by the MCP Client (like Claude Desktop) using standard stdio.
- Upon startup, the MCP Server reads the local dynamic port discovery file `{user_data_dir}/app.port` to find the active Local REST API port and single-use Bearer token.
- When an MCP Client requests a resource or calls a tool, the MCP Server formats the request and queries the **Local REST API (SPEC-024)** over local loopback HTTP.
- This proxy pattern is highly secure: it strictly respects the toggles, authentication tokens, and safe thread bridging implemented in Spec-024.

### 2. UI Setting & Configuration Copy Helper
In `src/ui/settings/general_panel.py`:
- **"Enable MCP Server Integration"** checkbox (persisted as `enable_mcp_server`). If checked, the launcher allows the MCP process. If unchecked, the MCP proxy process instantly rejects connection attempts, enforcing strict privacy.
- **"Copy Claude Desktop Config"** button:
  - Generates the exact JSON block matching the current environment:
    ```json
    {
      "mcpServers": {
        "el-secretario": {
          "command": "python",
          "args": [
            "/path/to/El-Secretario/src/api/mcp_server.py"
          ],
          "env": {
            "PYTHONPATH": "/path/to/El-Secretario"
          }
        }
      }
    }
    ```
  - Copies this JSON directly to the user's system clipboard, enabling a 1-click configuration experience!

## MCP Protocol Specifications

### 1. Resources

#### `secretario://transcriptions`
- **Description:** Lists all available meetings, recordings, and transcripts with metadata (IDs, titles, dates, durations).
- **MimeType:** `application/json`

#### `secretario://transcriptions/{id}`
- **Description:** Exposes the full transcript, summaries, and notes of a specific meeting for LLM comprehension.
- **MimeType:** `text/plain` or `application/json`

#### `secretario://tasks/active`
- **Description:** Exposes the board of active task cards.
- **MimeType:** `application/json`

### 2. Tools

#### `search_knowledge`
- **Schema:**
  ```json
  {
    "query": {
      "type": "string",
      "description": "The search query (semantic or keyword) to search in transcripts, notes, and summaries."
    }
  }
  ```
- **Returns:** List of search snippets, titles, dates, and relevance scores.

#### `start_recording`
- **Schema:** `{}`
- **Returns:** Success confirmation string. Triggers physical GUI microphone capture.

#### `stop_recording`
- **Schema:** `{}`
- **Returns:** Success confirmation string and temporary ID of the generated session.

#### `create_task`
- **Schema:**
  ```json
  {
    "title": { "type": "string", "description": "Short summary of the task." },
    "description": { "type": "string", "description": "Optional notes or details." },
    "due_date": { "type": "string", "description": "Optional due date (YYYY-MM-DD)." }
  }
  ```
- **Returns:** Task card creation confirmation.

## Test and Validation Plan

- **Protocol Conformity Tests:**
  - Connect to the `mcp_server.py` using the official `@modelcontextprotocol/inspector` tool.
  - Verify resource schemas and tool listings conform to the MCP protocol specification.
- **Proxy Call Loopback Tests:**
  - Mock the Local REST API HTTP server. Verify the MCP server correctly reads the `app.port` discovery file, forwards requests with correct headers, and translates JSON responses into MCP-compliant ToolOutputs.
- **Privacy Override Verification:**
  - Toggle off "Enable MCP Integration" in general settings. Start the MCP server process via stdio, and verify it immediately terminates with a clean error message.
- **UI Copy Helper Validation:**
  - Click the "Copy Claude Desktop Config" button in settings, paste, and verify that the JSON is valid and has correct absolute paths of the environment python and directories.
