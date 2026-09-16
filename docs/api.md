# El Secretario - Local REST API Integration Guide

This document describes how to integrate external tools, scripts, and assistants with El Secretario using its built-in Local REST API (SPEC-024).

## Table of Contents
1. [Enabling the Local API](#1-enabling-the-local-api)
2. [Dynamic Port & Token Discovery](#2-dynamic-port--token-discovery)
3. [Local Security & CORS](#3-local-security--cors)
4. [Endpoint Reference](#4-endpoint-reference)
   - [GET /api/v1/status](#get-apiv1status)
   - [GET /api/v1/recordings](#get-apiv1recordings)
   - [GET /api/v1/recordings/{id}](#get-apiv1recordingsid)
   - [GET /api/v1/tasks](#get-apiv1tasks)
   - [GET /api/v1/search](#get-apiv1search)
   - [POST /api/v1/record/start](#post-apiv1recordstart)
   - [POST /api/v1/record/stop](#post-apiv1recordstop)
   - [POST /api/v1/tasks](#post-apiv1tasks)
5. [Curl Example Scripts](#5-curl-example-scripts)

---

## 1. Enabling the Local API

To use the API, it must first be enabled in the application's user interface:
1. Open El Secretario.
2. Navigate to the **Settings** panel (General).
3. Under the **🔌 Local REST API** section, check **Enable Local REST API server on loopback (127.0.0.1)**.
4. Click **Save Settings**. The background server will immediately spin up and bind to a local port.

---

## 2. Dynamic Port & Token Discovery

To prevent port conflicts and secure localhost communication, El Secretario binds to a **dynamically allocated free TCP port** (starting from `12800`) and generates a **random, single-use Bearer Token** on each launch.

The active port and token are written to a temporary discovery file `app.port` in the application's root workspace directory upon startup. External scripts must read this file to establish communication:

**Example `app.port` content:**
```ini
port=12800
token=fa8d7a18b2c4d5e9f0123456789abcde
```

On clean application exit, the `app.port` file is automatically deleted from disk.

---

## 3. Local Security & CORS

- **Loopback-Only Binding:** The HTTP server strictly binds to the loopback interface (`127.0.0.1`). Any request coming from external IP addresses is immediately rejected by the OS network stack.
- **Header Authentication:** All state and data requests require a standard authorization header containing the generated token:
  ```http
  Authorization: Bearer <token>
  ```
- **CORS Support:** The API server supports Cross-Origin Resource Sharing (CORS) preflight checks (`OPTIONS` requests), enabling easy integration with local browser extensions or local web-apps.

---

## 4. Endpoint Reference

All REST endpoints are prefixed with `/api/v1`.

### `GET /api/v1/status`
Retrieves live status information of the application window.
- **Response Example:**
  ```json
  {
    "app_name": "El Secretario",
    "version": "1.0.0",
    "status": "recording",
    "active_recording": {
      "elapsed_seconds": 124,
      "audio_device": "Blue Yeti Microphone"
    },
    "processing_queue_backlog": 0
  }
  ```

### `GET /api/v1/recordings`
Returns a paginated list of metadata for completed recordings.
- **Parameters:**
  - `limit` (Query parameter, default: 50)
  - `offset` (Query parameter, default: 0)
- **Response Example:**
  ```json
  [
    {
      "id": 42,
      "title": "Weekly Team Sync",
      "date": "2026-09-15 10:00:00",
      "duration_seconds": 1824,
      "summary_generated": true,
      "tags": ["sync", "weekly"]
    }
  ]
  ```

### `GET /api/v1/recordings/{id}`
Returns the full text, notes, summary, and tags of a specific recording.
- **Response Example:**
  ```json
  {
    "id": 42,
    "title": "Weekly Team Sync",
    "date": "2026-09-15 10:00:00",
    "duration_seconds": 1824,
    "transcript": "Speaker 1: Welcome everyone...",
    "notes": "Action items decided.",
    "summary": "This sync covered the next release phases.",
    "tags": ["sync", "weekly"]
  }
  ```

### `GET /api/v1/tasks`
Returns a list of all active tasks on the board.
- **Response Example:**
  ```json
  [
    {
      "id": 1,
      "title": "Complete Spec 24",
      "description": "Write tests and documentation.",
      "due_date": "2026-09-15",
      "completed": false
    }
  ]
  ```

### `GET /api/v1/search`
Queries El Secretario's semantic RAG vector database and keyword indexes.
- **Parameters:**
  - `query` (Query parameter, string, required)
- **Response Example:**
  ```json
  {
    "query": "installer scripts",
    "results": [
      {
        "source": "recording",
        "source_id": 42,
        "title": "Weekly Team Sync",
        "text": "...we finished building the installer scripts and native packages...",
        "relevance_score": 0.89
      }
    ]
  }
  ```

### `POST /api/v1/record/start`
Triggers the microphone and system audio capture in the PyQt application window immediately.
- **Response Example:**
  ```json
  {
    "success": true,
    "message": "Recording session initiated successfully."
  }
  ```

### `POST /api/v1/record/stop`
Stops the current recording, triggers the transcription queue, and saves metadata.
- **Response Example:**
  ```json
  {
    "success": true,
    "message": "Recording stopped. Sent to transcription queue."
  }
  ```

### `POST /api/v1/tasks`
Programmatically inserts a new task card onto the tasks board database.
- **Request Payload:**
  ```json
  {
    "title": "Task title summary",
    "description": "Optional notes or details",
    "due_date": "2026-09-18"
  }
  ```
- **Response Example (`201 Created`):**
  ```json
  {
    "success": true,
    "task_id": 105,
    "message": "Task created successfully on the board."
  }
  ```

---

## 5. Curl Example Scripts

Here are quick shell recipes showing how to query the discovery file and call the local REST API:

### Discovery and Query Script (Bash)
```bash
#!/usr/bin/env bash
set -e

# Read dynamic port and token from discovery file
if [ ! -f "app.port" ]; then
    echo "[ERROR] El Secretario is not running or the Local REST API is disabled."
    exit 1
fi

PORT=$(grep port app.port | cut -d= -f2)
TOKEN=$(grep token app.port | cut -d= -f2)

# 1. Fetch live state status
echo "Fetching live application status..."
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/v1/status"

# 2. Trigger start recording remotely
echo "Triggering microphone recording..."
curl -s -X POST -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/v1/record/start"

# 3. Create a task card programmatically
echo "Adding a new task on the board..."
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "Automated API Task", "description": "Created from local curl shell script", "due_date": "2026-09-30"}' \
     "http://127.0.0.1:$PORT/api/v1/tasks"
```
