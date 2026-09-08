# SPEC-014: Export, Import, Maintenance, And Tools

Status: Implemented
Owner: TBD
Last updated: 2026-09-08

## Problem

Users need one safe place to maintain stored data, run batch workflows, move data between installations, and request RAG maintenance.

## Scope

- In scope: tools tab composition, maintenance, data export/import, batch tool access, and RAG reindex queue requests.
- Out of scope: data file format internals and RAG indexing implementation.

## Acceptance Criteria

- Given a Tools tab is opened with injected persistence, when batch subtabs are created, then every batch widget uses that same persistence port.
- Given a RAG scope is selected, when the user queues a reindex, then the central queue receives the selected scope and the UI reports accepted or duplicate requests.
- Given an export/import succeeds, when the action completes, then the UI reports record, session, and notebook counts.

## Architecture Notes

- `src/ui/tools_widget.py` is the tabbed Qt façade.
- `src/ui/tools/rag.py` owns reindex submission status policy; `src/ui/tools/data_transfer.py` owns exporter/importer invocation and success-message formatting.
- Batch subwidgets receive the same injected persistence port supplied to `ToolsWidget`.

## Test Plan

- Unit: RAG queue result policy and import/export status formatting under `tests/ui/tools/`.
- Integration: `tests/integration/test_tools_widget_ports.py` verifies real SQLite persistence injection across all batch tabs and RAG queue submission.

## Refactor Notes

- 2026-09-08: extracted RAG and data-transfer actions to `src/ui/tools/` and corrected batch-tab persistence injection.
