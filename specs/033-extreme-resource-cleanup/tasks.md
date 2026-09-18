# Tasks: Extreme Resource Cleanup

Status: Draft
Last updated: 2026-09-17

- [ ] T001 Design the centralized proactive memory flushing routine inside a helper utility module.
- [ ] T002 Inject memory cleanup hooks inside `TranscriberThread` and PyAnnote execution paths.
- [ ] T003 Inject memory flushing inside MCP and REST API background workers upon task completion.
- [ ] T004 Implement safe PyTorch CUDA empty cache checks to prevent exceptions on CPU-only platforms.
- [ ] T005 Write unit tests and benchmarks verifying that idle RAM/VRAM drops significantly within 5 seconds after task completion.
