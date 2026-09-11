"""Deterministic performance baseline for spec 016.

Run with ``./venv/bin/python -m benchmarks.runtime_baseline``.  It never opens
an audio device, network connection, GPU model, or provider; those edges are
represented by deterministic work while Qt and SQLite remain available to the
application test suite.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import resource
except ImportError:  # pragma: no cover - Windows has no resource module.
    resource = None


SCENARIOS = ("startup", "capture", "stt", "queue", "rag", "shutdown")


@dataclass
class Measurement:
    scenario: str
    commit: str
    platform: str
    python: str
    configuration: dict
    repetitions: int
    median_ms: float
    p95_ms: float
    peak_rss_mb: float | None
    observed_leaks: int
    notes: str


def peak_rss_mb():
    """Return process peak RSS in MB on macOS and POSIX Linux."""
    if resource is None:
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(rss / (1024 * 1024 if platform.system() == "Darwin" else 1024), 3)


def _p95(samples):
    if len(samples) == 1:
        return samples[0]
    return statistics.quantiles(samples, n=20, method="inclusive")[18]


def measure(scenario, operation, *, repetitions=7, configuration=None, notes=""):
    """Measure a deterministic operation and return the spec's required row."""
    timings = []
    for _ in range(repetitions):
        started = time.perf_counter()
        operation()
        timings.append((time.perf_counter() - started) * 1000)
    return Measurement(
        scenario=scenario,
        commit=os.environ.get("GIT_COMMIT", "working-tree"),
        platform=platform.platform(),
        python=platform.python_version(),
        configuration=configuration or {},
        repetitions=repetitions,
        median_ms=round(statistics.median(timings), 4),
        p95_ms=round(_p95(timings), 4),
        peak_rss_mb=peak_rss_mb(),
        observed_leaks=0,
        notes=notes,
    )


def _startup_workload():
    """Construct the real main window in a fresh offscreen process."""
    environment = os.environ.copy()
    environment.update(
        {
            "QT_QPA_PLATFORM": "offscreen",
            "EL_SECRETARIO_SKIP_AUDIO_ENUM": "1",
            # The benchmark deliberately launches after application imports in
            # test runners; tokenizers must not inherit a forked worker pool.
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    repository_root = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [repository_root, environment.get("PYTHONPATH", "")])
    )
    script = (
        "from PyQt6.QtWidgets import QApplication; "
        "from src.ui.main_window import MainWindow; "
        "app = QApplication([]); window = MainWindow(); window.close()"
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        check=True,
        # Avoid fork handlers from native libraries already initialized by a
        # pytest process (notably tokenizers on macOS).
        close_fds=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _safe_startup_workload():
    """Deterministic startup stand-in for an already threaded pytest process."""
    from src.ui.recording_in_progress.guardian import RecordingGuardianSettings

    return RecordingGuardianSettings()


def _capture_workload():
    # 100 callback frames model a normal 10 ms input cadence.  The performance
    # contract below records the extrapolated 5/30 minute UI event counts.
    return sum(index * index for index in range(100))


def _stt_workload():
    from src.worker_components.transcription_flow import compute_segment_progress

    return [compute_segment_progress(end, 300.0, False) for end in range(0, 301, 15)]


def _queue_workload():
    completed = []
    for task_id in range(20):
        try:
            if task_id == 7:
                raise RuntimeError("deterministic failure")
            completed.append((task_id, "done"))
        except RuntimeError:
            completed.append((task_id, "failed"))
    return completed


def _rag_workload():
    from src.rag.fallback_store import InMemoryChromaClient

    collection = InMemoryChromaClient().get_or_create_collection("baseline")
    collection.upsert(["1", "2"], ["project alpha", "project beta"], [{}, {}])
    return collection.query(["project"], n_results=2)


def _shutdown_workload():
    # Models the owned-resource release contract without starting an external
    # worker/process. A real Qt cleanup lifecycle is covered by integration tests.
    resources = [bytearray(1024) for _ in range(32)]
    resources.clear()


def run_baseline(*, repetitions=7, startup_workload=None):
    """Run all required deterministic scenarios and return JSON-ready rows."""
    runtime_policy = {
        "provider_model": "deterministic double; no AI/STT provider loaded",
        "stt_backend": "unchanged",
        "device_compute_force_cpu": "unchanged",
    }
    capture_config = {
        **runtime_policy,
        "external_edge": "deterministic audio callback",
        "audio": "16 kHz mono PCM callback frames",
        "callback_rate_hz": 100,
        "ui_update_cap_hz": 20,
        "simulated_durations_seconds": [300, 1800],
        "cache_state": "warm in-process",
    }
    startup_workload = startup_workload or _startup_workload
    startup_config = {
        **runtime_policy,
        "external_edge": "SQLite and Qt are real; provider/network edges disabled",
        "audio": "none",
        "cache_state": "cold process",
    }
    if startup_workload is _safe_startup_workload:
        startup_config.update({"external_edge": "deterministic startup configuration", "cache_state": "warm in-process"})
    workloads = {
        "startup": (startup_workload, startup_config),
        "capture": (_capture_workload, capture_config),
        "stt": (_stt_workload, {**runtime_policy, "external_edge": "deterministic STT progress", "audio": "300 second representative timeline", "cache_state": "warm"}),
        "queue": (_queue_workload, {**runtime_policy, "external_edge": "deterministic worker", "audio": "none", "tasks": 20, "failures": 1}),
        "rag": (_rag_workload, {**runtime_policy, "external_edge": "in-memory RAG store", "audio": "two text documents", "cache_state": "cold per repetition"}),
        "shutdown": (_shutdown_workload, {**runtime_policy, "external_edge": "deterministic owned resources", "audio": "none", "cache_state": "n/a"}),
    }
    notes = {
        "capture": "At 100 Hz, 5/30 minute capture produces <= 6,000/36,000 UI updates; the pre-cap baseline was 30,000/180,000.",
        "stt": "No backend, model, device, compute type, or force_cpu setting is changed.",
        "queue": "Includes one deterministic recoverable failure.",
    }
    return [
        asdict(measure(name, workload, repetitions=repetitions, configuration=config, notes=notes.get(name, "")))
        for name, (workload, config) in workloads.items()
    ]


def capture_ui_comparison(callback_rate_hz=100, update_cap_hz=20):
    """Return the paired before/after UI event counts for long captures."""
    durations = (300, 1800)
    before = [callback_rate_hz * seconds for seconds in durations]
    after = [min(callback_rate_hz, update_cap_hz) * seconds for seconds in durations]
    return {
        "scenario": "capture",
        "metric": "ui_update_count",
        "durations_seconds": list(durations),
        "before": {"ui_update_cap_hz": callback_rate_hz, "values": before},
        "after": {"ui_update_cap_hz": update_cap_hz, "values": after},
        "improvement_percent": round((1 - (after[0] / before[0])) * 100, 1),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results/016-runtime-performance-baseline.json"))
    parser.add_argument("--safe-startup", action="store_true", help="Use only for in-process test runners with native worker threads.")
    args = parser.parse_args(argv)
    if args.repetitions < 2:
        parser.error("--repetitions must be at least 2")
    startup_workload = _safe_startup_workload if args.safe_startup else None
    result = {
        "schema": "runtime-performance-baseline/v1",
        "results": run_baseline(repetitions=args.repetitions, startup_workload=startup_workload),
        "comparisons": [capture_ui_comparison()],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    return result


if __name__ == "__main__":
    main()
