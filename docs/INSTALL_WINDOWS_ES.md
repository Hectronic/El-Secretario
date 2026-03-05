# 📘 MANUAL DE INSTALACIÓN
El Secretario – Windows 10 / 11

## 🧩 0. Requisitos del sistema

*   Windows 10 o Windows 11 (64 bits)
*   Conexión a Internet
*   Permisos de usuario normal (no hace falta admin salvo PATH)

## 🧩 1. Instalar Python (OBLIGATORIO)

### 🎯 Versión recomendada

👉 **Python 3.10.11 (64-bit)**

Es la versión más estable para Whisper, Torch y pyannote en Windows.
Python `3.11` y `3.12` también están soportados. Evita Python `3.13+` por ahora porque dependencias fijadas como `torch==2.5.1` pueden fallar al instalar.

### 🔽 Descarga

https://www.python.org/downloads/release/python-31011/

Archivo: **Windows installer (64-bit)**

### ⚠️ Durante la instalación (CRÍTICO)

Marca SIEMPRE:

*   ✅ Add Python to PATH
*   ✅ pip
*   ✅ venv

### ✅ Verificación

Abrir PowerShell nuevo:

```powershell
python --version
pip --version
```

Resultado esperado:

```
Python 3.10.11
pip 23.x
```

*(Captura aquí: consola mostrando python --version)*

## 🧩 2. Instalar Git

### 🔽 Descarga

https://git-scm.com/download/win

Instalar con opciones por defecto.

### ✅ Verificación

```powershell
git --version
```

Resultado esperado:

```
git version 2.xx.x.windows.x
```

*(Captura aquí: git --version)*

## 🧩 3. Clonar el repositorio

### 📁 Crear carpeta de trabajo

```powershell
mkdir C:\dev
cd C:\dev
```

### 🔽 Clonar repo correcto

```powershell
git clone https://github.com/Hectronic/El-Secretario.git
cd El-Secretario
```

### ✅ Verificación

```powershell
dir
```

Debe aparecer:

```
main.py
requirements.txt
src\
tests\
```

*(Captura aquí: carpeta del proyecto abierta)*

## 🧩 4. Crear y activar entorno virtual (venv)

### 🔧 Crear venv

```powershell
python -m venv venv
```

### ▶️ Activar venv

```powershell
venv\Scripts\activate
```

Si sale error de ejecución de scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
venv\Scripts\activate
```

### ✅ Resultado correcto

```powershell
(venv) PS C:\dev\El-Secretario>
```

*(Captura aquí: PowerShell con (venv) activo)*

## 🧩 5. Instalar dependencias Python

### 🔄 Actualizar pip

```powershell
python -m pip install --upgrade pip
```

### 📦 Instalar requirements

```powershell
pip install -r requirements.txt
```

⏳ Puede tardar varios minutos (Torch, Whisper).

*(Captura aquí: instalación completada sin errores)*

## 🧩 6. Instalar ffmpeg (IMPRESCINDIBLE)

ffmpeg es el motor que permite:

*   Leer audios (mp3, wav, m4a…)
*   Convertirlos para Whisper
*   Procesarlos para diarización

### 🔽 Descarga correcta

https://www.gyan.dev/ffmpeg/builds/

En release builds, descargar: **ffmpeg-release-essentials.zip**

### 📂 Estructura correcta

1.  Extraer el ZIP
2.  Mover el contenido a: `C:\ffmpeg`

Estructura final correcta:

```
C:\ffmpeg\
 ├─ bin\
 │   ├─ ffmpeg.exe
 │   ├─ ffprobe.exe
 │   └─ ffplay.exe
 ├─ doc\
 ├─ presets\
```

*(Captura aquí: C:\ffmpeg\bin mostrando los .exe)*

### ➕ Añadir ffmpeg al PATH

Ruta exacta a añadir: `C:\ffmpeg\bin`

Pasos:

1.  Win + R → `sysdm.cpl`
2.  Opciones avanzadas
3.  Variables de entorno
4.  Path (usuario)
5.  Nuevo → pegar ruta

### ✅ Verificación

Cerrar PowerShell → abrir nuevo:

```powershell
ffmpeg -version
```

Resultado esperado:

```
ffmpeg version 8.x
```

*(Captura aquí: ffmpeg -version)*

## 🧩 7. Primer arranque de El Secretario

### ▶️ Ejecutar la app

```powershell
cd C:\dev\El-Secretario
venv\Scripts\activate
python main.py
```

## 🧩 8. Error conocido y solución (IMPORTANTE)

### ❌ Error

`ModuleNotFoundError: No module named 'markdown'`

### ✅ Solución

```powershell
pip install markdown
```

Y volver a ejecutar:

```powershell
python main.py
```

📌 Es un bug del proyecto, no del usuario.

### ❌ Error

`Transcription subprocess crashed with exit code 3221225477`

### ✅ Solución (regresión de ctranslate2 en Windows)

Ejecutar dentro del venv del proyecto:

```powershell
pip uninstall -y ctranslate2
pip install "ctranslate2<4.7"
pip install -r requirements.txt
```

Y volver a ejecutar:

```powershell
python main.py
```

### ⚙ Ajustes recomendados para estabilidad en Windows

- `Ajustes de audio -> Auto-index to RAG`: activado por defecto (`true`).
- `Ajustes de audio -> Transcription Backend`: mantener en `auto` salvo que quieras forzar `openai-whisper`.
- Si los crashes con faster-whisper continúan, cambia a `openai-whisper` en Ajustes. La app puede guardar automáticamente el backend que funcione tras un fallback exitoso.

## 🧩 9. Warnings que NO son errores

Estos mensajes se pueden ignorar:

*   FutureWarning de Google / Gemini
*   Warnings de pyannote o torchaudio

👉 No impiden el funcionamiento.

## 🧩 10. Configuración opcional de APIs

### 🔑 Hugging Face (diarización)

*   Token READ
*   Aceptar modelo: `pyannote/speaker-diarization-3.1`

### 🔑 Gemini API (chat con audios)

*   API Key desde Google AI Studio

Se introducen en:

*   UI de la app o
*   archivo `.env` (según versión)

## 🧪 11. Prueba final recomendada

1.  Importar audio MP3 o WAV
2.  Esperar transcripción
3.  Verificar:
    *   No errores
    *   Audio procesado
    *   Texto generado
