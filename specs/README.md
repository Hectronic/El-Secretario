# El Secretario: peticiones y specs vivas

- [REQUESTS.md](REQUESTS.md): registro ordenado de lo solicitado, estados y trazabilidad.
- [CURRENT.md](CURRENT.md): mapa de funcionalidad existente, propietarios, pruebas y límites conocidos.
- Cada `spec.md`: contrato vivo del área. `plan.md`: decisiones y evidencia de validación. `tasks.md`: trabajo y pendientes.
- [Plantilla](templates/feature-spec.md): estructura para nuevas specs y actualizaciones.

## Cómo mantenerlo

1. Registrar cada petición antes de implementar, con ID estable, origen conocido y spec propietaria. No inventar el historial ausente.
2. Revisar código y pruebas del área. Mantener el comportamiento existente en la spec; dejar las propuestas sin implementar en una sección marcada y en tareas pendientes.
3. Si cambia el comportamiento, actualizar su spec propietaria y las referencias de otras specs afectadas en la misma PR. No crear una nueva spec por cada corrección de una funcionalidad existente.
4. Separar estado de implementación y validación: registrar comandos, fecha, entorno, resultados y comprobaciones pendientes en el plan. Una casilla marcada no constituye evidencia.
5. Actualizar REQUESTS y CURRENT al entregar. Conservar las peticiones sustituidas o descartadas con el motivo y el enlace sucesor. El historial detallado se consulta en Git.

## Contratos por área

- [001-audio-capture-import](001-audio-capture-import/spec.md)
- [002-transcription-runtime](002-transcription-runtime/spec.md)
- [003-diarization-speakers](003-diarization-speakers/spec.md)
- [004-recording-metadata](004-recording-metadata/spec.md)
- [005-audio-editor](005-audio-editor/spec.md)
- [006-rag-search](006-rag-search/spec.md)
- [007-chat-sessions](007-chat-sessions/spec.md)
- [008-chat-context-sidebar](008-chat-context-sidebar/spec.md)
- [009-calendar-context](009-calendar-context/spec.md)
- [010-collections-notebooks](010-collections-notebooks/spec.md)
- [011-summaries-queue](011-summaries-queue/spec.md)
- [012-tasks-board](012-tasks-board/spec.md)
- [013-settings-runtime](013-settings-runtime/spec.md)
- [014-tools-data-management](014-tools-data-management/spec.md)
- [015-recording-safety-guardian](015-recording-safety-guardian/spec.md)
- [016-runtime-performance-baseline](016-runtime-performance-baseline/spec.md)
- [017-stability-hardening](017-stability-hardening/spec.md)
- [018-lightweight-runtime](018-lightweight-runtime/spec.md)
- [019-knowledge-workflows](019-knowledge-workflows/spec.md)
- [020-system-tray-icon](020-system-tray-icon/spec.md)
- [021-installation-scripts](021-installation-scripts/spec.md)
- [022-os-integration](022-os-integration/spec.md)
- [023-auto-updater](023-auto-updater/spec.md)
- [024-local-api](024-local-api/spec.md)
- [025-mcp-server](025-mcp-server/spec.md)
- [026-custom-titlebar](026-custom-titlebar/spec.md)
- [027-realtime-waveform-visualizer](027-realtime-waveform-visualizer/spec.md)
- [028-drag-drop-audio-importer](028-drag-drop-audio-importer/spec.md)
- [029-sql-repositories-decoupling](029-sql-repositories-decoupling/spec.md)
- [030-media-player-state-pattern](030-media-player-state-pattern/spec.md)
- [031-automatic-audio-compression](031-automatic-audio-compression/spec.md)
- [032-rag-embeddings-cache](032-rag-embeddings-cache/spec.md)
- [033-extreme-resource-cleanup](033-extreme-resource-cleanup/spec.md)
- [034-pomodoro-timeline](034-pomodoro-timeline/spec.md)
- [035-recurring-meetings](035-recurring-meetings/spec.md)
- [036-chat-ux-workflows](036-chat-ux-workflows/spec.md)
- [037-settings-experience](037-settings-experience/spec.md)
- [038-tray-quick-actions](038-tray-quick-actions/spec.md)
- [039-pomodoro-quick-start](039-pomodoro-quick-start/spec.md)

- [040-living-specs](040-living-specs/spec.md)

## Cross-feature invariants

- `016` owns measurements and accepted performance thresholds; later specs must
  reference its baselines rather than inventing unmeasured targets.
- `017` owns lifecycle, failure, cancellation, retry, and cleanup semantics.
- `018` owns packaging, capability detection, lazy imports, and cold-start cost.
- `019` owns indexing freshness, provenance, and resumable knowledge workflows.
- Existing compatibility façades (`DBManager`, `RAGEngine`, legacy widgets) are
  preserved unless a future spec explicitly defines a migration.
- `034` owns focused-work sessions and the user-visible activity timeline.
- `035` owns recurring-meeting definitions, occurrence scheduling, and reminder
  dispatch; it may create timeline events defined by `034`.
- `036` owns chat interaction and presentation workflows; it consumes context and
  provenance from `007`, `008`, and `019` without redefining their data policies.
- `037` owns settings navigation, presentation, validation, and discoverability;
  setting values and runtime semantics remain with their feature owners.
- `038` owns tray menu actions and state presentation; capture, Pomodoro, and
  meeting operations are delegated to their existing or proposed feature owners.
- `039` owns the simplified Pomodoro interaction and first-class discovery in
  the single general activity timeline, search, and chat context. Timer
  lifecycle and source persistence remain owned by `034`; no Pomodoro-only
  timeline is introduced.
