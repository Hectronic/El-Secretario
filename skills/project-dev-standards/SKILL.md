---
name: project-dev-standards
description: Enforce local repository development standards whenever code is created, edited, refactored, moved, or deleted in src/, tests/, scripts/, or docs/. Use this for all implementation tasks so new files include the GPL header, code includes concise non-trivial comments where needed, and unit tests mirror source folder structure (e.g., src/foo/bar.py -> tests/foo/test_bar.py).
---

# Project Dev Standards

## Apply On Every Code Change

1. Add the project GPL header block at the top of every new Python source or test file.
2. Keep comments concise and useful:
- explain intent or non-obvious behavior
- avoid redundant comments
3. Preserve compatibility-first refactors:
- keep import surface stable unless explicitly requested
- prefer wrappers/shims during incremental migrations
4. Preserve runtime configuration:
- respect configured STT backend, device, compute type, and `force_cpu`
- prefer GPU/CUDA when available and `force_cpu` is false
- do not introduce unconditional CPU forcing except for existing safe fallback paths after real runtime failures
- keep transcription and diarization aligned with the same runtime policy where supported

## Test Layout Rule

1. Mirror `src/` structure in `tests/` for new unit tests.
2. Prefer:
- `src/worker_components/transcription_flow.py`
- `tests/worker_components/test_transcription_flow.py`
3. Avoid dumping new unit tests into generic files when a feature/module-specific path exists.

## Validation Rule

1. Run targeted tests for touched modules first.
2. Run full suite when refactors touch shared runtime or threading/transcription paths.
3. Report exact commands executed and pass/fail counts.
