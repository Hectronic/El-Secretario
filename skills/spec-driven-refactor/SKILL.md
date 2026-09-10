---
name: spec-driven-refactor
description: Keep El Secretario GitHub Spec Kit artifacts and architecture docs aligned while refactoring. Use when Codex refactors, splits, moves, renames, or reorganizes code in this repository, or when a change lacks a matching feature contract in specs/. Ensure spec.md, plan.md, and tasks.md retain acceptance criteria, affected modules, and validation.
---

# Spec Driven Refactor

Use this skill together with `refactor-workflow`, `project-dev-standards`, and `pyqt-venv-dev-test` when refactoring this repository.

Also use it as the workflow for the `Refactor and Specs Steward` subagent defined in `AGENTS.md`.

## Workflow

1. Identify the behavior boundary before moving code.
- Read the matching `specs/<NNN-feature>/spec.md` and `plan.md`.
- Check whether the refactor preserves an existing capability or creates/changes behavior.
- Map touched code to the nearest numbered feature directory.

2. Decide the documentation action.
- If behavior is unchanged: update the existing feature's plan and completed tasks.
- If user-visible behavior changes: update or create a feature spec before implementation.
- If a new feature area appears: add `specs/<next-number>-<slug>/spec.md`, `plan.md`, and `tasks.md`.
- If architecture boundaries change: update `docs/ARCHITECTURE.md`.

3. Preserve traceability.
- Mention old and new module paths for moved code.
- List compatibility shims kept or removed.
- List tests that pin the preserved behavior.
- Record follow-up refactors explicitly instead of hiding them in implementation notes.

4. Update tests with the refactor.
- Move tests to mirror new source paths when modules move.
- Add characterization tests before moving fragile behavior.
- Keep tests linked to acceptance criteria or preserved behavior.

5. Validate and report.
- Run focused tests for touched areas.
- Run the full suite when shared UI, worker, STT, or threading code is touched.
- Run `git diff --check` for documentation and formatting sanity.
- Report exact commands and any skipped validation.

## Spec Decision Rules

- Update an existing spec when the same product capability still exists and only implementation structure changes.
- Create a new spec when the user can now do something materially new.
- Create a refactor record when the change is architecture-significant but behavior-preserving.
- Update README language variants only when user-facing behavior or contributor workflow changes.
- Do not create specs for trivial internal cleanup unless it changes a documented boundary or hotspot.

## Required Files

- Constitution: `.specify/memory/constitution.md`
- Feature artifacts: `specs/<NNN-feature>/spec.md`, `plan.md`, and `tasks.md`
- Architecture map: `docs/ARCHITECTURE.md`
- User-facing docs: `README.md`, `README_ES.md`, `README_AST.md`

## Completion Checklist

- The matching Spec Kit feature artifact reflects code reality.
- Any touched plan includes current module paths and tests; completed work is checked in `tasks.md`.
- `docs/ARCHITECTURE.md` reflects new boundaries or remaining hotspots.
- README variants are updated when behavior or workflow changes.
- Validation commands are run from the project virtualenv for code changes.
