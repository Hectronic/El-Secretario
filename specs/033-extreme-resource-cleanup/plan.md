# Implementation Plan: Extreme Resource Cleanup

Status: Implemented
Last updated: 2026-09-24
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Thread-Exit Hook Injection
- Inject custom cleanup hooks inside all worker components and threads:
  - `TranscriberThread` inside `src/audio.py` or worker threads.
  - `src/api/mcp_server.py` and `mcp` background runners.
  - `src/api/server.py` REST API worker tasks.

### Phase 2: Core Memory Flushing
- Within the cleanup hooks, execute the following sequentially:
  - Safe import of `torch` and check `torch.cuda.is_available()`.
  - Call `torch.cuda.empty_cache()` and `torch.cuda.ipc_collect()` inside a safe `try-except` block to prevent errors on CPU-only machines.
  - Call `gc.collect()` to force immediate RAM collection.

### Phase 3: Benchmark and Verification
- Update the benchmark suite (`benchmarks/runtime_baseline.py`) to measure idle memory usage after execution, asserting it falls below 150 MB within 5 seconds of idle.

## Delivered

- `src/resource_cleanup.py` owns best-effort GC, CUDA allocator eviction, and CUDA IPC collection without altering backend/device policy.
- STT subprocesses, the transcriber terminal path, summary queue, RAG operations/subprocesses, local API shutdown, and MCP request completion call the routine.
- Benchmarks report the host RSS result against the 150 MB / 5 second target; it is not a portable VRAM measurement.
