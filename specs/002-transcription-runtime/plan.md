# Implementation Plan: Transcription Runtime and STT Providers

**Branch**: `002-transcription-runtime` | **Status**: Implemented

`src/worker_components/` and `src/stt_providers/` own dispatch, configured backend/device/compute policy, subprocess isolation, fallbacks, and resource cleanup.
