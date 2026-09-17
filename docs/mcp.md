# El Secretario - Model Context Protocol (MCP) Integration Guide

This document describes how to connect advanced local AI clients—such as **Claude Desktop**—to El Secretario using the Model Context Protocol (SPEC-025).

## Table of Contents
1. [What is MCP?](#1-what-is-mcp)
2. [Enabling MCP Server Integration](#2-enabling-mcp-server-integration)
3. [Claude Desktop Setup (1-Click)](#3-claude-desktop-setup-1-click)
4. [Exposed Resources](#4-exposed-resources)
5. [Exposed Tools](#5-exposed-tools)

---

## 1. What is MCP?

The **Model Context Protocol (MCP)** is an open-standard protocol developed by Anthropic that allows local AI models and applications to safely and securely read data (Resources) and trigger actions (Tools) inside local computer systems.

By exposing El Secretario as an MCP server, your local AI chat assistants (like Claude Desktop) gain the ability to search your meeting notes, query transcripts, list active tasks, start/stop voice recordings, and append new task cards onto your board automatically during your conversations.

---

## 2. Enabling MCP Server Integration

Before any client can connect, you must enable the integration inside El Secretario to authorize the port:
1. Open El Secretario.
2. Go to **Settings** (General panel).
3. Under the **🤖 Model Context Protocol (MCP)** section, check **Enable Model Context Protocol (MCP) Server Integration**.
4. Click **Save Settings**.

*Note: For strict security and privacy, if this checkbox is turned off, any attempt to launch or connect to the MCP server process is instantly blocked with a termination exit code.*

---

## 3. Claude Desktop Setup (1-Click)

El Secretario features a **1-click clipboard helper** to make configuring Claude Desktop trivial:

1. Open **Settings** in El Secretario.
2. Click the button **Copy Claude Desktop Config**.
   - This dynamically crafts the exact JSON block with correct absolute paths matching your Python virtual environment and folder structure, copying it straight to your clipboard.
3. Open your Claude Desktop configuration file:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
4. Paste the copied JSON block inside the `"mcpServers"` object.

**Example Generated JSON Configuration:**
```json
{
  "mcpServers": {
    "el-secretario": {
      "command": "/home/developer/repos/hector/El-Secretario/.venv/bin/python",
      "args": [
        "/home/developer/repos/hector/El-Secretario/src/api/mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/home/developer/repos/hector/El-Secretario"
      }
    }
  }
}
```
5. Restart Claude Desktop. You will see the **El Secretario** tool connection icon active in your chat window!

---

## 4. Exposed Resources

MCP Resources are read-only data sources that the AI client can retrieve or reference:

- **`secretario://transcriptions`**
  - Exposes a list of metadata for all saved meetings and voice recording transcripts (ID, title, date, duration, tags).
- **`secretario://transcriptions/{id}`**
  - Exposes the full transcript, notes, and generated summary of a specific meeting.
- **`secretario://tasks/active`**
  - Exposes the live board of all active, incomplete tasks.

*Example Prompt:* `"Summarize the transcription secretario://transcriptions/42 and extract the action items."*

---

## 5. Exposed Tools

MCP Tools allow the AI client to execute actions inside the application as a proxy:

### `search_knowledge(query: string)`
Queries El Secretario's transcripts, notes, and summaries using the semantic RAG vector engine and keyword indexes, returning snippets with match relevance scores.
- *Example Prompt:* `"Search my transcripts to see if we discussed any deployment timelines recently."*

### `start_recording()`
Remotely starts a new voice recording session inside El Secretario's active GUI window.
- *Example Prompt:* `"Start recording my voice now."*

### `stop_recording()`
Stops the active recording session, trigger the transcription queue, and saves metadata.
- *Example Prompt:* `"Stop recording and save the transcript."*

### `create_task(title: string, description: string, due_date: string)`
Programmatically appends a new task card onto El Secretario's task board.
- *Example Prompt:* `"Add a task to check the deployment on Friday."*
