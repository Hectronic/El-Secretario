---
name: integration-testing
description: Add and validate meaningful cross-component tests for this repository when a change crosses UI, persistence, workers, queues, runtime adapters, or platform boundaries.
---

# Integration Testing

Use this skill when a change crosses component boundaries. Keep unit tests for local
logic; integration tests prove that independently owned components still honor their
observable contract together.

## Scope and Design

- Start by checking existing tests. Extend an existing integration test when it
  already owns the user flow; otherwise add one under `tests/integration/`.
- Use a temporary SQLite database and real Qt signals with `QT_QPA_PLATFORM=offscreen`.
- Replace only nondeterministic external edges (AI, STT, RAG, audio hardware, network)
  with deterministic doubles. Do not replace the components whose integration is being
  tested.
- Assert outcomes users or downstream components observe: persistence, emitted
  signals, UI status/history, resource cleanup, or continuation after failure.
- Cover the success path and the relevant failure/recovery path when workers, queues,
  STT, RAG, or persistence are involved.

## Required Validation

1. Run focused unit tests for every touched owner package.
2. Run the focused integration tests, including any existing test that owns the flow.
3. Run `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`
   for cross-component changes.
4. Update the relevant `SPEC-XXX` test plan with the contract and test path.

Report the exact focused and full commands, their results, and the contract covered.
