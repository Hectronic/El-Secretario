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
