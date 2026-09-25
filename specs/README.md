# El Secretario Spec Kit Features

Each feature directory follows the GitHub Spec Kit layout: `spec.md`, `plan.md`,
and `tasks.md`. Historical baseline tasks are complete; proposed features retain
their implementation checklist here until delivery.

- `001-audio-capture-import`
- `002-transcription-runtime`
- `003-diarization-speakers`
- `004-recording-metadata`
- `005-audio-editor`
- `006-rag-search`
- `007-chat-sessions`
- `008-chat-context-sidebar`
- `009-calendar-context`
- `010-collections-notebooks`
- `011-summaries-queue`
- `012-tasks-board`
- `013-settings-runtime`
- `014-tools-data-management`
- `015-recording-safety-guardian` — implemented and validated
- `016-runtime-performance-baseline` — completed and validated
- `017-stability-hardening` — completed and validated
- `018-lightweight-runtime` — planned
- `019-knowledge-workflows` — planned
- `034-pomodoro-timeline` — implemented; SQLite/Qt integration and full-suite validated
- `035-recurring-meetings` — proposed
- `036-chat-ux-workflows` — proposed
- `037-settings-experience` — proposed
- `038-tray-quick-actions` — proposed

## Roadmap relationship

The planned work is intentionally staged:

1. `016-runtime-performance-baseline` measures before optimization.
2. `017-stability-hardening` strengthens lifecycle and failure contracts.
3. `018-lightweight-runtime` reduces installation and cold-start cost without
   changing provider behavior.
4. `019-knowledge-workflows` deepens indexing, provenance, and resumable
   knowledge features.

`015-recording-safety-guardian` can proceed alongside the baseline when its
recording-specific contracts are implemented.

## Cross-feature invariants

- `016` owns measurements and accepted performance thresholds; later specs must
  reference its baselines rather than inventing unmeasured targets.
- `017` owns lifecycle, failure, cancellation, retry, and cleanup semantics.
- `018` owns packaging, capability detection, lazy imports, and cold-start cost.
- `019` owns indexing freshness, provenance, and resumable knowledge workflows.
- Existing compatibility façades (`DBManager`, `RAGEngine`, legacy widgets) are
  preserved unless a future spec explicitly defines a migration.
- `034` owns focused-work sessions and the user-visible activity timeline.
- `035` owns recurring-meeting definitions, occurrence scheduling, and reminder
  dispatch; it may create timeline events defined by `034`.
- `036` owns chat interaction and presentation workflows; it consumes context and
  provenance from `007`, `008`, and `019` without redefining their data policies.
- `037` owns settings navigation, presentation, validation, and discoverability;
  setting values and runtime semantics remain with their feature owners.
- `038` owns tray menu actions and state presentation; capture, Pomodoro, and
  meeting operations are delegated to their existing or proposed feature owners.
