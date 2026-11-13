# Plan: diagnóstico y resultado de diarización

Status: Implemented — validación manual pendiente

## Orden propuesto

1. Caracterizar transcripción directa, cola y lotes, persistencia y sobrescritura/reintento; reproducir el estado `is_diarized` incorrecto. Diseñar estados/códigos sin exponer credenciales.
2. Implementar diagnóstico local y remoto explícito, limitado en tiempo y asíncrono, comprobando los recursos realmente usados por el modelo. Contemplar respuestas ambiguas, caché y obsolescencia tras cambio de token.
3. Propagar resultado real y advertencia persistente por los flujos directos y de cola, proteger los datos previos en reintentos y conservar continuación/limpieza. Mantener la política CUDA/CPU de SPEC-002 y SPEC-003.
4. Integrar acción, estado y soluciones en Ajustes y resultado/tarea, incluyendo navegación, accesibilidad, localización y documentación multilingüe aplicable.
5. Actualizar los contratos propietarios, registro y catálogo. Ejecutar pruebas focalizadas e integración antes de la suite completa.

## Fronteras y validación prevista

Cruza interfaz/señales Qt, worker, red, cola y persistencia; exige pruebas de integración con Qt offscreen y SQLite temporal reales, sustituyendo únicamente las aristas externas. Cubrir token ausente/rechazado, acceso ambiguo y aceptado, recursos secundarios, red y timeout, dependencia incompatible, cambios concurrentes de token, cancelación, GPU/fallback, conservación de texto, estado persistido, advertencia observable y continuación de la cola. Pruebas unitarias cubrirán clasificación prudente y saneamiento de secretos. Verificar rutas directas, cola y lotes; usar flujos existentes cuando tengan cobertura equivalente y registrar el contrato probado.

La validación manual prevista en la instalación afectada incluye comprobar el token y permisos con consentimiento del usuario, red disponible/no disponible, y una muestra real con varios hablantes; probar CPU y CUDA en equipos adecuados. Ninguna comprobación local por sí sola identifica la causa en la instalación del usuario.

## Evidencia de esta propuesta

2026-11-12: inspección estática del worker, ajustes, cola, tests y documentación. El registro local disponible no contiene coincidencias de las cadenas de error o éxito de diarización buscadas; no permite determinar la causa del problema del usuario. Sin cambios de código de aplicación ni pruebas de implementación. La comprobación de integridad del catálogo de specs se registrará tras crear los artefactos.

Validación documental en Linux: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_spec_registry.py -q` — 4 passed; `git diff --check` — sin errores. No se han ejecutado pruebas de una implementación nueva porque todavía no existe.

## Implementación y validación de 2026-11-12

Rama `041-diarization-diagnostics`, Linux, `.venv`, Qt `offscreen`. Se introdujo `src/worker_components/diarization_diagnostics.py` como propietario de la comprobación y `src/ui/settings/diarization_check.py` para la interacción asíncrona; los propietarios existentes de resultados, Qt, cola y SQLite se han ampliado sin mover archivos. La migración añade `records.diarization_warning`, sin modificar registros históricos. La comprobación valida acceso a cuenta, configuración del modelo y ficheros de sus dependencias declaradas; no carga pesos ni prueba inferencia. El estado incierto y el alcance se muestran expresamente.

La comprobación tiene un límite de interfaz de 45 s y cada petición de red usa un timeout de 10 s. Cancelar o cerrar invalida el resultado y evita peticiones posteriores; una petición que ya se esté realizando termina en segundo plano antes de liberar su sesión. No se garantiza interrumpir inmediatamente una importación nativa o una resolución DNS bloqueada. Las credenciales no se incluyen en los resultados y se sanea el detalle de errores.

Pruebas focalizadas (138 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/worker/test_worker_unit.py tests/worker/test_worker_integration.py tests/worker_components/test_runtime.py tests/worker_components/test_diarization_diagnostics.py tests/app/summary_queue tests/ui/settings tests/ui/test_diarization_text.py -q
```

Pruebas de integración (15 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/integration/test_diarization_diagnostics.py tests/integration/test_settings_experience.py tests/integration/test_recording_widget_persistence.py tests/test_summary_task_queue_integration.py -q
```

El contrato de `tests/integration/test_diarization_diagnostics.py` usa señales Qt, SQLite y workers reales con aristas de STT/red deterministas: resultado sin token, persistencia y reapertura del aviso, conservación del texto anterior, continuación de la cola, navegación y cancelación de una comprobación. No sustituye la prueba con la cuenta e instalación del usuario.

Suite completa (1057 passed, 1 skipped por ausencia de bandeja del sistema, 11 subtests passed, 127.49 s):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q
```

Pendiente validación manual con cuenta real y condiciones de acceso, audio con varios hablantes, GPU y CPU, y apariencia nativa en los sistemas admitidos. El entorno actual no permite identificar la causa de la instalación del usuario.

La estructura del fixture de configuración se contrastó con el [config.yaml oficial de pyannote 3.1](https://github.com/pyannote/hf-speaker-diarization-3.1/blob/main/config.yaml): los identificadores de segmentación y embeddings están en `pipeline.params`. La denegación del modelo de segmentación tiene una regresión específica.

La interfaz de esta función selecciona textos en español, asturiano o inglés según `QLocale.system()`. Los mensajes persistidos no incluyen credenciales y se traducen al mostrarse en la grabación y el historial.

Una ejecución anterior fue interrumpida por el agente mientras una prueba Qt de audio escribía un archivo; pytest registró un `KeyboardInterrupt` en esa prueba. La suite final anterior se ejecutó sin interrupciones y pasó.

## Entrega de 2026-11-13

La rama `041-diarization-diagnostics` se publicó para revisión en [PR #68](https://github.com/Hectronic/El-Secretario/pull/68), a petición del usuario (REQ-041.2). Las comprobaciones locales y las validaciones manuales pendientes están registradas arriba; la CI de la PR tiene su propio estado en GitHub.
