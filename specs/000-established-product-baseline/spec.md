# Feature Specification: Established Product Baseline

**Feature Branch**: `000-established-product-baseline`  
**Created**: 2026-09-10  
**Status**: Implemented and converged  
**Input**: Migration of the established El Secretario product contracts into GitHub Spec Kit.

## User Scenarios & Testing

### User Story 1 - Capture, transcribe, and edit audio (Priority: P1)

Users record or import audio, obtain transcription/diarization, and safely edit a
recording before retranscribing it.

**Independent Test**: Capture/editor unit tests plus SQLite edit → backup →
retranscription integration coverage.

**Acceptance Scenarios**:

1. **Given** audio is captured or imported, **When** processing completes, **Then** a recording and its transcription are persisted.
2. **Given** an edited recording, **When** changes are applied, **Then** the original is backed up and derived transcription is refreshed.

### User Story 2 - Organize and retrieve work (Priority: P1)

Users manage recordings, notes, tags, collections, notebooks, calendar views, and
semantic search without losing persisted metadata.

**Independent Test**: Persistence, calendar, notebook, RAG, and sidebar integration tests.

**Acceptance Scenarios**:

1. **Given** stored records and notes, **When** users filter or browse them, **Then** the matching persisted content is shown.
2. **Given** an indexed record, **When** users search semantically, **Then** relevant results are returned with safe fallback behavior.

### User Story 3 - Generate assistance and summaries (Priority: P1)

Users chat over selected context and create recording, daily, weekly, and batch
summaries through configured AI providers.

**Independent Test**: Chat/session, provider, summary-generation, and queue lifecycle integrations.

**Acceptance Scenarios**:

1. **Given** valid context and provider settings, **When** a chat or summary is requested, **Then** the response persists and UI state recovers after completion or failure.
2. **Given** an invalid provider configuration, **When** work starts, **Then** no invalid worker starts and the user receives an actionable message.

### User Story 4 - Manage tasks, tools, and application settings (Priority: P2)

Users review extracted tasks, run maintenance/import/export tools, and configure
themes, prompts, secrets, audio, and RAG settings.

**Independent Test**: Tasks, tools, settings, and persistence integration tests.

**Acceptance Scenarios**:

1. **Given** task and summary work is queued, **When** its state changes, **Then** boards, sidebars, and counts remain synchronized.
2. **Given** changed settings, **When** the application uses a provider, theme, or runtime, **Then** the configured policy is applied safely.

## Edge Cases

- Missing audio, invalid external configuration, unavailable GPU, broken subprocess/network edges, malformed stored context, and closed Qt tabs recover without corrupting persisted state.
- All supported desktop platforms retain safe path, Qt ownership, and runtime behavior.

## Requirements

### Functional Requirements

- **FR-001**: The application MUST capture/import, persist, transcribe, diarize, and edit recordings with safe backup and retranscription.
- **FR-002**: The application MUST persist and retrieve recordings, notes, tags, notebooks, summaries, tasks, chat sessions, and settings through compatible APIs.
- **FR-003**: The application MUST provide context-aware RAG search, chat, and AI summary workflows with recoverable errors.
- **FR-004**: The application MUST preserve real Qt signal, worker, queue, and SQLite contracts across refactors.
- **FR-005**: The application MUST run on Windows, Ubuntu, and macOS while respecting configured STT backend/device/compute policy.
- **FR-006**: Every cross-boundary change MUST have focused tests, real-boundary integration coverage when applicable, and full-suite validation.

### Key Entities

- **Record**: persisted audio or note with text, tags, metadata, and derived artifacts.
- **Chat session**: saved messages plus selected context and display state.
- **Summary task**: queued AI generation work with lifecycle and result state.
- **Task**: extracted actionable work linked to persisted records.

## Success Criteria

- **SC-001**: The full automated suite passes on the supported test runtime.
- **SC-002**: Real SQLite/Qt integration tests cover capture, editing, sessions, queues, persistence, RAG/provider, and tools boundaries.
- **SC-003**: Public façades retain their established imports and observable contracts.

## Assumptions

- External AI, STT, RAG, and audio hardware are replaceable with deterministic doubles in tests.
- The desktop application remains a local-first PyQt application backed by SQLite.
