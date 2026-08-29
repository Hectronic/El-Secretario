# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import gc
import logging
from typing import Any, Dict, Iterable, Tuple


def stop_worker(worker: Any, *, timeout_ms: int = 15000, force_timeout_ms: int = 5000, log_context: str = "") -> None:
    if worker is None:
        return
    try:
        if hasattr(worker, "cancel"):
            worker.cancel()
        if hasattr(worker, "requestInterruption"):
            worker.requestInterruption()
        if hasattr(worker, "quit"):
            worker.quit()
        if hasattr(worker, "isRunning") and worker.isRunning() and hasattr(worker, "wait"):
            if not worker.wait(timeout_ms) and hasattr(worker, "terminate"):
                if log_context:
                    logging.warning("Forcing queue worker shutdown during %s.", log_context)
                worker.terminate()
                worker.wait(force_timeout_ms)
    except Exception:
        pass


def collect_runtime_stats(
    *,
    has_current_task: bool,
    pending_count: int,
    history_entries: Iterable[Dict[str, Any]],
) -> Dict[str, int]:
    stats = {
        "running": 1 if has_current_task else 0,
        "pending": int(pending_count),
        "queued": 0,
        "finished": 0,
        "failed": 0,
        "skipped": 0,
        "cancelled": 0,
        "cleared": 0,
        "trace": 0,
    }
    for entry in history_entries:
        event = str(entry.get("event") or "").strip().lower()
        if event in stats:
            stats[event] += 1
    return stats


def build_retry_wait_state(
    delay_seconds: float,
    attempt: int,
    total_attempts: int,
    error_text: str,
) -> Tuple[int, str, str]:
    wait_seconds = max(1, int(round(float(delay_seconds))))
    short_error = str(error_text or "").strip().replace("\n", " ")
    if len(short_error) > 120:
        short_error = short_error[:117] + "..."
    description = f"Retry {attempt + 1}/{total_attempts} in progress"
    status_message = f"Waiting {wait_seconds}s before retry ({attempt + 1}/{total_attempts}). {short_error}"
    return wait_seconds, description, status_message


def cleanup_between_jobs() -> None:
    try:
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    except Exception:
        pass
