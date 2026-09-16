# Implementation Plan: Local REST API

Status: Implemented
Last updated: 2026-09-15
Spec: [spec.md](spec.md)

## Overview
Develop a highly performant, standard-library based local REST API server running on an isolated `QThread` to allow secure, local loopback communication and workflow automation with El Secretario.

## Phases

### Phase 1: Core Server & Security
- Implement `LocalAPIServer` subclassing `http.server.ThreadingHTTPServer` to support parallel request handling.
- Write request routing inside `LocalAPIRequestHandler` subclassing `http.server.BaseHTTPRequestHandler`.
- Implement strict `127.0.0.1` binding and loopback IP checking on all incoming connections.
- Program port-discovery writing: On startup, select a dynamic, free TCP port, generate a cryptographically secure random Bearer token, and write them to `{user_data_directory}/app.port` in format `port=XXXX\ntoken=YYYY`.
- Enforce token-checking header (`Authorization: Bearer YYYY`) on all state-mutating requests.

### Phase 2: Database and Read Endpoints
- Implement GET endpoints to query data directly from SQL databases:
  - `GET /api/v1/recordings` (queries recordings from DBManager)
  - `GET /api/v1/recordings/{id}` (retrieves full transcripts, notes, and summaries)
- Serialize Python lists/dictionaries directly into standard JSON strings using the native `json` library.

### Phase 3: Action Triggering & Qt Thread Bridging
- Create custom `PyQt6.QtCore.QObject` subclass inside the API thread to define cross-thread signals:
  - `sig_start_recording = pyqtSignal()`
  - `sig_stop_recording = pyqtSignal()`
- Connect these signals inside `MainWindow.bootstrap_main_window` directly to main GUI action slots.
- Implement POST endpoints to emit signals:
  - `POST /api/v1/record/start`
  - `POST /api/v1/record/stop`
  - `POST /api/v1/tasks` (creates a task in Database)

### Phase 4: UI Integration & Settings Toggle
- Add an "Enable Local REST API" checkbox to the `GeneralSettingsPanel` (`src/ui/settings/general_panel.py`) linked to the `enable_local_api` QSettings variable.
- In `main.py` or during MainWindow bootstrap, check `enable_local_api` settings:
  - If enabled, start the background `QThread` server.
  - If toggled off in settings, stop the server and close the active TCP socket immediately.

### Phase 5: Documentation & Client Helpers
- Write `docs/api.md` containing full API specs, Curl command examples, and Python integration guides.
