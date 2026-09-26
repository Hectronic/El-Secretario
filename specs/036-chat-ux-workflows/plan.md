# Implementation Plan: Useful And Intuitive Chat Workflows

**Branch**: `036-chat-ux-workflows` | **Status**: Proposed

## Delivery Outline

1. Add focused tests for the existing composer, pending/error state, source
   presentation, session search, and floating/docked state before behavior moves.
2. Extract or extend narrowly owned chat presentation-state helpers while keeping
   `ChatWidget` and conversation runtime compatibility boundaries intact.
3. Implement starter prompts, composer/draft behavior, context summary, response
   actions, source presentation, and local session search incrementally.
4. Verify cancellation/retry and floating lifecycle through real Qt signals and
   temporary SQLite, then run the full virtualenv suite.
5. Update English and Spanish documentation after user-visible behavior lands.

## Integration Boundary Decision

This feature crosses chat UI/signals, worker lifecycle, session persistence,
context synchronization, and floating main-window behavior. It requires real
SQLite plus Qt-signal integration coverage; provider and RAG boundaries may use
deterministic doubles.
