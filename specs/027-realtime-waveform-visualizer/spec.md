# SPEC-027: Real-Time Audio Waveform Visualizer

Status: Draft
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-17

## Problem
The current VU-meter used during active recording sessions is a simple vertical/horizontal static green bar indicating instant sound level. While functionally correct, it lacks visual responsiveness, does not show audio frequency or wave historical trends, and feels aesthetically rigid. Modern recording applications use live sinusoidal waveform drawing to provide highly engaging visual feedback to the user.

## Proposal
Replace the existing VU-meter widget with a custom QWidget-based `RealTimeWaveformVisualizer` that caches historical PCM amplitudes and renders a smooth, antialiased, scrolling wave graph inside the recording view.

### Key Highlights
- **Custom Painting with QPainter:** Use standard vector path rendering (`QPainterPath`) to draw symmetric picos and valles centered around a horizontal baseline.
- **Historical Amplitude Buffer:** Maintain a circular buffer (e.g. 50-100 values) of raw PCM amplitudes, pushing new samples and popping oldest.
- **Theme Reactivity:** Render the waveform using colors matching the currently active theme (Light, Dark, or SNES/Retro) dynamically read from the app palette.
- **High responsiveness:** Feed updates via the existing 20 Hz `amplitude_changed` signal emitted from the non-blocking `Recorder` stream loop.

## User Scenarios & Testing
- **Scenario:** The user starts a recording. The waveform visualizer begins centered at zero. As the user speaks, the widget renders dynamic peaks proportional to the voice volume, scrolling smoothly from right to left.
- **Testing:** Verify with unit tests that the visualizer successfully maintains its buffer limits, repaints on signal delivery, and releases resource allocations upon window closure.
