# SPEC-025: MCP Server Integration

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

Users want to use advanced AI assistants and agents (like Claude Desktop, Antigravity, or other MCP-compatible clients) to interact with the knowledge accumulated in "El Secretario". To achieve this seamlessly, "El Secretario" needs to act as a Model Context Protocol (MCP) server, exposing its transcriptions, recordings, tasks, and summarization capabilities as standard MCP Resources and Tools.

## Scope

- In scope: 
  - Implementation of an MCP server utilizing the official Python MCP SDK.
  - Integration with the Local API (SPEC-024) to fetch live data and trigger actions without duplicating business logic or risking database locks.
  - Exposing specific **Resources**: `secretario://transcriptions/{id}`, `secretario://tasks/active`.
  - Exposing specific **Tools**: `search_transcriptions`, `get_latest_summary`, `create_task`, `start_recording`.
- Out of scope: Implementing the MCP client side, handling complex real-time audio streaming over MCP (only metadata and text are exposed).

## User Stories

- As a user with an MCP-compatible AI assistant, I want to ask my assistant "What did I discuss in my last meeting recorded by El Secretario?", and have the assistant automatically pull the transcription using the MCP server.
- As a user, I want my AI assistant to be able to create tasks in El Secretario's task board based on our conversation.

## Acceptance Criteria

- Given an MCP client is connected to the El Secretario MCP server, when the client lists resources, then it receives a list of available transcription and task resources.
- Given an MCP client calls the `search_transcriptions` tool with a keyword, then the server responds with the matching transcription texts.
- Given an MCP client calls the `create_task` tool, then the server communicates with the Local API (SPEC-024) to create the task, and the task immediately appears in the El Secretario UI.

## Architecture Notes

- The MCP server can be run in two ways:
  1. **Embedded:** The server runs as a background process or thread managed by the main "El Secretario" Qt app, using SSE (Server-Sent Events) transport.
  2. **Standalone Stdio:** A separate Python script (`secretario_mcp.py`) that uses stdio transport (standard for Claude Desktop). This script acts as a proxy, translating MCP stdio requests into HTTP calls to the Local API (SPEC-024).
- The Standalone Stdio approach is recommended as it's the most compatible with current MCP clients (like Claude Desktop) which expect to spawn the server process directly. The proxy approach ensures the main Qt app remains the single source of truth.

## Test Plan

- Unit: Test the mapping of MCP tool calls to Local API requests.
- Integration: Use the MCP Inspector or a simple test client to connect to the MCP server via stdio, execute tools, and verify the resulting changes in the Local API.

## Documentation

- Add a guide in `docs/mcp.md` on how to configure Claude Desktop or other MCP clients to connect to the El Secretario MCP server.
