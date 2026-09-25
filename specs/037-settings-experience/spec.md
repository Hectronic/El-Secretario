# SPEC-037: Intuitive Settings With Full Control

Status: Proposed
Owner: Settings experience
Last updated: 2026-09-25

## Problem

Settings currently span General, Audio, RAG, and Prompts tabs. General mixes AI
providers, appearance, automation, and external integrations; Audio mixes device
selection, recording safety, and transcription runtime. The long forms make a
specific option hard to find and make it unclear which changes are saved, applied
immediately, or require a restart. Users need clearer grouping without losing
access to advanced controls.

## Scope

- In scope: information architecture, searchable settings, clear descriptions and
  defaults, Basic/Advanced disclosure, validation and save feedback, reset per
  setting/section, status for restart-required changes, keyboard accessibility,
  and navigation from relevant workflows to a setting.
- Out of scope: changing provider, STT, RAG, recording, or API runtime policy;
  removing existing options; changing credential storage; automatic tuning of
  hardware settings; and broad redesign of the application outside Settings.

## User Stories

### US1 - Find an option quickly

As a user, I can browse settings by familiar task or search by a setting name,
keyword, or description, so I do not need to know which old tab contains it.

### US2 - Change a preference confidently

As a user, I can see the current value, default, consequence, and whether a
change needs a restart. I can save or discard edits without accidentally changing
unrelated preferences.

### US3 - Keep expert control

As an advanced user, I can reveal backend, model, device, compute, indexing, and
integration options and reach the same controls available before the redesign.

## Proposed Navigation

The default view uses a persistent category list and a compact summary of each
category. Search results point to the original setting in its category rather
than creating a second editable copy.

| Category | Example controls | Source today |
| --- | --- | --- |
| Appearance & language | Theme, summary language | General |
| Recording & devices | Microphone, system audio, recording safety | Audio |
| Transcription & speakers | Backend/model, device/compute policy, diarization token | Audio, General |
| AI & chat | Provider, model, credentials, prompts | General, Prompts |
| Search & knowledge | RAG runtime, indexing and reindex actions | RAG, Audio |
| Automation & notifications | Startup summaries, recording reminders; later Pomodoro/meeting reminders | General, Audio |
| Integrations | Local API, MCP | General |

Basic mode presents the common controls and a concise summary of active advanced
choices. Advanced mode reveals all supported parameters in place; it does not
change values by itself. Category and disclosure state are remembered locally.

## Functional Requirements

- **FR-001**: Every existing editable setting and Settings action has one
  canonical location in the new navigation. Before implementation, an inventory
  maps each existing QSettings key, default, validator, consumer, and old UI
  control to that location. No setting silently disappears or changes meaning.
- **FR-002**: Search matches visible labels, descriptions, and relevant synonyms
  (for example “micrófono”/“microphone” and “GPU”/“CUDA”). Results identify the
  category and open the control with focus; clearing search restores the prior
  category and unsaved edits.
- **FR-003**: Every setting shows a readable label, short help text, current
  value, and reset-to-default action. Advanced controls remain keyboard and
  screen-reader accessible while collapsed controls are not focusable.
- **FR-004**: Settings distinguish immediate application, next-job application,
  and restart-required application. Saved-but-not-yet-active settings show a
  persistent status until they take effect; a requested restart uses the existing
  safe restart flow.
- **FR-005**: Edits are staged where possible. Save validates the changed fields,
  writes only valid values, reports which settings were saved, and preserves
  unrelated stored keys. Discard restores persisted values, including across
  categories. Navigating away with edits offers Save, Discard, or Stay.
- **FR-006**: Validation is inline, specific, and non-destructive. An invalid
  value does not overwrite the previous saved value; a failed apply operation
  reports the saved/active difference and offers a safe retry where supported.
- **FR-007**: Reset is available per setting and per category with an explicit
  preview/confirmation for the latter. Resetting one category leaves all other
  values, tokens, and custom prompts unchanged.
- **FR-008**: Secret fields remain masked by default; reveal and copy require an
  explicit action. Search and status messages never expose secret values.
- **FR-009**: Contextual entry points may open a category and focus a specific
  setting, such as a microphone error opening Recording & devices. Returning to
  Settings later restores the last manually visited category.
- **FR-010**: On narrow windows, navigation and fields remain usable without
  clipped controls or horizontal scrolling. Labels and status do not rely on
  icons or color alone; light/dark and Windows, Ubuntu, and macOS are supported.
- **FR-011**: New settings from SPEC-034/035/038 are placed in the relevant
  category when those features land, using the same search and status metadata.

## Compatibility And Ownership

- `src/ui/settings/` owns the Settings shell, navigation, descriptors, and
  category views. The existing `SettingsWidget` public signals and QSettings
  store remain compatible during incremental migration.
- Feature owners still define runtime defaults, allowed values, and apply timing:
  SPEC-013 for provider/theme/RAG configuration, SPEC-002 for STT, SPEC-015 for
  recording safety, SPEC-034/035 for productivity reminders, and SPEC-024/025 for
  external integrations.
- RAG initialize/reload/reindex actions remain explicit commands, clearly
  separated from saving preferences; opening or searching Settings cannot run
  them.
- Existing stored values must round-trip unchanged unless a targeted migration
  is documented and tested. Credential values never appear in diagnostics.

## Acceptance Criteria

1. Given a user searches for “microphone”, when a result is selected, then the
   Recording & devices control is focused with its saved value intact.
2. Given Advanced mode is hidden, when it is revealed, then all existing backend,
   device, compute, RAG, prompt, and integration controls remain reachable and
   retain their stored values.
3. Given an invalid model/device value and a valid theme change, when Save is
   selected, then the invalid value is not persisted and the UI clearly states
   what was saved and what still needs correction.
4. Given edits in two categories, when the user attempts to leave Settings, then
   Save, Discard, and Stay preserve or revert the complete staged edit set as
   chosen.
5. Given a restart-required value is saved, when Settings is reopened before a
   restart, then the pending status remains visible and the active runtime value
   is distinguishable from the saved value.
6. Given a category reset is confirmed, when Settings is saved, then only that
   category’s defaults are applied; secrets and other categories remain intact.
7. Given an existing QSettings store from the current release, when the new
   Settings opens and saves an unrelated option, then all legacy settings and
   feature consumers retain their values and behavior.

## Test Plan

- Characterization: inventory current keys and cover their load/save round trips
  before moving controls.
- Unit/UI: category mapping and search, Basic/Advanced disclosure, reset scope,
  validation, dirty state, focus, secret masking, and apply status.
- Integration: a temporary real QSettings store plus real Qt signals in offscreen
  mode verifies old-value migration-free round trips and Settings save → active
  runtime consumer; external provider/network edges use deterministic doubles.
- Full suite: required because this crosses shared UI, settings persistence,
  provider/STT/RAG consumers, and restart behavior.

## Documentation

- Update README and README_ES with the new navigation and the distinction between
  saving, applying, and restarting when implementation begins.
- Register implementation status in `specs/README.md`.
