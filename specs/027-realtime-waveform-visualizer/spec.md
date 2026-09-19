# SPEC-027: Real-Time Audio Waveform Visualizer

Status: Implemented and validated
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-18

## Problem and scope
The active recording screen displays only the instantaneous level. Replace its
progress bar with a scrolling amplitude history owned by
`src/ui/recording_in_progress/waveform.py`. The notebook and microphone setup
meters remain outside this feature.

## Product contract
- `RealTimeWaveformVisualizer` renders a symmetric, antialiased envelope using
  QPainterPath, with the newest level at the right and a centered silent baseline.
- Consume the existing `Recorder.amplitude_changed(float)` RMS signal, capped at
  20 Hz. These are aggregated levels, not raw PCM, a frequency spectrum, or a
  reconstruction of the original waveform. Do not change audio capture or storage.
- Keep exactly 80 display levels (approximately four seconds at 20 Hz), initially
  zero. Apply the previous meter's gain of 10, clamp to [0, 1], and treat nonfinite
  values as silence. Geometry stays within the widget even at clipping levels.
- Read Window, Mid and Highlight from the current Qt palette on every paint;
  palette changes must take effect without recreating the widget.
- Use heights of 48/64 for compact/regular layouts and an expanding horizontal size policy
  so the centered waveform occupies the available recording-view width.
- During pause ignore incoming levels and decay the existing envelope by 0.75
  every 50 ms, snapping values below 0.001 to zero. Stop the timer when silent;
  resume accepts new levels immediately and stops decay. No animation timer runs
  during active capture or after cleanup.
- Finish, cancel, close and failed startup leave a silent inactive visualizer.
  Cleanup is idempotent; already queued amplitude deliveries cannot revive it.
- Route recorder updates through a QObject slot on the UI thread; preserve
  guardian activity handling and recorder signal disconnection.

## Acceptance and integration gate
This change crosses the recorder signal / Qt UI / capture lifecycle boundary.
Unit tests cover history limits, normalization, drawing bounds and symmetry,
rendered palette changes, pause decay, resume and disposal. Integration tests
use real Qt signals, a temporary SQLite database, and deterministic audio/tray
edges; verify delivery from a worker thread, pause/resume, terminal cleanup and
startup failure. The real Recorder callback test proves 20 Hz throttling without
losing PCM blocks. Run focused tests before the complete suite in offscreen mode.
