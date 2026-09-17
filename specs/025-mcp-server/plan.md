# Implementation Plan: Model Context Protocol (MCP) Server Integration

Status: Implemented
Last updated: 2026-09-15
Spec: [spec.md](spec.md)

## Overview
Develop a standalone MCP Server process (`src/api/mcp_server.py`) using the official Python MCP SDK. The server will act as a secure proxy to the Local REST API (SPEC-024) to securely expose El Secretario's transcripts, RAG searching, and action controls to external AI agents.

## Phases

### Phase 1: Core MCP SDK & Stdio Setup
- Set up `mcp_server.py` using the official `mcp.server` framework.
- Configure stdio transport handles (`mcp.server.stdio.mcp_server_async`).
- Implement port discovery logic: Upon startup, parse the local `{user_data_dir}/app.port` file to extract the loopback HTTP port and single-use bearer token.
- Implement settings check: Read the `enable_mcp_server` flag from the app's `QSettings` file. If disabled, terminate the process instantly with an informative stderr message.

### Phase 2: Exposing Resources
- Implement the MCP `@server.list_resources()` handler. Expose:
  - `secretario://transcriptions` (Metadata list of saved meetings).
  - `secretario://tasks/active` (All active task board cards).
- Implement the `@server.read_resource()` handler. Translate:
  - `secretario://transcriptions/{id}` ➔ Make HTTP `GET /api/v1/recordings/{id}` request and return the result.
  - `secretario://tasks/active` ➔ Make HTTP `GET /api/v1/tasks` request and format as JSON.

### Phase 3: Exposing Tools
- Implement the `@server.list_tools()` handler. Define schemas for:
  - `search_knowledge`
  - `start_recording`
  - `stop_recording`
  - `create_task`
- Implement the `@server.call_tool()` handler:
  - Forward calls to corresponding endpoints in the Local REST API (Spec-024) with authorization headers.
  - Handle HTTP status codes gracefully and convert into proper MCP `CallToolResult` responses.

### Phase 4: UI Integration & Clipboard Helper
- In `GeneralSettingsPanel`, add:
  - "Enable Model Context Protocol (MCP) Server Integration" checkbox.
  - "Copy Claude Desktop Configuration" button.
- Program the button click to:
  - Query current Python interpreter path (`sys.executable`).
  - Calculate absolute path of `src/api/mcp_server.py`.
  - Format a complete `claude_desktop_config.json` snippet.
  - Copy this JSON block directly to the user's OS clipboard using `QApplication.clipboard().setText()`.

### Phase 5: Complete Verification & Documentation
- Document the entire integration process in `docs/mcp.md`.
- Verify the server's conformity using the MCP Inspector tool.
- Write automated tests checking proxy connections and setting enforcement.
