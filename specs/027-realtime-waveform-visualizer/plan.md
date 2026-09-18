# Implementation Plan: Real-Time Audio Waveform Visualizer

Status: Draft
Last updated: 2026-09-17
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Custom Widget Creation
- Subclass `QWidget` to create `RealTimeWaveformVisualizer`.
- Set fixed or layout-stretching dimensions appropriate for the recording view header.
- Implement a circular buffer (e.g., `collections.deque` with a `maxlen` of 80) to store amplitude values.

### Phase 2: Painting Mechanics
- Implement `paintEvent` inside the custom widget.
- Use `QPainterPath` to render a double-sided (top and bottom) symmetric wave around a middle horizontal axis.
- Apply `QPainter.RenderHint.Antialiasing` to make wave edges perfectly smooth.
- Retrieve active palette colors (window, mid, highlight) to theme the wave pen and fill brush.

### Phase 3: Signal Wiring
- Connect the `amplitude_changed(float)` signal from the active recording instance to append values to the visualizer deque and trigger `update()`.
- Add a smooth-decay timer to fade the wave down to a quiet baseline when the recorder is paused.
