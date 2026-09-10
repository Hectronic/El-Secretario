# Guía de arquitectura de El Secretario

Esta guía explica la arquitectura actual y cómo extenderla. Los contratos de
producto viven en `specs/<NNN-feature>/`.

## Vista general

El Secretario es una aplicación PyQt local-first: la interfaz presenta y
coordina, SQLite conserva estado y adaptadores aislados conectan STT, IA y RAG.

```text
main.py → MainWindow → src/ui/<feature>/ → servicios y runtimes
                         │                    │
                         └─ señales Qt         ├─ AI / STT / RAG
                                                └─ DBManager → SQLite
```

## Responsabilidades

| Capa | Owner | Responsabilidad |
| --- | --- | --- |
| Arranque | `main.py`, `src/ui/main_window/` | QApplication, composición, pestañas, navegación y apagado. |
| UI de feature | `src/ui/<feature>/` | Presentación, interacción y señales Qt. |
| Servicios | `src/app/`, runtimes de feature | Flujos no visuales y ciclo de workers. |
| Persistencia | `src/persistence/` | SQL, esquema/migraciones y traducción de datos por agregado. |
| Integraciones | `src/rag/`, `src/ai_providers/`, `src/stt_providers/` | Bordes externos y política específica de runtime. |

`src/database.py`, `src/rag_engine.py`, `src/ai_provider.py` y los widgets
históricos mantienen fachadas compatibles. No se añade comportamiento nuevo a
una fachada si existe un paquete propietario más pequeño.

## Paquetes principales

- `src/ui/main_window/`: coordinadores de layout, tabs, sidebar, chat flotante,
  inicio de runtime y ciclo de vida de ventana.
- `src/ui/recording/`, `recording_in_progress/` y `audio_editor/`: detalle,
  captura y edición segura con preview/retranscripción.
- `src/ui/chat/` y `context_manager/`: contexto, sesiones, rendering, runtime y
  sincronización de chat.
- `src/app/summaries/` y `src/app/summary_queue/`: generación y colas no Qt;
  `src/ui/summary_queue/` adapta señales y ciclo de vida a la interfaz.
- `src/persistence/`: repositorios de registros, chats, resúmenes, tareas y logs.
- `src/worker_components/`: transcripción, selección de dispositivo, aislamiento
  en subproceso y fallback; `src/stt_providers/` implementa backends.

## Flujos de datos

```text
captura/importación → worker STT → SQLite → RAG → búsqueda/chat/resúmenes
edición de audio → backup .orig + SQLite → retranscripción → señales UI
contexto de chat → RAG/context builder → proveedor AI → sesión SQLite
```

La configuración decide backend, dispositivo, compute type y `force_cpu`. Las
rutas GPU no se degradan a CPU salvo configuración o fallback seguro; workers y
memoria CUDA se liberan al terminar.

## Límites de prueba

- Las pruebas unitarias reflejan el paquete de código en `tests/`.
- Los límites UI/señales, SQLite, workers/colas, STT, AI, RAG y plataforma tienen
  integración real cuando se cruzan: SQLite temporal y Qt `offscreen`.
- Solo redes, AI, STT, RAG y hardware de audio se sustituyen por dobles
  deterministas. Se ejecuta `./venv/bin/python -m pytest` y, para cambios
  compartidos, la suite completa.

## Regla para cambios futuros

1. Lee `spec.md`, `plan.md` y `tasks.md` del feature afectado.
2. Sitúa el cambio en el owner más pequeño e inyecta bordes externos.
3. Añade pruebas unitarias e integración si cruza componentes.
4. Actualiza los tres artefactos Spec Kit tras validar.

Las nuevas capacidades se documentarán en un directorio Spec Kit numerado cuando
su contrato de usuario sea distinto; esta guía no crea ni propone aún esos specs.
