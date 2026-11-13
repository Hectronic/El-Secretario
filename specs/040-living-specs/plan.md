# Plan: registro y specs vivas

Status: Implemented

- Migrar los 39 contratos existentes sin borrar sus requisitos ni notas históricas.
- Añadir referencias verificadas de código y cobertura, separando objetivos y limitaciones.
- Corregir el índice completo y los estados obsoletos; registrar las peticiones de esta sesión.
- Mantener la política en AGENTS.md, constitución y plantilla; enlazar desde los tres README.

## Validación

Validado el 2026-10-22 en Linux:

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_spec_registry.py -q
```

Resultado: 3 passed. Comprueba inventario de 40 directorios, artefactos, IDs de petición únicos, enlaces locales de specs/catálogo y enlaces de los tres README. La comprobación queda en la suite para detectar divergencias futuras. Sin cambios de runtime propios de 040; la entrega conjunta usa las pruebas de 039.

Entrega conjunta en la rama `039-pomodoro-quick-start`: [PR #67](https://github.com/Hectronic/El-Secretario/pull/67). Suite completa de la entrega: 1031 passed, 1 skipped, 11 subtests passed (véase el plan de 039 para el comando y contratos).

## Windows decoding follow-up (2026-10-22, REQ-040.5)

Run 39813238392 exposed `Path.read_text()` using cp1252 for UTF-8 Markdown. All registry reads now specify `encoding="utf-8"`. Reproduced before the fix with the project interpreter under `-X utf8=0`, `LC_ALL=C`, and locale coercion disabled; the existing checks failed decoding non-ASCII documentation. The permanent subprocess regression uses `sys.executable`, so it retains the project interpreter, and re-runs all three document checks without enabling UTF-8 globally or relaxing any assertions.

Focused validation: 30 passed with `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_spec_registry.py tests/ui/settings -q`. The document checks remain local-file tests; no new application component boundary is introduced. Final Linux/offscreen validation: 1039 passed, 1 skipped, 11 subtests passed in 135.08 seconds; see the 037 follow-up plan for command and UI boundary coverage, and [PR #67 checks](https://github.com/Hectronic/El-Secretario/pull/67/checks) for native runs.

## Auditoría local de estado (2026-11-12, REQ-040.6)

Entorno: Linux, virtualenv del proyecto `.venv`, Qt `offscreen`; rama `main`, HEAD `f5fe68d` (merge de PR #67, 2026-10-23). Revisión local de artefactos, referencias, planes, tareas y preguntas abiertas; no se ha consultado CI remota. No se modifica código de aplicación ni se cruza una frontera de componentes; se ejercitan contratos de integración existentes.

Hallazgos:

- 40 specs con `spec.md`, `plan.md` y `tasks.md`; 268 tareas cerradas y ninguna abierta antes de esta auditoría. El registro marca implementadas las 40 áreas.
- Los pendientes descritos en 038/039 no estaban reflejados como tareas abiertas: comprobaciones visuales nativas y perfilado de cronología con historiales grandes. Se añaden como seguimiento, sin declarar funcionalidad sin implementar.
- 16 cabeceras mantienen `Owner: TBD`, aunque existen referencias de propietario al final. Planes como 001, 002 y 034 no aportan comandos/resultados/entorno concretos. Se registra normalización futura en las tareas de 040.
- Las preguntas abiertas de specs antiguas son propuestas sin decisión; no prueban fallos. Revisarlas antes de convertirlas en compromisos de producto.
- El árbol inicial tenía `ignored-by-fallback/embeddings_cache.sqlite` sin seguimiento. No se elimina ni se incluye en la entrega documental.

Validación focalizada (33 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_spec_registry.py tests/ui/settings -q
```

Integración focalizada (29 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/integration/test_settings_experience.py tests/integration/test_pomodoro_main_window.py tests/integration/test_pomodoro_timeline_flow.py tests/integration/test_tray_quick_actions.py tests/integration/test_recording_compression_lifecycle.py -q
```

Estos tests existentes ejercitan Qt y persistencia reales: guardado de ajustes, inicio y navegación Pomodoro, cronología/contexto, acciones de bandeja y ciclo de compresión. Las aristas externas se sustituyen de forma determinista. No se añaden tests porque solo cambia documentación.

Suite completa:

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q
```

Resultado: 1043 passed, 1 skipped, 11 subtests passed en 157.22 segundos. El único skip corresponde a `tests/ui/test_system_tray_integration.py:10`, por ausencia de bandeja del sistema. Tras actualizar los documentos, se repitió `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_spec_registry.py -q`: 4 passed. `git diff --check` también pasa.

Límites: esta revisión no certifica apariencia/foco nativos, instalaciones limpias en tres sistemas, audio físico, proveedores reales ni CUDA/VRAM. Los rendimientos históricos dependen del host y no son garantías universales. No se mueven ni se reestructuran archivos de código.
