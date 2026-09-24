"""Safe, centralized cleanup for local inference workloads.

Inference providers may retain Python objects and CUDA allocator blocks after a
request completes.  This helper deliberately never changes device selection;
it only releases resources that are no longer reachable after a terminal job.
"""

from __future__ import annotations

import gc
import logging
import sys
from typing import Any


logger = logging.getLogger(__name__)


def _load_torch() -> Any | None:
    """Return an already-loaded torch module without loading it just to clean up.

    A cleanup request must not initialize PyTorch's native runtime on an API or
    MCP-only process.  Inference paths have already imported it by the time a
    terminal hook runs, so ``sys.modules`` preserves cleanup coverage.
    """
    return sys.modules.get("torch")


def release_local_inference_resources() -> int:
    """Collect Python garbage and release safe CUDA allocator caches.

    CUDA calls are intentionally best-effort: driver teardown and CPU-only
    installations must never turn a completed transcription into an error.
    The returned count makes the routine observable in tests and diagnostics.
    """
    collected = gc.collect()
    torch = _load_torch()
    if torch is None:
        return collected

    try:
        if not torch.cuda.is_available():
            return collected
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    except Exception as error:
        logger.debug("CUDA cache cleanup was unavailable: %s", error)
    return collected
