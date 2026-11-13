# Implementation Plan: Audio Capture and Import

**Branch**: `001-audio-capture-import` | **Status**: Implemented

Capture/import ownership is split between `src/ui/welcome/`, `src/ui/recording_in_progress/`, and main-window recording tabs. Qt lifecycle and platform guards are covered by recording integration tests.

## Seguimiento Ubuntu en PR #68 (2026-11-13)

El [run 43349738105](https://github.com/Hectronic/El-Secretario/actions/runs/43349738105/job/131637604099) falló durante la colección de integración: la inicialización de `sounddevice`/PortAudio no pudo conectar con PulseAudio. Antes de corregirlo se reprodujo en Linux con un módulo de prueba que lanza `sounddevice.PortAudioError` al importar: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/secretario-portaudio-failure:$PWD ./.venv/bin/python -m pytest --collect-only -q tests/integration/test_audio_compression_service.py` terminó con error de colección.

La corrección pertenece a `tests/conftest.py`, no al runtime de audio. Solo ante `sounddevice.PortAudioError` en importación se instala un doble que devuelve cero dispositivos y rechaza `InputStream`, con advertencia explícita. Con `--run-audio-hw` no se instala el doble y se informa el fallo; otros errores siguen propagándose. El cambio cruza el límite del entorno de pruebas y el hardware, sin cambiar comportamiento de producción.

En Linux, `.venv`, Qt offscreen: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_audio_test_environment.py tests/test_z_audio.py tests/worker/test_worker_integration.py -q` — 13 passed. `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/secretario-portaudio-failure:$PWD ./.venv/bin/python -m pytest -q tests/integration` — 85 passed. Esta integración usa Qt/SQLite reales y conserva las dobles de hardware existentes; la nueva regresión verifica que una importación PortAudio fallida no impide la colección, que el modo de hardware real informa el error y que no se ocultan otros errores.

Suite completa en Linux/offscreen con el fallo simulado: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/secretario-portaudio-failure:$PWD ./.venv/bin/python -m pytest -q` — 1060 passed, 1 skipped por ausencia de bandeja, 11 subtests passed (126.14 s). Una cuarta regresión añadida tras la colección de esa suite se ejecutó por separado: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_audio_test_environment.py -q` — 4 passed. La validación de CI Ubuntu pasó sobre el commit `f818c37`: [run 43354250576](https://github.com/Hectronic/El-Secretario/actions/runs/43354250576), con integración y suite completa superadas. macOS también pasó en ese run; Windows seguía en ejecución al registrar esta evidencia.

Para reproducir el fallo de importación utilizado en los comandos anteriores:

```bash
mkdir -p /tmp/secretario-portaudio-failure
cat > /tmp/secretario-portaudio-failure/sounddevice.py <<'AUDIO_EOF'
class PortAudioError(Exception):
    pass

raise PortAudioError("Error initializing PortAudio: PulseAudio_Initialize: Can't connect to server")
AUDIO_EOF
```
