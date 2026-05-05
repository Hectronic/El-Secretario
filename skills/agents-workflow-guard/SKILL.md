---
name: agents-workflow-guard
description: "Enforce this repository workflow from AGENTS.md. Use when implementing or modifying code: run tests with the project virtual environment, add or update tests for behavior changes, preserve configured GPU/CPU transcription behavior, keep Windows/Ubuntu compatibility, and update documentation (all available languages) when features change."
---

# Agents Workflow Guard

Apply this guardrail to any code change in this repository.

## Mandatory Rules

1. Test after every development change.
- Never assume code works without tests.
- Prefer targeted tests during iteration, then run the full suite before finishing.

2. Use the project virtual environment for tests.
- Always run tests with `./.venv/bin/python -m pytest`, falling back to `./venv/bin/python -m pytest` (or `./run_with_test.sh`).
- Do not use global/system Python for test execution.

3. Add or update tests when behavior changes.
- New feature: add new tests.
- Bug fix: add or update tests that reproduce and validate the fix.
- Refactor with behavior impact: update tests intentionally and explicitly.

4. Keep cross-platform behavior safe.
- Do not break Ubuntu/Windows differences.
- If code is platform-specific, preserve existing guards and add checks/tests where practical.

5. Keep docs aligned with feature changes.
- Update relevant docs after significant changes.
- If a document exists in multiple languages, update all language variants.

6. Preserve transcription runtime preferences.
- Respect configured STT backend, device, compute type, and `force_cpu`.
- Prefer GPU/CUDA when available and `force_cpu` is false.
- Do not force CPU unless explicitly configured, CUDA is unavailable, or a safe fallback path is handling a real runtime failure.
- Keep transcription and diarization aligned with this runtime policy where supported.

## Execution Order

1. Understand the requested change and impacted files.
2. Implement minimal production changes.
3. Create or update tests for the changed behavior.
4. Run focused tests with `./.venv/bin/python -m pytest ...` or `./venv/bin/python -m pytest ...`.
5. Run full suite with `./.venv/bin/python -m pytest -q` or `./venv/bin/python -m pytest -q`.
6. Report test evidence and remaining risks (if any).

## Reporting Checklist

- Files changed (code + tests + docs).
- Tests added or updated.
- Targeted test command/results.
- Full suite command/results.
- Any platform-specific caveats (Ubuntu/Windows).
