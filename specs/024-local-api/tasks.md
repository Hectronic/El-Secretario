# Tasks: Local REST API

Status: Completed
Last updated: 2026-09-15

- [x] T001 Design REST endpoints schema and write detailed API documentation in `docs/api.md`.
- [x] T002 Implement `http.server` background server and routing in an isolated `QThread` (`src/api/server.py`).
- [x] T003 Code local loopback security binding and secure Bearer token generation & verification.
- [x] T004 Implement `app.port` token & port dynamic file-discovery writing.
- [x] T005 Code safe cross-thread PyQt6 signal-slot bridging for starting/stopping recordings and task inserts.
- [x] T006 Program read endpoints: connecting database queries for completed recordings, summaries, and transcripts.
- [x] T007 Integrate "Enable Local REST API" toggle in the general settings panel UI and manage server thread lifecycle on settings change.
- [x] T008 Add automated test suite validating port binding, port discovery, request authorization, and cross-thread signals.
