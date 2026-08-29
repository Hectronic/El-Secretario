---
name: spec-driven-refactor
description: Keep El Secretario specs and architecture docs aligned while refactoring. Use when Codex refactors, splits, moves, renames, or reorganizes code in this repository, and also when a change touches code that is listed as a hotspot, is not yet well refactored, or lacks a matching SPEC-XXX contract in docs/specs. Ensure existing specs are updated or new specs/refactor records are created with acceptance criteria, affected modules, and validation.
---

# Spec Driven Refactor

Use this skill together with `refactor-workflow`, `project-dev-standards`, and `pyqt-venv-dev-test` when refactoring this repository.

Also use it as the workflow for the `Refactor and Specs Steward` subagent defined in `AGENTS.md`.

## Workflow

1. Identify the behavior boundary before moving code.
- Read `docs/specs/README.md`.
- Check whether the refactor preserves an existing capability or creates/changes behavior.
- Map touched code to the nearest spec ID in the feature registry.

2. Decide the documentation action.
- If behavior is unchanged: update the existing spec's architecture notes or add a refactor record.
- If user-visible behavior changes: update or create a feature spec before implementation.
- If a new feature area appears: add a new `SPEC-XXX-*.md` and register it in `docs/specs/README.md`.
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

- Feature registry and template: `docs/specs/README.md`
- Architecture map and refactor queue: `docs/ARCHITECTURE.md`
- Existing refactor records: `docs/specs/REFACTOR-*.md`
- User-facing docs: `README.md`, `README_ES.md`, `README_AST.md`

## Refactor Record Template

Use this for behavior-preserving architecture work:

```markdown
# REFACTOR-YYYY-MM: Short Name

Status: Implemented | In progress | Planned
Last updated: YYYY-MM-DD

## Goal

Why the refactor exists.

## Behavior Contract

- Preserved:
- Changed:
- Out of scope:

## Moved Boundaries

- From:
- To:

## Specs Affected

- SPEC-XXX:

## Tests

- Focused:
- Full suite:

## Follow-Ups

- ...
```

## Completion Checklist

- `docs/specs/README.md` registry still matches code reality.
- Any touched spec includes current module paths and tests.
- `docs/ARCHITECTURE.md` reflects new boundaries or remaining hotspots.
- README variants are updated when behavior or workflow changes.
- Validation commands are run from the project virtualenv for code changes.
