# AI Agents Guide

This document contains useful information and strict rules for AI agents working on this repository.

## General Rules

1. **Mandatory Tests**:
- Always verify generated or modified code with tests.
- Every new feature must include new tests, unit or integration as appropriate.
- Never assume code works without testing it.
- Always run tests with the project virtual environment: `./.venv/bin/python -m pytest`, falling back to `./venv/bin/python -m pytest`, or `./run_with_test.sh`.
- Do not run tests with global/system Python.

2. **Documentation Updates**:
- Documentation must be kept up to date.
- With every new feature or significant change, verify and update the relevant documentation.
- If a document exists in multiple languages, update all language variants consistently.

3. **Project Context**:
- This project uses a logging system in `log/app.log`; use it for debugging.
- Source code lives in `src/` and tests live in `tests/`.
- New unit tests should mirror the source folder structure.
- Large UI areas are split by feature packages instead of flat modules:
  - `src/ui/main_window/` contains `MainWindow` plus focused coordinators such as `chat_floating.py`, `recording_tabs.py`, `sidebar_actions.py`, `sidebar_content.py`, `sidebar_sync.py`, and `setup_actions.py`.
  - `src/ui/chat/` contains chat-specific helpers such as `add_context_dialog.py`, `context_builder.py`, and `session_state.py`.
  - `src/ui/context_manager_panel.py` is a reusable context sidebar component shared by chat widgets.
- SQLite persistence is split by aggregate under `src/persistence/`; `src/database.py` keeps the backwards-compatible `DBManager` facade.
- Prefer adding new behavior to the smallest feature package that owns it.
- Keep compatibility shims only when needed during incremental migrations, and move tests to mirror the new package layout under `tests/ui/<feature>/` or `tests/persistence/`.

4. **Platforms**:
- This project is used on Ubuntu and Windows. Preserve existing platform guards and do not break either platform.

5. **Transcription Runtime Preferences**:
- Respect the configured STT backend, device, compute type, and `force_cpu` setting.
- Prefer GPU/CUDA for transcription and diarization when CUDA is available and `force_cpu` is false.
- Do not force CPU unless the user explicitly configured it, CUDA is unavailable, or the existing safe fallback path is handling a real runtime failure.
- Keep diarization aligned with the same runtime policy as transcription where supported.
- After GPU transcription or diarization paths, preserve explicit cleanup of CUDA memory and worker resources.

## Recommended Workflow

1. Understand the requirement and affected modules.
2. Plan the smallest safe change.
3. Implement the change.
4. Create or update tests.
5. Run focused tests first.
6. Run the full suite before finishing when shared UI, worker, STT, threading, or persistence code is touched.
7. Update documentation when behavior changes.

## Refactor and Specs Steward

Use the spec-driven refactor workflow whenever a task modifies code that is not yet well refactored, is listed as a hotspot, or lacks a matching product spec in `docs/specs/`.

Activation checks:
- The changed file is listed in `docs/specs/REFACTOR-2026-05-feature-packages.md` under `Remaining Hotspots`.
- The changed behavior is not covered by an existing `SPEC-XXX` entry in `docs/specs/README.md`.
- The change adds behavior to a broad module when a smaller feature package already owns the area.
- The implementation needs compatibility shims, migration glue, or duplicated logic that should be recorded as follow-up refactor work.

Responsibilities:
- Identify the smallest owner package for the behavior and move or shape code toward that boundary when it is safe.
- Add or update tests before refactoring behavior-sensitive code.
- Update the relevant spec in `docs/specs/`, or create a new `SPEC-XXX` when the behavior has no product contract.
- Update `docs/specs/README.md` feature registry, refactor records, hotspots, or Definition of Done when the change alters ownership or follow-up work.
- Keep refactors incremental and behavior-preserving unless the user explicitly requested a behavior change.
- Run focused tests for the touched area and the broader suite when shared UI, worker, STT, threading, provider, persistence, or migration contracts are affected.

Expected output:
- A short note naming the spec or refactor record updated.
- The files moved or reshaped, if any.
- The exact focused and broader test commands run.
