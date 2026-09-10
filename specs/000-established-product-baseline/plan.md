# Implementation Plan: Established Product Baseline

**Branch**: `000-established-product-baseline` | **Date**: 2026-09-10 | **Spec**: [spec.md](spec.md)

## Summary

This is the converged plan for the already implemented desktop product. Its
architecture uses feature packages for UI/runtime concerns, aggregate repositories
for SQLite, compatibility façades for stable imports, and real-boundary integration
tests for shared contracts.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: PyQt6, pytest, local Whisper/STT adapters, AI provider adapters  
**Storage**: SQLite  
**Testing**: pytest + pytest-qt in offscreen mode  
**Target Platform**: Windows, Ubuntu, macOS desktop  
**Project Type**: local-first desktop application

## Constitution Check

Passed. The current code keeps compatible façades (`DBManager`, `RAGEngine`,
`MainWindow`, queue/UI shims), uses real SQLite and Qt boundaries in integration
tests, and preserves platform/runtime guards.

## Product Capability Map

| Slice | Main ownership | Representative verification |
| --- | --- | --- |
| Capture/import | `src/ui/welcome/`, `src/ui/recording_in_progress/` | `test_recording_in_progress_lifecycle.py` |
| STT/diarization | `src/worker_components/`, `src/stt_providers/` | `tests/worker/`, `tests/stt_providers/` |
| Recording metadata | `src/ui/recording/`, `src/persistence/records.py` | `test_recording_widget_persistence.py` |
| Audio editor | `src/ui/audio_editor/` | `test_audio_editor_persistence.py` |
| RAG | `src/rag/` | `test_rag_engine_contract.py` |
| Chat/context | `src/ui/chat/`, `src/ui/main_window/` | `test_chat_session_persistence.py`, `test_chat_window_persistence.py` |
| Calendar/notebooks/tags | `src/ui/calendar*`, `src/ui/notebooks/` | calendar/sidebar/notebook integrations |
| Summaries/queues | `src/app/summary_queue/`, `src/app/summaries/` | summary generation and queue integrations |
| Tasks/tools/settings | `src/ui/tasks/`, `src/ui/tools/`, `src/ui/settings/` | task/tools/provider integrations |

## Project Structure

```text
src/                 # PyQt UI, workers, adapters, persistence, application services
tests/               # unit, UI, worker, persistence, and integration tests
specs/000-established-product-baseline/
├── spec.md          # product requirements and acceptance scenarios
├── plan.md          # current architecture and verification mapping
└── tasks.md         # completed implementation and closure work
.specify/memory/constitution.md
```

## Refactor Decisions

- Feature packages own focused UI behavior; broad modules remain only as compatible façades.
- SQLite operations are split by aggregate below `src/persistence/`.
- AI/STT/RAG worker lifecycles are isolated from presentation and always clean up resources.
- No structural hotspot remains confirmed; future extraction requires a concrete ownership conflict rather than size alone.
