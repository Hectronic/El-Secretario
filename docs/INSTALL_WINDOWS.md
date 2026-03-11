# 📘 INSTALLATION MANUAL
El Secretario – Windows 10 / 11

## 🧩 0. System Requirements

*   Windows 10 or Windows 11 (64-bit)
*   Internet Connection
*   Standard user permissions (Admin not required except for PATH)

## 🧩 1. Install Python (MANDATORY)

### 🎯 Recommended Version

👉 **Python 3.10.11 (64-bit)**

This is the most stable version for Whisper, Torch, and pyannote on Windows.
Python `3.11` and `3.12` are also supported. Avoid Python `3.13+` for now because pinned dependencies like `torch==2.5.1` may fail to install.

### 🔽 Download

https://www.python.org/downloads/release/python-31011/

File: **Windows installer (64-bit)**

### ⚠️ During Installation (CRITICAL)

ALWAYS check:

*   ✅ Add Python to PATH
*   ✅ pip
*   ✅ venv

### ✅ Verification

Open a new PowerShell window:

```powershell
python --version
pip --version
```

Expected result:

```
Python 3.10.11
pip 23.x
```

*(Screenshot here: console showing python --version)*

## 🧩 2. Install Git

### 🔽 Download

https://git-scm.com/download/win

Install with default options.

### ✅ Verification

```powershell
git --version
```

Expected result:

```
git version 2.xx.x.windows.x
```

*(Screenshot here: git --version)*

## 🧩 3. Clone the Repository

### 📁 Create Working Directory

```powershell
mkdir C:\dev
cd C:\dev
```

### 🔽 Clone Correct Repo

```powershell
git clone https://github.com/Hectronic/El-Secretario.git
cd El-Secretario
```

### ✅ Verification

```powershell
dir
```

Should show:

```
main.py
requirements.txt
src\
tests\
```

*(Screenshot here: project folder open)*

## 🧩 4. Create and Activate Virtual Environment (venv)

### 🔧 Create venv

```powershell
python -m venv venv
```

### ▶️ Activate venv

```powershell
venv\Scripts\activate
```

If you get a script execution error:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
venv\Scripts\activate
```

### ✅ Correct Result

```powershell
(venv) PS C:\dev\El-Secretario>
```

*(Screenshot here: PowerShell with (venv) active)*

## 🧩 5. Install Python Dependencies

### 🔄 Update pip

```powershell
python -m pip install --upgrade pip
```

### 📦 Install requirements

```powershell
pip install -r requirements.txt
```

⏳ This may take several minutes (Torch, Whisper).

*(Screenshot here: installation completed without errors)*

## 🧩 6. Install ffmpeg (ESSENTIAL)

ffmpeg is the engine that allows:

*   Reading audio files (mp3, wav, m4a…)
*   Converting them for Whisper
*   Processing them for diarization

### 🔽 Correct Download

https://www.gyan.dev/ffmpeg/builds/

In release builds, download: **ffmpeg-release-essentials.zip**

### 📂 Correct Structure

1.  Extract the ZIP
2.  Move the content to: `C:\ffmpeg`

Final correct structure:

```
C:\ffmpeg\
 ├─ bin\
 │   ├─ ffmpeg.exe
 │   ├─ ffprobe.exe
 │   └─ ffplay.exe
 ├─ doc\
 ├─ presets\
```

*(Screenshot here: C:\ffmpeg\bin showing the .exe files)*

### ➕ Add ffmpeg to PATH

Exact path to add: `C:\ffmpeg\bin`

Steps:

1.  Win + R → `sysdm.cpl`
2.  Advanced
3.  Environment Variables
4.  Path (User variables)
5.  New → paste path

### ✅ Verification

Close PowerShell → open a new one:

```powershell
ffmpeg -version
```

Expected result:

```
ffmpeg version 8.x
```

*(Screenshot here: ffmpeg -version)*

## 🧩 7. First Run of El Secretario

### ▶️ Run the App

```powershell
cd C:\dev\El-Secretario
venv\Scripts\activate
python main.py
```

## 🧩 8. Known Error and Solution (IMPORTANT)

### ❌ Error

`ModuleNotFoundError: No module named 'markdown'`

### ✅ Solution

```powershell
pip install markdown
```

And run again:

```powershell
python main.py
```

📌 This is a project bug, not a user error.

### ❌ Error

`Transcription subprocess crashed with exit code 3221225477`

### ✅ Solution (ctranslate2 regression on Windows)

Run inside the project venv:

```powershell
pip uninstall -y ctranslate2
pip install "ctranslate2<4.7"
pip install -r requirements.txt
```

Then run again:

```powershell
python main.py
```

### ⚙ Settings recommended for stable Windows operation

- `Audio Settings -> Auto-index to RAG`: enabled by default (`true`).
- `Audio Settings -> Transcription Backend`: keep `auto` unless you want to force `openai-whisper`.
- If faster-whisper crashes continue, switch to `openai-whisper` in Settings. The app can persist the working backend automatically after successful fallback.

## 🧩 9. Warnings that are NOT Errors

These messages can be ignored:

*   FutureWarning from Google / Gemini
*   Warnings from pyannote or torchaudio

👉 They do not prevent functionality.

## 🧩 10. Optional API Configuration

### 🔑 Hugging Face (Diarization)

*   READ Token
*   Accept model: `pyannote/speaker-diarization-3.1`

### 🔑 Gemini API (Chat with Audio)

*   API Key from Google AI Studio

Enter them in:

*   App UI or
*   `.env` file (depending on version)

## 🧪 11. Recommended Final Test

1.  Import MP3 or WAV audio
2.  Wait for transcription
3.  Verify:
    *   No errors
    *   Audio processed
    *   Text generated
