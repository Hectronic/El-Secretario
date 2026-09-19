# SPEC-030: Media Player State Pattern

Status: Implemented
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-19

## Problem
The audio player logic in `RecordingWidget` relies on direct conditional state checks when managing the multimedia `QMediaPlayer` backend. State transitions (Playing, Paused, Stopped, Trimming) are managed via flag checking scattered across different slot connections. This leads to fragile state transitions, GUI button mismatching, or potential null pointer exceptions in asynchronous audio events, especially on platforms with differing gstreamer or directshow dependencies.

## Proposal
Isolate audio player controls by restructuring the reproduction state flow under the classic State Design Pattern. All player behaviors (play, pause, stop, set_position, start_trim) will delegate their calls to a polymorphic `PlayerState` object.

### Key Highlights
- **State Pattern Architecture:** Create a state base interface `PlayerState` and concrete state implementations (`StoppedState`, `PlayingState`, `PausedState`, `TrimmingState`).
- **Encapsulated Transitions:** Encapsulate transition safety rules inside states (e.g. calling `pause` inside `StoppedState` is safely ignored or disabled, while calling it inside `PlayingState` cleanly transitions to `PausedState` and pauses `QMediaPlayer`).
- **Clean UI Synchronization:** Let each State class control which UI player buttons (Play, Pause, Stop, Trim sliders) are enabled or disabled, eliminating cluttered flag checking in UI files.

## User Scenarios & Testing
- **Scenario:** The user clicks the Trim Audio button during active reproduction. The player state smoothly transitions from `PlayingState` to `TrimmingState`, pausing playback, locking playback sliders, and displaying the trim handles safely without race conditions.
- **Testing:** Add unit tests using MagicMocks to drive state transitions sequentially, asserting that forbidden transitions are blocked and that correct `QMediaPlayer` calls are invoked at each stage.

## Implementation
The player controls of `RecordingWidget` are now delegated to `MediaPlayerContext` and its `PlayerState` hierarchy. `StoppedState`, `PlayingState`, `PausedState`, and `TrimmingState` own valid playback transitions and synchronize Play, Pause, Stop, seek, and trim controls. The existing widget methods and `RecordingActionsCoordinator` remain as compatibility entry points that forward to the context.

Audio trimming enters `TrimmingState`, which pauses active playback and locks playback controls while keeping trim inputs available. Completing or failing the trim returns the context safely to `StoppedState`.
