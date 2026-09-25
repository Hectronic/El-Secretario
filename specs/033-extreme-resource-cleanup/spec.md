# SPEC-033: Extreme Resource Cleanup

Status: Implemented
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-24

## Problem
When El Secretario executes local deep learning tasks (such as Faster-Whisper transcription, PyAnnote diarization, or semantic vector generation), the underlying PyTorch / CUDA backends allocate massive amounts of system RAM and graphics card memory (VRAM). After the transcription or diarization job is finished, PyTorch by default retains this allocated memory block inside its internal memory cache pool to speed up future hypothetical calls. This leaves El Secretario consuming up to several gigabytes of RAM/VRAM even when idling in the system tray, degrading general system responsiveness and starving other applications.

## Proposal
Implement an aggressive, proactive background resource garbage collection system. Immediately after any local AI, STT, diarization, or RAG inference task completes, the application will forcefully flush and release all cached RAM, CUDA VRAM, and garbage collector pools, reducing its idle memory footprint to less than **150 MB**!

### Key Highlights
- **Active CUDA VRAM Flushing:** Execute explicit CUDA cache emptying (`torch.cuda.empty_cache()` and `torch.cuda.ipc_collect()`) in the transcriber and diarization worker threads.
- **Proactive Garbage Collection:** Trigger explicit Python garbage collections (`gc.collect()`) to free up any unreferenced deep-learning variables instantly.
- **Worker Resource Release:** Ensure any subprocess runners or thread pools spawned by backends are fully terminated and joined upon task completion.

## User Scenarios & Testing
- **Scenario:** The user transcribes a 1-hour recording. Their graphics card VRAM spikes to 1.8 GB during execution. As soon as the transcription completes and saves, the background thread flushes CUDA caches. The VRAM drops instantly back to 0 MB, and El Secretario's idle system RAM shrinks to 120 MB.
- **Testing:** Unit and integration tests verify terminal GC/CUDA cleanup hooks. The runtime benchmark records post-cleanup RSS and whether the 150 MB/5 second idle target is met on the host; VRAM allocator calls are verified with deterministic CUDA doubles.
