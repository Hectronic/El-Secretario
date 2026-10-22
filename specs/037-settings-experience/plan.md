# Implementation Plan: Intuitive Settings With Full Control

**Branch**: `037-settings-experience` | **Status**: Implemented

## Delivery Outline

1. Inventory the existing Settings controls, QSettings keys, defaults, validators,
   runtime consumers, and effective-when semantics; add characterization tests.
2. Define canonical category and search descriptors, Basic/Advanced disclosure,
   and save/apply status without duplicating editable controls.
3. Move controls incrementally into focused `src/ui/settings/` views while keeping
   `SettingsWidget` signals and stored keys compatible.
4. Add staged edit, validation, reset, and navigation safeguards; verify secrets
   and explicit RAG actions retain their safety contracts.
5. Run focused UI/settings and consumer tests, real QSettings/Qt integration tests,
   then the full virtualenv suite. Update README and README_ES.

## Integration Boundary Decision

This redesign crosses UI/signals, QSettings persistence, runtime consumers,
and restart behavior. It requires real Qt/QSettings integration coverage, plus
focused unit tests before any behavior-sensitive refactor.

## Delivered

- Catalog and inventory cover legacy setting keys, defaults, validation,
  consumers, and apply timing across seven settings categories.
- The Settings shell now stages edits, searches and opens controls, validates and
  saves changed fields, supports per-field/category reset, and guards navigation.
- Secret reveal and copy actions are explicitly named for assistive technology;
  secret inputs no longer impose a wide minimum width.
- Pomodoro global preferences now live under Automation & notifications; its
  runtime reads the persisted interval preferences.
- README variants and Spec Kit registry updated. Focused verification: 38 passed.
  Full suite: 1003 passed, 1 skipped because the system tray is unavailable,
  and 11 subtests passed.

## Appearance follow-up (2026-10-22, REQ-037.1)

The supplied Windows screenshot showed excessive vertical gaps, cramped category rows and weak section hierarchy. `presentation.py` now owns compact panel geometry and theme-aware chrome; the shell adds the category heading, one trailing surface stretch and category-scoped advanced hints. Existing panels, QSettings keys, controls and signals are reused. No files moved.

Reviewed actual Qt offscreen screenshots in light/dark at 1220×900. Automated resize coverage compares RAG action position at 700/1000 px heights; existing narrow-window coverage remains. Live-theme regression verifies navigation rows do not overlap and controls are not recreated.

Boundary: presentation, Qt signals and QSettings. Added `test_compact_settings_layout_keeps_real_save_and_rag_actions_working` in `tests/integration/test_settings_experience.py`: actual Save persists the directory, Reload emits its saved config and category navigation keeps controls visible. Existing integration retains saved-STT/Pomodoro preference propagation.

Focused units: 30 passed with `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_audio_compression.py tests/ui/settings -q`.
Focused integration: 5 passed with `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/integration/test_recording_compression_lifecycle.py tests/integration/test_audio_compression_service.py tests/integration/test_settings_experience.py tests/integration/test_recording_player_state.py -q`.
Full Linux/offscreen suite: 1037 passed, 1 skipped (system tray unavailable), 11 subtests passed in 129.35 seconds with `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q`. Native cross-platform validation is tracked in [PR #67 checks](https://github.com/Hectronic/El-Secretario/pull/67/checks); screenshots do not certify native Windows rendering.

Narrow-window review at 680×540 exposed clipped controls in the old two-column layout. The category selector now replaces the sidebar below 860 px; geometry checks across all seven categories keep controls inside the viewport. The unit regression checks switching back to a wide window preserves the selected category.

## Windows font follow-up (2026-10-22, REQ-037.2)

Run 39813238392 passed the compression integration fix but exposed larger native text metrics in Settings. Reproduced locally by changing the QApplication system font to 14 pt; changing only the Settings widget font did not reproduce the native layout. The surface exceeded its viewport (control right edge 652 vs viewport 630). Informational labels now wrap, and long checkbox captions use a wrapping QLabel while the original checkbox keeps state, signals, keyboard focus and accessibility. No files moved.

The narrow-navigation regression now runs under both font sizes and checks the entire surface against the viewport in all seven categories. Existing real Qt/QSettings integration additionally clicks a wrapping caption and verifies the changed preference is saved. This covers the presentation → control signal → persistence boundary without replacing app components.

Focused command (30 passed, including registry checks):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_spec_registry.py tests/ui/settings -q
```

Focused integration command (7 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/integration/test_settings_experience.py tests/integration/test_pomodoro_main_window.py -q
```

Final Linux/offscreen validation: 1039 passed, 1 skipped (system tray unavailable), 11 subtests passed in 135.08 seconds with `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q`. Native results are tracked in [PR #67 checks](https://github.com/Hectronic/El-Secretario/pull/67/checks).
