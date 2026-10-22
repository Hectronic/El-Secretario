# Registro ordenado de peticiones

Este archivo registra lo solicitado y su resolución. El orden histórico recuperado es el número de spec, no una prioridad ni una fecha de conversación inferida. Las entradas 001–039 se reconstruyen de los artefactos versionados: no son citas literales de conversaciones antiguas. Los requisitos detallados conservan sus identificadores en la spec enlazada.

Las peticiones nuevas se añaden al final con ID estable, origen, estado y spec propietaria. Una petición modificada o descartada se conserva indicando su sustitución y motivo. Estados: pendiente, en curso, implementada, descartada o sustituida. La validación se registra aparte, en plan.md, con comandos y límites.

| ID | Petición recuperada | Estado de implementación | Contrato / origen |
| --- | --- | --- | --- |
| REQ-001 | Captura e importación de audio | Implementada | [001-audio-capture-import/spec.md](001-audio-capture-import/spec.md) |
| REQ-002 | Transcripción y selección de STT | Implementada | [002-transcription-runtime/spec.md](002-transcription-runtime/spec.md) |
| REQ-003 | Diarización y hablantes | Implementada | [003-diarization-speakers/spec.md](003-diarization-speakers/spec.md) |
| REQ-004 | Metadatos de grabaciones | Implementada | [004-recording-metadata/spec.md](004-recording-metadata/spec.md) |
| REQ-005 | Editor de audio | Implementada | [005-audio-editor/spec.md](005-audio-editor/spec.md) |
| REQ-006 | Búsqueda RAG | Implementada | [006-rag-search/spec.md](006-rag-search/spec.md) |
| REQ-007 | Sesiones de chat | Implementada | [007-chat-sessions/spec.md](007-chat-sessions/spec.md) |
| REQ-008 | Panel de contexto | Implementada | [008-chat-context-sidebar/spec.md](008-chat-context-sidebar/spec.md) |
| REQ-009 | Calendario y fechas | Implementada | [009-calendar-context/spec.md](009-calendar-context/spec.md) |
| REQ-010 | Colecciones y cuadernos | Implementada | [010-collections-notebooks/spec.md](010-collections-notebooks/spec.md) |
| REQ-011 | Resúmenes y cola | Implementada | [011-summaries-queue/spec.md](011-summaries-queue/spec.md) |
| REQ-012 | Tablero de tareas | Implementada | [012-tasks-board/spec.md](012-tasks-board/spec.md) |
| REQ-013 | Configuración de ejecución | Implementada | [013-settings-runtime/spec.md](013-settings-runtime/spec.md) |
| REQ-014 | Exportación, mantenimiento y herramientas | Implementada | [014-tools-data-management/spec.md](014-tools-data-management/spec.md) |
| REQ-015 | Protección de grabación | Implementada | [015-recording-safety-guardian/spec.md](015-recording-safety-guardian/spec.md) |
| REQ-016 | Mediciones de rendimiento | Implementada | [016-runtime-performance-baseline/spec.md](016-runtime-performance-baseline/spec.md) |
| REQ-017 | Estabilidad y limpieza de ciclos | Implementada | [017-stability-hardening/spec.md](017-stability-hardening/spec.md) |
| REQ-018 | Ejecución ligera | Implementada | [018-lightweight-runtime/spec.md](018-lightweight-runtime/spec.md) |
| REQ-019 | Flujos de conocimiento | Implementada | [019-knowledge-workflows/spec.md](019-knowledge-workflows/spec.md) |
| REQ-020 | Icono de bandeja | Implementada | [020-system-tray-icon/spec.md](020-system-tray-icon/spec.md) |
| REQ-021 | Instalación multiplataforma | Implementada | [021-installation-scripts/spec.md](021-installation-scripts/spec.md) |
| REQ-022 | Integración del sistema operativo | Implementada | [022-os-integration/spec.md](022-os-integration/spec.md) |
| REQ-023 | Actualización automática | Implementada | [023-auto-updater/spec.md](023-auto-updater/spec.md) |
| REQ-024 | API local | Implementada | [024-local-api/spec.md](024-local-api/spec.md) |
| REQ-025 | Servidor MCP | Implementada | [025-mcp-server/spec.md](025-mcp-server/spec.md) |
| REQ-026 | Barra de título | Implementada | [026-custom-titlebar/spec.md](026-custom-titlebar/spec.md) |
| REQ-027 | Forma de onda en directo | Implementada | [027-realtime-waveform-visualizer/spec.md](027-realtime-waveform-visualizer/spec.md) |
| REQ-028 | Importación por arrastre | Implementada | [028-drag-drop-audio-importer/spec.md](028-drag-drop-audio-importer/spec.md) |
| REQ-029 | Repositorios SQL | Implementada | [029-sql-repositories-decoupling/spec.md](029-sql-repositories-decoupling/spec.md) |
| REQ-030 | Estado del reproductor | Implementada | [030-media-player-state-pattern/spec.md](030-media-player-state-pattern/spec.md) |
| REQ-031 | Compresión de audio | Implementada | [031-automatic-audio-compression/spec.md](031-automatic-audio-compression/spec.md) |
| REQ-032 | Caché de embeddings | Implementada | [032-rag-embeddings-cache/spec.md](032-rag-embeddings-cache/spec.md) |
| REQ-033 | Liberación de recursos | Implementada | [033-extreme-resource-cleanup/spec.md](033-extreme-resource-cleanup/spec.md) |
| REQ-034 | Pomodoro y cronología | Implementada | [034-pomodoro-timeline/spec.md](034-pomodoro-timeline/spec.md) |
| REQ-035 | Reuniones recurrentes | Implementada | [035-recurring-meetings/spec.md](035-recurring-meetings/spec.md) |
| REQ-036 | Experiencia de chat | Implementada | [036-chat-ux-workflows/spec.md](036-chat-ux-workflows/spec.md) |
| REQ-037 | Experiencia de ajustes | Implementada | [037-settings-experience/spec.md](037-settings-experience/spec.md) |
| REQ-038 | Acciones de bandeja | Implementada | [038-tray-quick-actions/spec.md](038-tray-quick-actions/spec.md) |
| REQ-039 | Pomodoro rápido y descubrimiento | Implementada | [039-pomodoro-quick-start/spec.md](039-pomodoro-quick-start/spec.md) |
| REQ-040 | Registro de peticiones y specs vivas | Implementada | [040-living-specs/spec.md](040-living-specs/spec.md) |

