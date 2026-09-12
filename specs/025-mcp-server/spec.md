# SPEC-025: MCP Server Integration

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

Users want to use advanced AI assistants and agents (like Claude Desktop, Antigravity, or other MCP-compatible clients) to interact with the knowledge accumulated in "El Secretario". To achieve this seamlessly, "El Secretario" needs to act as a Model Context Protocol (MCP) server, exposing its transcriptions, recordings, tasks, and summarization capabilities as standard MCP Resources and Tools.

## Scope

- In scope: 
  - Implementation of an MCP server utilizing the official Python MCP SDK.
  - Integration with the Local REST API (SPEC-024) to fetch live data and trigger actions without duplicating business logic or risking database locks.
  - Exposing specific **Resources**: `secretario://transcriptions/{id}`, `secretario://tasks/active`.
  - Exposing specific **Tools**: `search_transcriptions`, `get_latest_summary`, `create_task`, `start_recording`.
  - A UI toggle in the application's Settings to enable or disable the MCP Server functionality.
- Out of scope: Implementing the MCP client side, handling complex real-time audio streaming over MCP (only metadata and text are exposed).

## User Stories

- As a user with an MCP-compatible AI assistant, I want to ask my assistant "What did I discuss in my last meeting recorded by El Secretario?", and have the assistant automatically pull the transcription using the MCP server.
- As a user, I want my AI assistant to be able to create tasks in El Secretario's task board based on our conversation.
- As a privacy-conscious user, I want the ability to explicitly enable or disable the MCP server integration from the El Secretario settings menu.

## Acceptance Criteria

- Given an MCP client is connected to the El Secretario MCP server, when the client lists resources, then it receives a list of available transcription and task resources.
- Given an MCP client calls the `create_task` tool, then the server communicates with the Local API (SPEC-024) to create the task, and the task immediately appears in the El Secretario UI.
- Given the user disables the MCP Server in Settings, then any spawned Standalone Stdio MCP process will immediately exit or return an error, preventing external AI agents from accessing El Secretario's data.

## Architecture Notes

- The MCP server will be implemented as a **Standalone Stdio** Python script (`secretario_mcp.py`) that uses stdio transport (standard for Claude Desktop). This script acts as a proxy, translating MCP stdio requests into HTTP calls to the Local REST API (SPEC-024).
- To respect the user's toggle setting: the `secretario_mcp.py` script will read the application's `QSettings` configuration file (or the Local REST API's status endpoint) upon initialization. If `enable_mcp_server` is false, the script will exit with an error message stating that the MCP integration is disabled by the user.
- The UI will include an "Enable MCP Server" checkbox in the settings, which persists the `enable_mcp_server` flag. It can also provide a helper button to auto-generate the `claude_desktop_config.json` snippet for the user.

## Test Plan

- Unit: Test the mapping of MCP tool calls to Local API requests.
- Integration: Use the MCP Inspector to connect to the MCP server via stdio, execute tools, and verify changes.
- Security/Toggle: Disable the MCP setting, attempt to run the `secretario_mcp.py` script, and verify it cleanly rejects the execution.

## Documentation

- Add a guide in `docs/mcp.md` on how to configure Claude Desktop or other MCP clients to connect, and clarify that it must be enabled in Settings first.
