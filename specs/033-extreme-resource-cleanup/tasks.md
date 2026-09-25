# Tasks: Extreme Resource Cleanup

Status: Implemented
Last updated: 2026-09-24

- [x] T001 Design the centralized proactive memory flushing routine inside a helper utility module.
- [x] T002 Inject memory cleanup hooks inside `TranscriberThread` and PyAnnote execution paths.
- [x] T003 Inject memory flushing inside MCP and REST API background workers upon task completion.
- [x] T004 Implement safe PyTorch CUDA empty cache checks to prevent exceptions on CPU-only platforms.
- [x] T005 Write unit/integration tests and a host benchmark for the 150 MB / 5 second idle target. CUDA calls are deterministically verified; host RSS is reported because VRAM is hardware-specific.
