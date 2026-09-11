import json

import numpy as np

from benchmarks.runtime_baseline import (
    SCENARIOS,
    _safe_startup_workload,
    capture_ui_comparison,
    main,
    run_baseline,
)
from src.audio import Recorder


def test_capture_vu_events_are_bounded_without_dropping_pcm_blocks():
    clock = [0.0]
    recorder = Recorder(amplitude_update_hz=20, monotonic_clock=lambda: clock[0])
    amplitudes = []
    recorder.amplitude_changed.connect(amplitudes.append)
    block = np.ones((160, 1), dtype=np.float32)

    recorder.callback(block, 160, None, None)
    clock[0] = 0.01
    recorder.callback(block, 160, None, None)
    clock[0] = 0.05
    recorder.callback(block, 160, None, None)

    assert len(amplitudes) == 2
    assert len(recorder.recording) == 3
    assert all(np.array_equal(saved, block) for saved in recorder.recording)


def test_runtime_baseline_covers_all_scenarios_and_required_measurements():
    results = run_baseline(repetitions=2, startup_workload=_safe_startup_workload)

    assert [result["scenario"] for result in results] == list(SCENARIOS)
    for result in results:
        assert set(result) == {
            "scenario", "commit", "platform", "python", "configuration", "repetitions",
            "median_ms", "p95_ms", "peak_rss_mb", "observed_leaks", "notes",
        }
        assert result["repetitions"] == 2
        assert result["median_ms"] >= 0
        assert result["p95_ms"] >= result["median_ms"]


def test_runtime_baseline_cli_writes_machine_readable_results(tmp_path):
    output = tmp_path / "baseline.json"

    main(["--safe-startup", "--repetitions", "2", "--output", str(output)])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "runtime-performance-baseline/v1"
    assert len(payload["results"]) == 6
    assert payload["comparisons"] == [capture_ui_comparison()]


def test_capture_comparison_records_the_measured_ui_event_reduction():
    comparison = capture_ui_comparison()

    assert comparison["before"]["values"] == [30000, 180000]
    assert comparison["after"]["values"] == [6000, 36000]
    assert comparison["improvement_percent"] == 80.0
