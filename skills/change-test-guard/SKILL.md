---
name: change-test-guard
description: "Implement code changes with mandatory test safety checks. Use when a request asks to fix bugs, add features, refactor behavior, or touch production code and also requires confidence via tests: add or update tests, run focused tests for changed behavior, then run the full suite before finishing."
---

# Change Test Guard

Follow this workflow for every code change.

## Workflow

1. Reproduce and scope.
- Identify affected modules and expected behavior.
- Run the smallest failing or relevant test first.

2. Implement minimal code change.
- Modify only files required for the requested behavior.
- Avoid unrelated refactors in the same patch.

3. Add or update tests for the change.
- Add a new test for new behavior.
- Update existing tests only when behavior is intentionally changed.
- Cover success path and at least one edge or failure path.

4. Run targeted tests first.
- Execute tests directly related to changed files or features.
- Fix failures before broader runs.
- Prefer commands like `pytest tests/path/test_file.py -q` or `pytest -k "feature_name" -q`.

5. Run full regression suite.
- Run the complete project suite (for example `pytest`).
- Do not conclude while the suite is red unless the user explicitly accepts unrelated known failures.

6. Report with proof.
- Summarize code changes.
- List tests added/updated.
- Report targeted and full-suite results with pass/fail counts.
- Call out residual risks if coverage is still partial.

## Test Selection Rules

- Prefer narrow test runs for fast feedback during iteration.
- Always finish with a full suite run.
- If full suite is too expensive, run the best available near-full command and clearly state the gap.
- If a flaky or unrelated failure appears, document the exact failing test and why it is out of scope.

## Quality Bar

- Reject fixes that only silence errors without validating behavior.
- Keep tests deterministic and isolated.
- Prefer assertions on behavior over implementation details.

## Example Trigger Phrases

- "Arregla este bug y asegúrate de que no rompe nada."
- "Haz el cambio y añade tests."
- "Pasa toda la batería después del fix."
- "Implementa esto con cobertura y regresión completa."
