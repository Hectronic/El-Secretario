---
name: refactor-workflow
description: Use when the user asks to refactor, split, reorganize, or simplify code. First raise coverage around the target area to a reasonable level, then refactor incrementally, run focused and full tests, and adjust until behavior is stable. Combine with project development and PyQt testing standards when working in this repository.
---

# Refactor Workflow

Use this skill for refactors that change structure more than behavior.

## Workflow

1. Scope the target.
- Identify the files, modules, and public APIs that are in scope.
- Prefer small, incremental refactors over broad rewrites.

2. Raise coverage first.
- Add or expand tests for the target area before changing implementation.
- Cover the main path, one edge case, and one regression risk.
- If the area is fragile, keep adding tests until the behavior is well pinned down.

3. Refactor in small steps.
- Preserve the external API unless the user explicitly asks for a breaking change.
- Extract reusable code instead of duplicating logic.
- Move code only when tests already cover the behavior you are moving.

4. Validate after each meaningful step.
- Run targeted tests for the touched module first.
- Fix failures immediately.
- Run the full suite before finishing.

5. Adjust and tighten.
- If the refactor exposes ambiguity, add another test and simplify the implementation.
- If the change affects runtime behavior, document the new rule in the code or tests.

## Repository Defaults

- Follow the project GPL header and test layout rules.
- Use the project venv and Qt headless settings for Python/PyQt tests.
- Do not force CPU or weaken runtime selection unless the refactor is specifically about fallback behavior.
- Follow the refactored UI architecture in this repo:
  - `src/ui/main_window/` is a package of focused coordinators, not a single growing file.
  - `src/ui/chat/` holds chat-specific helpers and dialog logic.
  - Shared chat context UI belongs in `src/ui/context_manager_panel.py`.
  - New tests should mirror these package boundaries under `tests/ui/`.
- Prefer extracting helpers into the owning feature package before moving code across unrelated areas.
- Keep temporary compatibility imports/shims only during migration, and remove them once callers are updated.

## When To Use

- Splitting a large file into smaller components.
- Removing duplication between adjacent modules.
- Reorganizing a feature by responsibility.
- Cleaning up worker, UI, or provider code without changing the user-facing contract.
