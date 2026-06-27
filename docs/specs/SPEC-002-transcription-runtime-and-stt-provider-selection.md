# SPEC-002: Transcription Runtime And STT Provider Selection

Status: Implemented
Owner: TBD
Last updated: 2026-06-27

## Problem

Users need transcription to choose a reliable speech-to-text backend and runtime profile without manual tuning for each recording. The app must prefer CUDA when available and allowed, keep Windows and Ubuntu behavior stable, fall back predictably after native backend failures, and expose local Sherpa-ONNX as a selectable offline option.

## Scope

- In scope: transcription model option normalization, legacy model-name mapping, backend dispatch, device and compute-type selection, subprocess isolation, faster-whisper retry/fallback policy, openai-whisper compatibility fallback, Sherpa-ONNX model selection/preflight, long-recording chunking, progress/status reporting, and runtime cleanup.
- Out of scope: audio capture/import UI, recording metadata persistence, diarization speaker assignment details, transcript editing, cloud transcription services, and database schema redesign.

## User Stories

- As a user, I want the app to pick a good transcription runtime automatically so that recordings transcribe without manual device setup.
- As a user with CUDA available, I want transcription to use GPU unless I explicitly force CPU or the fallback path needs CPU.
- As a user on Windows, I want native backend crashes and timeouts handled without taking down the desktop app.
- As a user, I want Sherpa-ONNX available as a local backend so that transcription can run without Whisper.
- As a user, I want the finished transcript metadata to record the backend, device, compute type, model, duration, and timing so that later diagnostics are possible.

## Acceptance Criteria

- Given saved or UI-provided transcription model names, when they are normalized, then supported UI labels are preserved, legacy names map to current labels, and invalid values fall back to the default model.
- Given Sherpa-ONNX is selected, when a `TranscriberThread` is created, then the worker uses the `sherpa-onnx` backend with CPU and `onnxruntime` compute settings.
- Given no explicit device or compute type is supplied, when CUDA is available and `force_cpu` is false, then device selection prefers CUDA and chooses a compute type based on platform and available VRAM.
- Given `force_cpu` is true, when device selection runs, then CUDA is ignored and CPU compute settings are used.
- Given the platform is Windows, when CPU or CUDA profiles are selected for faster-whisper, then compute types are adjusted to the Windows-safe profiles used by the worker.
- Given faster-whisper runs, when transcription starts, then the heavy backend executes in a spawned subprocess and returns serialized segment dictionaries.
- Given a faster-whisper subprocess crashes or times out on a retryable profile, when fallback profiles remain, then the worker retries with safer device/compute combinations and emits status updates for each attempt.
- Given Windows faster-whisper attempts keep crashing on large models, when smaller model fallbacks are available, then the worker retries in the configured Windows model fallback order.
- Given Windows faster-whisper attempts all fail with a native crash, when openai-whisper fallback succeeds, then the final result records `openai-whisper` as the effective backend.
- Given backend dispatch receives an unsupported backend, when the subprocess entrypoint runs, then it returns an error payload instead of silently succeeding.
- Given transcription emits segments and total duration is known, when progress is computed, then progress is capped at 100 and diarization reserves the final progress range.
- Given transcription completes, when the result is emitted, then it includes text, model name, backend, device, compute type, transcription time, audio duration, audio size, and diarization flag.
- Given transcription exits after success or failure, when CUDA is available, then CUDA cache cleanup is attempted.

## Architecture Notes

- Options: `src/transcription_options.py` owns UI model labels, legacy model normalization, Whisper model-name mapping, Sherpa-ONNX option detection, and Sherpa model-type normalization.
- Worker orchestration: `src/worker_components/transcriber_thread.py` owns the Qt worker lifecycle, backend selection, progress/status signals, diarization handoff, result shaping, settings persistence, cancellation checks, and final cleanup.
- Device policy: `src/worker_components/device_selection.py` owns runtime device and compute-type selection for CUDA/CPU, Ubuntu, Windows, VRAM-sensitive profiles, and `force_cpu`.
- Runtime diagnostics: `src/worker_components/runtime.py` owns transcription runtime logging, optional pyannote import caching, log flushing before subprocess boundaries, and diarization GPU eligibility checks.
- Fallback policy: `src/worker_components/engine.py` owns faster-whisper retry profiles, Windows model fallback ordering, native-crash/timeout classification, and openai-whisper compatibility fallback.
- Subprocess isolation: `src/worker_components/subprocess_runner.py` owns spawned backend process execution, cancellation, timeout handling, crash detection, result-queue validation, and queue/process cleanup.
- Provider dispatch: `src/stt_providers/dispatcher.py` maps backend identifiers to provider adapters and returns structured success/error payloads.
- Provider adapters: `src/stt_providers/faster_whisper.py`, `src/stt_providers/openai_whisper.py`, and `src/stt_providers/sherpa_onnx/` translate common payloads into backend-specific calls and serialize segments.
- Sherpa model management: `src/stt_providers/sherpa_onnx/model_manager.py` owns default model paths, model URL, model-layout detection, preflight checks, and ONNX config resolution.
- Platform constraints: preserve Ubuntu CUDA preference when available and not forced off; preserve Windows-safe compute profiles, subprocess crash isolation, and model/backend fallbacks.

## Test Plan

- Unit: transcription option normalization, Sherpa model-type normalization, device/compute selection, progress calculation, segment merge behavior, runtime helper decisions, fallback profile ordering, and fatal failure classification.
- Provider: backend dispatcher routing/error payloads, faster-whisper payload serialization, openai-whisper model-name compatibility, and Sherpa-ONNX model config/preflight behavior.
- Worker: subprocess runner success/error/timeout/cancel/crash paths, transcriber thread initialization, backend choice, fallback settings persistence, and worker integration paths.
- Integration: recording/transcription flow tests that exercise worker handoff and result persistence without real native backend work.
- Manual: transcribe short and long recordings on Ubuntu and Windows with CUDA enabled, CPU forced, faster-whisper, openai-whisper fallback, and Sherpa-ONNX.

## Documentation

- Feature registry: `docs/specs/README.md`.
- Refactor record: `docs/specs/REFACTOR-2026-05-feature-packages.md`.
- Runtime diagnostics: `log/app.log` records backend, device, compute type, package versions, CUDA state, and environment flags for troubleshooting.

## Refactor Notes

- 2026-06-27: created the dedicated transcription runtime spec for the existing `src/worker_components/` and `src/stt_providers/` split.
- 2026-06-27: recorded `TranscriberThread` as the public Qt orchestration boundary and `src/worker_components/` plus `src/stt_providers/` as the smaller runtime/provider owners.

## Open Questions

- Should `TranscriberThread` shrink further by moving diarization orchestration into a dedicated `src/worker_components/diarization.py` helper once SPEC-003 has its own file?
- Should backend preference and fallback decisions be represented by typed configuration objects before adding more STT providers?
- Should Windows CI include a smoke test for the spawned subprocess path using a fake backend target instead of only unit-level process behavior?
