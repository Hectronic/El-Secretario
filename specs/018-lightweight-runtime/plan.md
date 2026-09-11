# Implementation Plan: Lightweight Installation And Lazy Runtime

**Branch**: `018-lightweight-runtime` | **Status**: Planned

## Summary

Measure import and startup costs, define supported dependency profiles, then
defer optional provider imports and RAG/model initialization behind stable
capability boundaries.

## Phases

1. Inventory dependency ownership and cold-start imports.
2. Define profiles and capability diagnostics without changing defaults.
3. Introduce lazy provider and RAG initialization.
4. Verify core startup, optional first use, packaging, and full-profile parity.

## Migration Strategy

1. Add capability detection without changing imports.
2. Add tests that prove current full-profile behavior.
3. Move one provider family at a time behind its factory/entry point.
4. Split dependency manifests while retaining a compatibility full install.
5. Defer RAG embedding creation only after persistence and search contract tests
   prove equivalent results.

Do not begin by deleting packages from `requirements.txt`; first provide an
installable equivalent and update all platform instructions together.

## Constitution Check

No provider is removed and no runtime preference is overridden. Missing optional
dependencies fail explicitly and cross-platform install paths remain documented.
