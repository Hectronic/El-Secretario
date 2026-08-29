# Test Playbook (PyQt + venv)

## 1) Detectar intérprete del proyecto

```bash
if [ -x ./.venv/bin/python ]; then
  VENV_PY=./.venv/bin/python
elif [ -x ./venv/bin/python ]; then
  VENV_PY=./venv/bin/python
else
  echo "No project virtualenv found (.venv or venv)" >&2
  exit 1
fi
```

## 2) Comandos base

```bash
$VENV_PY -m pip install -r requirements.txt
$VENV_PY -m py_compile src/ui/audio_editor/widget.py
```

## 3) Ejecutar tests PyQt en headless

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 $VENV_PY -m pytest -q
```

## 4) Ejecutar solo tests afectados (rápido)

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 $VENV_PY -m pytest -q tests/ui/audio_editor/test_widget.py
```

## 5) Fallback si hay conflicto de plugins de pytest

```bash
QT_QPA_PLATFORM=offscreen PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 $VENV_PY -m pytest -q
```

## 6) Política de validación recomendada

1. Ejecutar tests afectados por el cambio.
2. Ejecutar smoke de flujo principal.
3. Ejecutar suite completa antes de cerrar.
4. Informar exactamente qué comandos y qué archivos se validaron.
