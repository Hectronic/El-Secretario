---
name: pyqt-venv-dev-test
description: Standardize coding and testing workflow for Python/PyQt projects with mandatory virtualenv usage and stable test execution. Use whenever code is created, edited, refactored, or deleted (src/, tests/, scripts/, configs) so Codex always run checks from project venv, apply PyQt headless safeguards, and report reproducible validation commands.
---

# PyQt Venv Dev Test

## Enforce Environment

1. Detect the project venv in this order:
- `./.venv/bin/python`
- `./venv/bin/python`

2. Run Python tools only through that interpreter:
- `VENV_PY -m pytest ...`
- `VENV_PY -m pip ...`
- `VENV_PY -m py_compile ...`

3. Never use global `python`, `pip`, or `pytest` if a local project venv exists.

## Stabilize PyQt Tests

1. For tests that instantiate Qt widgets, export before running pytest:
- `QT_QPA_PLATFORM=offscreen`
- `PYTHONUNBUFFERED=1`

2. If test discovery loads unwanted plugins, run with:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` (only when plugin conflicts are suspected)

3. Keep Qt creation deterministic:
- Create one `QApplication` per process in tests.
- Reuse `QApplication.instance()` in fixtures.

## Execute Validation After Every Code Change

1. Run targeted tests for touched modules first.
2. Run broader scope when local changes affect shared UI/state.
3. Run full suite before finishing, unless explicitly skipped by the user.
4. If execution time is large, at least run:
- impacted tests
- smoke tests for startup/UI flow
- one end-to-end path that covers the changed feature

## Report Reproducible Commands

Always report exact commands executed, using the project venv interpreter path.

## Use Reference Playbook

Load and follow [references/test-playbook.md](references/test-playbook.md) for command templates and troubleshooting.