## Desglose de la petición 039

Origen: requisitos FR-001–FR-014 y criterios de aceptación de SPEC-039. Todos forman parte de REQ-039; el estado final se contrasta con el plan y las pruebas de esa spec.

| ID | Cosa solicitada | Contrato |
| --- | --- | --- |
| REQ-039.1 | Botón visible y accesible para iniciar foco con duración guardada y título localizado. | FR-001–003 |
| REQ-039.2 | Abrir el foco o descanso activo, también pausado, sin crear otro temporizador. | FR-004–005 |
| REQ-039.3 | Persistencia, errores visibles, recuperación y continuidad al cerrar la pestaña. | FR-006–008 |
| REQ-039.4 | Una cronología general ordenada y filtrable con reuniones, Pomodoros, notas y resúmenes. | FR-009–010, FR-014 |
| REQ-039.5 | Búsqueda por contenido y navegación al propietario existente. | FR-011 |
| REQ-039.6 | Selección explícita de Pomodoros y notas para chat, sin alterar sus filtros ni enviar mensajes automáticamente. | FR-012 |
| REQ-039.7 | Temporizador y controles esenciales prioritarios; opciones secundarias realmente plegables. | FR-013 |

## Peticiones de esta revisión (2026-10-22)

| ID | Petición | Estado | Origen / entrega |
| --- | --- | --- | --- |
| REQ-039.8 | Revisar si 039 está completa y corregir los huecos encontrados. | Implementada | Usuario en esta sesión; plan de 039. |
| REQ-040.1 | Un archivo con cada petición, ordenada y vinculada a su estado. | Implementada | Usuario en esta sesión; este archivo. |
| REQ-040.2 | Specs vivas que describan la funcionalidad realmente existente. | Implementada | Usuario en esta sesión; CURRENT.md y las referencias de implementación de cada spec. |
| REQ-040.3 | Mantener registro, contratos, evidencia y tareas sincronizados en futuros cambios. | Implementada | AGENTS.md, constitución y plantilla de specs. |
| REQ-040.4 | Crear rama, subirla y abrir PR con la revisión y estos ajustes. | Implementada | Usuario en esta sesión; rama `039-pomodoro-quick-start`, [PR #67](https://github.com/Hectronic/El-Secretario/pull/67). |

## Seguimiento de PR #67

| ID | Petición | Estado | Origen / entrega |
| --- | --- | --- | --- |
| REQ-031.1 | Corregir el fallo de la pipeline Windows de la PR #67 al liberar el WAV tras comprimir. | Implementada | Usuario en esta sesión; fallo de CI 39798480934; SPEC-031. |
| REQ-037.1 | Mejorar en la misma PR la apariencia de ajustes mostrada en la captura. | Implementada | Usuario en esta sesión y captura; SPEC-037. |
| REQ-037.2 | Corregir los recortes de ajustes con fuentes y métricas de Windows. | Implementada | Usuario en esta sesión; fallos del run 39813238392; SPEC-037. |
| REQ-040.5 | Corregir la lectura de documentación UTF-8 en la CI Windows con locale cp1252. | Implementada | Usuario en esta sesión; fallos del run 39813238392; SPEC-040. |
