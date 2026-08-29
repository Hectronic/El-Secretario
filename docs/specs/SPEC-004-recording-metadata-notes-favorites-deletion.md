# SPEC-004: Recording Metadata, Notes, Favorites, And Deletion

Status: Implemented
Owner: TBD
Last updated: 2026-06-03

## Problem

Users need a recording detail view that lets them review and maintain the saved transcription and related recording metadata without losing the link to the source audio.

## Scope

- In scope: recording title, tags, notes, diarization metadata, transcription text editing, speaker-label renaming, copying the full transcription, favorites/deletion flows, audio playback controls, legacy trim-and-retranscribe controls, and recording-level AI actions.
- Out of scope: transcription runtime selection, waveform audio editing, chat sessions, summaries queue internals, and database schema redesign.

## User Stories

- As a user, I want to edit a recording title, tags, notes, and transcription so that saved meeting context stays accurate.
- As a user, I want to copy the full transcription with one action so that I can paste it elsewhere without manually selecting long text.
- As a user, I want recording deletion to remove the app record and associated search index entry so that stale content does not remain available.

## Acceptance Criteria

- Given a recording has a transcription, when the recording detail tab is open, then the Original tab exposes a copy action for the full transcription.
- Given the copy action is clicked, when transcription text exists, then the complete transcription is placed on the system clipboard without requiring text selection.
- Given a recording has notes but no transcription, when the recording detail tab is open, then transcription copy remains disabled while AI actions may still use notes.
- Given the recording detail tab has no unsaved edits, when it is displayed, then the Save All Changes action in the bottom action bar is disabled.
- Given metadata, notes, transcription, tags, diarization, or audio trim fields change, when dirty tracking is active, then the bottom Save All Changes action becomes enabled and uses the primary blue button styling.
- Given metadata or transcription edits are saved, when persistence succeeds, then the tab is marked clean, the Save All Changes action is disabled, and interested sidebars are notified.
- Given a recording is deleted, when the user confirms deletion, then the database row, local audio file when present, and RAG document when available are removed.

## Architecture Notes

- UI: `src/ui/recording_widget.py` owns high-level recording tab orchestration. `src/ui/recording/transcription_panel.py`, `metadata_panel.py`, `content_tabs.py`, and `actions_bar.py` own focused UI construction. `src/ui/recording/controls.py` owns shared recording-tab button/playback-control factories so action styling, playback controls, and enabled-state defaults stay consistent.
- UI helpers: `src/ui/recording/state.py` owns small non-visual helpers for record paths, AI-text presence, fallback labels, and settings booleans. `src/ui/recording/ai_actions.py`, `speaker_actions.py`, and `audio_trim.py` own queue-facing AI actions, speaker-label mapping, and legacy trim validation/backup helpers. `src/ui/recording/rag_indexing.py` owns recording-tab RAG auto-index checks and add-document side effects after save or direct transcription.
- Services: AI actions are routed through the summary task queue when available; legacy trim uses safe `.orig` backup creation before overwriting the source audio and retranscribing.
- Persistence: `src/database.py` persists recording metadata, transcription, notes, tags, and deletion.
- Workers/integrations: `src/ui/recording/transcription_flow.py` owns direct transcription startup, preflight, runtime worker kwargs, thread wiring, queue traces, and persistence of direct transcription results before the recording detail view refreshes.
- Platform constraints: Clipboard behavior uses Qt application clipboard APIs and must work on Ubuntu and Windows.

## Test Plan

- Unit/UI: recording control factories, panel builders, non-visual recording helpers, direct transcription flow helpers, AI action helpers, RAG indexing helpers, speaker mapping helpers, trim validation/backup helpers, recording widget tab composition, copy button state, full-transcription clipboard copy, notes-only state, save/delete behavior, and bottom action dirty-state behavior.
- Integration: recording flow and tab lifecycle coverage for open/save/delete workflows.
- Manual: open a transcribed recording, click Copy Transcription, and paste into another app on Ubuntu and Windows.

## Documentation

- README: feature list mentions one-click full-transcription copying.
- Other docs: `docs/specs/README.md` links this spec and records `src/ui/recording/` as the focused recording UI package.

## Open Questions

- Should the same copy action eventually be exposed from history context menus or search results?
