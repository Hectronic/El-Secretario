# Tasks: Model Context Protocol (MCP) Server Integration

Status: Draft
Last updated: 2026-09-15

- [ ] T001 Write full user setup documentation and guides under `docs/mcp.md`.
- [ ] T002 Implement `src/api/mcp_server.py` core stdio skeleton and dynamic port/token parsing.
- [ ] T003 Code `mcp_server.py` check enforcing QSettings `enable_mcp_server` and termination logic.
- [ ] T004 Implement MCP Resource endpoints for listing transcriptions and reading specific transcripts.
- [ ] T005 Implement MCP Tool handlers for `search_knowledge`, `start_recording`, `stop_recording`, and `create_task` mapping them to the API.
- [ ] T006 Integrate "Enable MCP Server" checkbox inside the Settings General Panel.
- [ ] T007 Program "Copy Claude Desktop Config" button inside settings to copy a dynamically-crafted path config to the clipboard.
- [ ] T008 Develop automated integration tests verifying MCP tool-to-HTTP mapping and settings-enforced termination.
