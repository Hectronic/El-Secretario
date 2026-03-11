# 📘 MANUAL D'INSTALACIÓN
El Secretario – Windows 10 / 11

## 🧩 0. Requisitos del sistema

*   Windows 10 o Windows 11 (64 bits)
*   Conexón a Internet
*   Permisos d'usuariu normal (nun fai falta alministrador sacante pal PATH)

## 🧩 1. Instalar Python (OBLIGATORIO)

### 🎯 Versión recomendada

👉 **Python 3.10.11 (64-bit)**

Ye la versión más estable pa Whisper, Torch y pyannote en Windows.
Python `3.11` y `3.12` tamién tan soportaos. Evita Python `3.13+` por agora porque dependencies fixaes como `torch==2.5.1` pueden fallar al instalase.

### 🔽 Descarga

https://www.python.org/downloads/release/python-31011/

Archivu: **Windows installer (64-bit)**

### ⚠️ Mientres la instalación (CRÍTICU)

Marca SIEMPRE:

*   ✅ Add Python to PATH
*   ✅ pip
*   ✅ venv

### ✅ Verificación

Abrir PowerShell nuevu:

```powershell
python --version
pip --version
```

Resultáu esperáu:

```
Python 3.10.11
pip 23.x
```

*(Captura equí: consola amosando python --version)*

## 🧩 2. Instalar Git

### 🔽 Descarga

https://git-scm.com/download/win

Instalar coles opciones por defeutu.

### ✅ Verificación

```powershell
git --version
```

Resultáu esperáu:

```
git version 2.xx.x.windows.x
```

*(Captura equí: git --version)*

## 🧩 3. Clonar el repositoriu

### 📁 Crear carpeta de trabayu

```powershell
mkdir C:\dev
cd C:\dev
```

### 🔽 Clonar repo correutu

```powershell
git clone https://github.com/Hectronic/El-Secretario.git
cd El-Secretario
```

### ✅ Verificación

```powershell
dir
```

Tien d'apaecer:

```
main.py
requirements.txt
src\
tests\
```

*(Captura equí: carpeta del proyeutu abierta)*

## 🧩 4. Crear y activar entornu virtual (venv)

### 🔧 Crear venv

```powershell
python -m venv venv
```

### ▶️ Activar venv

```powershell
venv\Scripts\activate
```

Si sal fallu d'execución de scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
venv\Scripts\activate
```

### ✅ Resultáu correutu

```powershell
(venv) PS C:\dev\El-Secretario>
```

*(Captura equí: PowerShell con (venv) activu)*

## 🧩 5. Instalar dependencies Python

### 🔄 Anovar pip

```powershell
python -m pip install --upgrade pip
```

### 📦 Instalar requirements

```powershell
pip install -r requirements.txt
```

⏳ Pue tardar varios minutos (Torch, Whisper).

*(Captura equí: instalación completada ensin fallos)*

## 🧩 6. Instalar ffmpeg (IMPRESCINDIBLE)

ffmpeg ye el motor que permite:

*   Lleer audios (mp3, wav, m4a…)
*   Convertilos pa Whisper
*   Procesalos pa diarización

### 🔽 Descarga correuta

https://www.gyan.dev/ffmpeg/builds/

En release builds, descargar: **ffmpeg-release-essentials.zip**

### 📂 Estructura correuta

1.  Estrayer el ZIP
2.  Mover el conteníu a: `C:\ffmpeg`

Estructura final correuta:

```
C:\ffmpeg\
 ├─ bin\
 │   ├─ ffmpeg.exe
 │   ├─ ffprobe.exe
 │   └─ ffplay.exe
 ├─ doc\
 ├─ presets\
```

*(Captura equí: C:\ffmpeg\bin amosando los .exe)*

### ➕ Añader ffmpeg al PATH

Ruta exacta a añader: `C:\ffmpeg\bin`

Pasos:

1.  Win + R → `sysdm.cpl`
2.  Opciones avanzaes
3.  Variables d'entornu
4.  Path (usuariu)
5.  Nuevu → pegar ruta

### ✅ Verificación

Zarrar PowerShell → abrir nuevu:

```powershell
ffmpeg -version
```

Resultáu esperáu:

```
ffmpeg version 8.x
```

*(Captura equí: ffmpeg -version)*

## 🧩 7. Primer arranque d'El Secretario

### ▶️ Executar l'app

```powershell
cd C:\dev\El-Secretario
venv\Scripts\activate
python main.py
```

## 🧩 8. Fallu conocíu y solución (IMPORTANTE)

### ❌ Fallu

`ModuleNotFoundError: No module named 'markdown'`

### ✅ Solución

```powershell
pip install markdown
```

Y volver executar:

```powershell
python main.py
```

📌 Ye un bug del proyeutu, non del usuariu.

### ❌ Fallu

`Transcription subprocess crashed with exit code 3221225477`

### ✅ Solución (regresión de ctranslate2 en Windows)

Executar dientro del venv del proyeutu:

```powershell
pip uninstall -y ctranslate2
pip install "ctranslate2<4.7"
pip install -r requirements.txt
```

Y volver executar:

```powershell
python main.py
```

### ⚙ Ajustes recomendaos pa estabilidá en Windows

- `Ajustes d'audio -> Auto-index to RAG`: activáu por defeutu (`true`).
- `Ajustes d'audio -> Transcription Backend`: caltenlo en `auto` sacante que quieras forzar `openai-whisper`.
- Si los crashes con faster-whisper sigan, camuda a `openai-whisper` n'Ajustes. L'app pue guardar automáticamente'l backend que funcione tres un fallback esitósu.

## 🧩 9. Avisos que NON son fallos

Estos mensaxes puen inorase:

*   FutureWarning de Google / Gemini
*   Warnings de pyannote o torchaudio

👉 Nun torguen el funcionamientu.

## 🧩 10. Configuración opcional d'APIs

### 🔑 Hugging Face (diarización)

*   Token READ
*   Aceptar modelu: `pyannote/speaker-diarization-3.1`

### 🔑 Gemini API (chat con audios)

*   API Key dende Google AI Studio

Introdúcense en:

*   UI de l'app o
*   archivu `.env` (según versión)

## 🧪 11. Prueba final recomendada

1.  Importar audio MP3 o WAV
2.  Esperar trescripción
3.  Verificar:
    *   Non fallos
    *   Audio procesáu
    *   Testu xeneráu
