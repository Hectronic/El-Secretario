# `worker.py` Documentation

## Objetivo

[`src/worker.py`](/home/developer/repos/hector/El-Secretario/src/worker.py) concentra la ejecución asíncrona de tareas pesadas para no bloquear la UI (PyQt):

- Transcripción de audio (faster-whisper, sherpa-onnx, fallback openai-whisper).
- Búsqueda RAG en segundo plano.
- Chat con proveedor AI en segundo plano.

La idea principal es: **la UI dispara hilos (`QThread`) y recibe señales** (`finished`, `progress`, `status_update`, `error`).

## Componentes principales

## `TranscriberThread`

Clase principal de transcripción.

- Entrada: `audio_path`, modelo, `device`, `compute_type`, idioma, diarización, etc.
- Salida (`finished.emit`): `dict` con texto, backend efectivo, dispositivo, compute type, tiempo, tamaño de audio, etc.
- Señales:
  - `progress(int)`
  - `status_update(str)`
  - `error(str)`
  - `finished(dict)`

Qué hace en `run()`:

1. Carga ajustes (`QSettings`) y contexto de runtime.
2. Elige backend:
   - `sherpa-onnx` si el modelo UI es sherpa.
   - `openai-whisper` si se fuerza preferencia.
   - `faster-whisper` por defecto.
3. Ejecuta transcripción en subprocess (aislamiento de fallos nativos).
4. Aplica reintentos y perfiles fallback (especialmente en Windows).
5. Opcional: diarización con pyannote.
6. Fusiona segmentos + speaker labels.
7. Persiste ajustes funcionales en `QSettings`.
8. Limpia memoria (`gc`, `torch.cuda.empty_cache()`).

## `SearchThread`

Wrapper simple para ejecutar `rag.search(query)` en segundo plano.

- `finished.emit(list)` con resultados.
- `error.emit(str)` si falla.

## `ChatThread`

Ejecuta chat AI en segundo plano usando configuración desde `QSettings` vía `get_ai_provider`.

- `finished.emit(str)` con respuesta.
- `error.emit(str)` si falla.

## Helpers/Utilidades clave

- Backend subprocess:
  - `_run_backend_subprocess`
  - `_run_transcription_in_subprocess`
  - `_run_openai_whisper_fallback`
  - `_run_sherpa_onnx_transcription`

- Sherpa-ONNX:
  - `_ensure_sherpa_onnx_model_ready`
  - `_resolve_sherpa_onnx_model_config`
  - `_download_sherpa_onnx_model`
  - `_safe_extract_tarball`
  - `get_transcription_preflight_error`

- Selección runtime / resiliencia:
  - `get_optimal_device`
  - `_subprocess_fallback_profiles`
  - `_windows_model_fallback_order`
  - `_is_subprocess_native_crash`
  - `_is_subprocess_timeout`

- Logging / contexto:
  - `_log_transcription_runtime_context`
  - `_pkg_version`
  - `_flush_log_handlers`

## Dónde se usa en la app

Referencias directas de producción:

- `TranscriberThread`:
  - [recording_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/recording_widget.py)
  - [notebook_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/notebook_widget.py)
  - [summary_task_queue.py](/home/developer/repos/hector/El-Secretario/src/ui/summary_task_queue.py)
  - [batch_process_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/batch_process_widget.py)
  - [audio_editor_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/audio_editor_widget.py)

- `SearchThread`:
  - [main_window.py](/home/developer/repos/hector/El-Secretario/src/ui/main_window.py)

- `ChatThread`:
  - [chat_window.py](/home/developer/repos/hector/El-Secretario/src/ui/chat_window.py)
  - [chat_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/chat_widget.py)

- Preflight sherpa:
  - [recording_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/recording_widget.py)
  - [notebook_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/notebook_widget.py)
  - [audio_editor_widget.py](/home/developer/repos/hector/El-Secretario/src/ui/audio_editor_widget.py)

## Por qué es crítico para refactor

`worker.py` mezcla varias responsabilidades:

- Orquestación de hilos Qt.
- Políticas de fallback por plataforma.
- Gestión de modelos sherpa.
- Infra de subprocess y manejo de errores.
- Lógica de diarización.

Por eso es buen candidato para separar en módulos (por ejemplo `worker_transcription.py`, `worker_sherpa.py`, `worker_subprocess.py`, `worker_threads.py`), pero solo después de tener una suite sólida.

## Estado actual de pruebas (antes de refactorizar)

Tests relevantes:

- [test_worker.py](/home/developer/repos/hector/El-Secretario/tests/test_worker.py)
- [test_worker_unit.py](/home/developer/repos/hector/El-Secretario/tests/test_worker_unit.py)

Cobertura focal de `worker.py` tras mejoras:

- 88% (test suite de worker).
