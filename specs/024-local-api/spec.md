# SPEC-024: Local REST API

Status: Approved
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-15

## Problem

"El Secretario" currently operates as an isolated desktop-only Qt application. To enable integration with external workflows—such as personal automation tools (e.g. keyboard shortcuts, Stream Decks), external AI assistants, browser extensions, or local scripting—the application needs a robust, local loopback communication channel. 

Directly accessing the SQLite database is highly discouraged as it bypasses the core application business rules, cannot retrieve live runtime status (e.g., active recording duration), and risks concurrency lockups. A local REST API provides an isolated, secure, and performant loopback integration edge.

## Scope

- **In scope:**
  - A lightweight local HTTP/REST API server built entirely using Python's standard library (`http.server`) to avoid adding bloated third-party web frameworks to `requirements.txt`.
  - The server runs on an isolated background `QThread` and strictly binds to `127.0.0.1` on a dynamically allocated, safe port.
  - Port discovery: Writes the current active port to a local file (`~/.local/share/El-Secretario/app.port` or `%LocalAppData%\El-Secretario\app.port`) so external scripts can automatically discover the endpoint.
  - Read endpoints: Fetch historical recordings, specific transcripts, daily/weekly summaries, and tasks.
  - Live state endpoints: Retrieve active recording state, mic volume, and current processing queue length.
  - Action endpoints: Remotely trigger start/stop/pause recording and programmatically append tasks.
  - Safe Thread Bridging: Employs PyQt signals to safely forward action requests from the HTTP handler thread to the main GUI thread.
  - Setting general panel toggle to enable or disable the local API server in `QSettings`.
- **Out of scope:**
  - Public network exposure (bindings other than `127.0.0.1` are blocked for security).
  - External authentication (standard token-based handshake is sufficient for localhost loopback security).

## REST API Endpoint Specifications

All endpoints are prefixed with `/api/v1`. All payloads use standard `application/json` format.

### 1. System & State Endpoints

#### `GET /api/v1/status`
Returns the real-time runtime status of the desktop application.
- **Response Code:** `200 OK`
- **Payload:**
  ```json
  {
    "app_name": "El Secretario",
    "version": "1.0.0",
    "status": "idle" | "recording" | "transcribing" | "indexing",
    "active_recording": {
      "elapsed_seconds": 124,
      "audio_device": "Default Microphone"
    },
    "processing_queue_backlog": 2
  }
  ```

### 2. Recording & Transcription Endpoints

#### `GET /api/v1/recordings`
Retrieves a paginated list of metadata for completed recordings in the database.
- **Parameters:**
  - `limit` (Query parameter, default: 50)
  - `offset` (Query parameter, default: 0)
- **Response Code:** `200 OK`
- **Payload:**
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

#### `GET /api/v1/recordings/{id}`
Retrieves the full transcript, notes, and aggregate data for a specific recording.
- **Response Code:** `200 OK` / `404 Not Found`
- **Payload:**
  ```json
  {
    "id": 42,
    "title": "Weekly Team Sync",
    "date": "2026-09-15 10:00:00",
    "duration_seconds": 1824,
    "transcript": "Speaker 1: Welcome everyone... Speaker 2: Yes, let's start.",
    "notes": "Action items: Hector to package installers.",
    "summary": "This was a sync meeting discussing packaging...",
    "tags": ["sync", "weekly"]
  }
  ```

### 3. Action / Control Endpoints

#### `POST /api/v1/record/start`
Triggers the application to start recording immediately.
- **Response Code:** `200 OK` / `409 Conflict` (if already recording)
- **Payload:**
  ```json
  {
    "success": true,
    "message": "Recording session initiated successfully."
  }
  ```

#### `POST /api/v1/record/stop`
Stops the current recording session, triggers the transcription queue, and saves metadata.
- **Response Code:** `200 OK` / `409 Conflict` (if not currently recording)
- **Payload:**
  ```json
  {
    "success": true,
    "message": "Recording stopped. Sent to transcription queue.",
    "temp_record_id": 43
  }
  ```

### 4. Tasks Board Endpoints

#### `POST /api/v1/tasks`
Programmatically inserts a new task card onto the tasks board database.
- **Request Payload:**
  ```json
  {
    "title": "Review spec-021 PR",
    "description": "Verify installers on multiple environments.",
    "due_date": "2026-09-18"
  }
  ```
- **Response Code:** `201 Created`
- **Response Payload:**
  ```json
  {
    "success": true,
    "task_id": 105,
    "message": "Task created successfully on the board."
  }
  ```

## Architecture & Safe Threading Design

The server is fully decoupled from the PyQt GUI main thread via an active subclass of `QThread`.

```
  +-----------------------+              +------------------------+
  |    Local REST API     |              |     PyQt main thread   |
  |  (Background QThread) |              |      (Main GUI Loop)   |
  |                       |              |                        |
  |   HTTP Request Received --------Signal-------> Starts/Stops   |
  |   (e.g., POST /start) |              |         Recording      |
  |                       |              |                        |
  |   Returns JSON        |<---Callback--|         MainWindow     |
  |   response to client  |              |                        |
  +-----------------------+              +------------------------+
```

### Safe Signal Bridging
1. The HTTP request comes in on the `QThread`'s HTTP Server worker thread.
2. The handler parses the action and emits a custom PyqtSignal:
   `sig_trigger_record_start = pyqtSignal()`
3. In `MainWindow`, this signal is connected to the native start recording action slot:
   `self.api_thread.sig_trigger_record_start.connect(self.recording_widget.start_recording)`
4. Since the signal crosses a thread boundary, PyQt automatically queues it, executing the slot safely on the **Main GUI Thread** without risking multi-threaded painter crashes or memory corruptions!

### Local Loopback Security
- The HTTP Server socket is initialized strictly binding to `127.0.0.1`.
- Any connection requests originating from external IP interfaces are rejected instantly by the OS TCP stack.
- To prevent unauthorized localhost processes from hitting critical actions, a random single-use API Bearer token is generated on startup and written to the `app.port` file. Local scripts must read this token to authorize their requests.

## Test and Validation Plan

- **Thread Startup & Shutdown Tests:**
  - Verify toggling the "Enable Local REST API" checkbox in settings opens and closes the loopback TCP port cleanly.
- **Port Discovery Validation:**
  - Ensure the file `app.port` is written correctly with format `port=XXXX\ntoken=YYYY` on launch.
- **Mocked HTTP Request Suite:**
  - Send HTTP requests to retrieve recordings, fetch transcripts, and verify status responses are correct.
- **Action Safe-threading verification:**
  - Programmatically trigger `POST /record/start` via curl and verify that PyQt safely triggers the GUI microphone capture and updates the layout.
