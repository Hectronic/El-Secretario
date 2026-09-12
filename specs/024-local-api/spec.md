# SPEC-024: Local REST API

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

"El Secretario" currently operates as a standalone Qt desktop application. To allow external tools (like other AI agents, scripts, or external clients) to interact with it, read live data, or trigger actions (like starting a recording), the application needs a localized interface for communication. While external tools could theoretically read the SQLite database directly, doing so bypasses business logic, cannot interact with live runtime state (like current recording status), and risks database locking issues.

## Scope

- In scope: 
  - A lightweight local REST API over HTTP running alongside or within the main Qt event loop.
  - Read endpoints for database entities: Transcriptions, Recordings, Tasks, Summaries.
  - Read endpoints for live application state: Current recording status, active microphone.
  - Action endpoints: Start/stop recording, create task, trigger summary.
  - A UI toggle in the application's Settings to enable or disable the REST API.
- Out of scope: Public internet exposure, complex GraphQL APIs, external authentication (assumes local loopback access only).

## User Stories

- As a developer, I want to query the application for the latest transcriptions via a local REST endpoint so I can use that data in my own scripts.
- As an external AI tool, I want to check if the user is currently recording before I interrupt them with a notification.
- As a power user, I want to trigger a recording from a custom keyboard shortcut via a simple `curl` command.
- As a privacy-conscious user, I want the ability to turn off the REST API entirely from the Settings menu.

## Acceptance Criteria

- Given the application is running and the API is enabled in settings, when a local client makes a GET request to `/api/v1/recordings`, then it receives a JSON list of recent recordings.
- Given the application is running and the API is enabled, when a local client makes a POST request to `/api/v1/record/start`, then the UI updates and a recording actually begins.
- Given the user disables the REST API in Settings, then the local server stops listening on its port, and all subsequent API requests fail (Connection Refused).
- Given the application starts, it checks the persisted setting to decide whether to launch the API background thread.

## Architecture Notes

- Run a lightweight Python ASGI/WSGI server (like FastAPI/Uvicorn) in a separate `QThread`.
- Bind the server to `127.0.0.1` and a discoverable port (e.g., written to `~/.local/share/El-Secretario/app.port`).
- Use Qt's Signal/Slot mechanism to bridge thread communication safely between the REST endpoints and the Qt Main Event Loop.
- Integrate with `src/ui/settings_runtime.py` (or similar) to persist the `enable_rest_api` flag in `QSettings`. The main application will start or stop the Uvicorn/API thread when this setting is toggled.

## Test Plan

- Unit: Test the API thread's ability to emit correct signals based on HTTP requests.
- Integration: Toggle the setting on/off and verify the port opens and closes. Make real HTTP requests to verify state changes.
- Security: Verify that the server strictly rejects non-loopback connections.

## Documentation

- Create `docs/api.md` detailing available endpoints, payloads, how to discover the port, and how to enable it in Settings.
