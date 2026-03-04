# AI Agents Guide

This document contains useful information and strict rules for AI agents working on this repository.

## General Rules

1.  **Mandatory Tests**:
    *   **Always** verify generated or modified code with tests.
    *   **Every new feature must include new tests** (unit or integration as appropriate).
    *   Never assume code works without testing it.
    *   **Always run tests with the project virtual environment** (`./venv/bin/python -m pytest` or `./run_with_test.sh`). Do not run tests with the global/system Python.

2.  **Documentation Updates**:
    *   **Documentation must be kept up to date.**
    *   With every new feature or significant change, verify and update the relevant documentation (README, installation guides, code comments, etc.).
    *   **CRITICAL**: You must update the documentation in **ALL available languages** (e.g., English, Spanish, Asturian). If a file exists in multiple languages (like `README.md`, `README_ES.md`, `README_AST.md`), you must update all of them to maintain consistency.

3.  **Project Context**:
    *   This project uses a logging system in `log/app.log`. Use it for debugging.
    *   The project structure separates source code in `src/` and tests in `tests/`.

4.  **Platforms**:
    *   This project is being used in Ubuntu and Windows, sometimes there are diferent implemetations, bear it in mind and don't break other systems


## Recommended Workflow

1.  Understand the requirement.
2.  Plan the changes (create/modify files).
3.  Implement the changes.
4.  **Create/Update Tests**.
5.  Run Tests and Verify.
6.  Update Documentation (in all languages).
