# Tasks: Local REST API

Status: Draft
Last updated: 2026-09-15

- [ ] T001 Design REST endpoints schema and write detailed API documentation in `docs/api.md`.
- [ ] T002 Implement `http.server` background server and routing in an isolated `QThread` (`src/api/server.py`).
- [ ] T003 Code local loopback security binding and secure Bearer token generation & verification.
- [ ] T004 Implement `app.port` token & port dynamic file-discovery writing.
- [ ] T005 Code safe cross-thread PyQt6 signal-slot bridging for starting/stopping recordings and task inserts.
- [ ] T006 Program read endpoints: connecting database queries for completed recordings, summaries, and transcripts.
- [ ] T007 Integrate "Enable Local REST API" toggle in the general settings panel UI and manage server thread lifecycle on settings change.
- [ ] T008 Add automated test suite validating port binding, port discovery, request authorization, and cross-thread signals.
