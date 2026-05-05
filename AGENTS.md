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
6. Run the full suite before finishing when shared UI, worker, STT, or threading code is touched.
7. Update documentation when behavior changes.
