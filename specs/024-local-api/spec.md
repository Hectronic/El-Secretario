# SPEC-024: Local API / IPC

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

"El Secretario" currently operates as a standalone Qt desktop application. To allow external tools (like other AI agents, scripts, or external clients) to interact with it, read live data, or trigger actions (like starting a recording), the application needs a localized interface for Inter-Process Communication (IPC). While external tools could theoretically read the SQLite database directly, doing so bypasses business logic, cannot interact with live runtime state (like current recording status), and risks database locking issues.

## Scope

- In scope: 
  - A lightweight local API server (e.g., REST over HTTP or a local UNIX socket / named pipe) running alongside or within the main Qt event loop.
  - Read endpoints for database entities: Transcriptions, Recordings, Tasks, Summaries.
  - Read endpoints for live application state: Current recording status, active microphone.
  - Action endpoints: Start/stop recording, create task, trigger summary.
- Out of scope: Public internet exposure, authentication (assuming local-only loopback access), complex GraphQL APIs.

## User Stories

- As a developer, I want to query the application for the latest transcriptions via a local HTTP endpoint so I can use that data in my own scripts.
- As an external AI tool, I want to check if the user is currently recording before I interrupt them with a notification.
- As a power user, I want to trigger a recording from a custom keyboard shortcut via a simple `curl` command.

## Acceptance Criteria

- Given the application is running, when a local client makes a GET request to `/api/v1/recordings`, then it receives a JSON list of recent recordings.
- Given the application is running, when a local client makes a GET request to `/api/v1/state`, then it receives the current active state (e.g., `{"is_recording": true}`).
- Given the application is running, when a local client makes a POST request to `/api/v1/record/start`, then the UI updates and a recording actually begins.

## Architecture Notes

- Run a lightweight Python ASGI/WSGI server (like FastAPI/Uvicorn or a simple `http.server` wrapper) in a separate `QThread`.
- Use Qt's Signal/Slot mechanism to bridge thread communication safely. The API thread emits signals that the main GUI thread catches to perform actions, and the GUI thread can share thread-safe data or the SQLite connection (using WAL mode or appropriate connection pooling) to the API thread.
- Bind the server to `127.0.0.1` and a fixed or discoverable port (e.g., written to a lockfile in `~/.local/share/El-Secretario/app.port`).

## Test Plan

- Unit: Test the API thread's ability to emit correct signals based on HTTP requests.
- Integration: Start the app in headless/test mode, make real HTTP requests to the exposed port, and verify that the database or state changes.
- Security: Verify that the server strictly rejects non-loopback connections.

## Documentation

- Create `docs/api.md` detailing available endpoints, payloads, and how to discover the port.
