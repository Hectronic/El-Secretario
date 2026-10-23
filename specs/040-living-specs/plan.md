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
