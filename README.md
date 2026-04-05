<p align="center">
  <img src="logo.png" alt="El Secretario Logo" width="200"/>
</p>

# El Secretario

El Secretario is an intelligent audio transcription and organization tool designed to help you manage your recordings and notes efficiently. It leverages advanced AI models for transcription, diarization, and semantic search, allowing you to easily find and interact with your audio content.

Read this in [Español](README_ES.md) | [Asturianu](README_AST.md)

## Features

- **Audio Recording & Import**: Record audio directly within the app or import existing files.
- **Transcription & Diarization**: Automatically transcribe audio and identify different speakers (diarization) using local Whisper backends, `sherpa-onnx`, and pyannote.audio.
- **Intelligent Search (RAG)**: Use Retrieval-Augmented Generation (RAG) to chat with your recordings and find specific information. Supports Google Gemini and **Ollama** for local execution.
- **Flexible Chat Windows**: Chats can stay as regular tabs, move to the floating bar, and be minimized into compact chips for quick restore.
- **Notebooks & Collections**: Organize your recordings into notebooks and collections. Access them directly from the sidebar.
- **Calendar View**: Browse your recordings by date.
- **Unified Tools**: Storage cleanup, batch processing, and data export/import in one convenient tab.
- **Customizable Theme**: Support for Light, Dark, and System themes.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hector/secretario.git
    cd secretario
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install system dependencies (Linux):**
    You may need to install `ffmpeg` and `portaudio` libraries.
    ```bash
    sudo apt-get install ffmpeg portaudio19-dev
    ```

    > **Windows Users:** Please refer to the [Windows Installation Guide](docs/INSTALL_WINDOWS.md).
    > Use Python `3.12` (recommended) or `3.11`. Python `3.14` is currently not compatible with pinned ML dependencies such as `torch==2.5.1`.

## Configuration

To fully utilize the features of El Secretario, you will need to configure the API tokens. You can do this easily via the **🔧 Settings** button on the Welcome screen, or manually in the application settings.

1.  **Hugging Face Token**: Required for speaker diarization (identifying who is speaking).
    -   Create a token at: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    -   Ensure you have accepted the user conditions for the `pyannote/speaker-diarization-3.1` model.

2.  **Gemini API Key**: Required for the AI Assistant (chat) features by default.
    -   Get your API key at: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

3.  **Ollama**: (Optional) Alternative for AI Assistant features if you prefer to run models locally.
    -   Install [Ollama](https://ollama.com/) on your system.
    -   Ensure the Ollama server is running before starting the app.
    -   You can select your preferred local model (e.g., `llama3`, `mistral`) in the application settings.

4.  **Sherpa-ONNX**: (Optional) Alternative local transcription backend.
    -   Install dependencies from `requirements.txt` so the `sherpa-onnx` Python package is available.
    -   Download a compatible offline model to a local directory, for example `models/sherpa-onnx`.
    -   Configure the model directory and model type in **Settings -> Audio** if you select `sherpa-onnx` as your transcription option.
    -   If the configured local model is missing, El Secretario can automatically download the default official `sherpa-onnx-whisper-tiny` archive on first use.

## Usage

1.  **Run the application:**
    ```bash
    ./run.sh
    ```

2.  **Start Recording**: Click the microphone icon to start recording.
3.  **Import Audio**: Use the import button to add existing audio files.
4.  **Chat**: Open a recording or a collection to start chatting with your data.

## Running Tests

Run tests with the project virtual environment to avoid global Python mismatches:

```bash
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m pytest -q
```

You can also use:

```bash
./run_with_test.sh
```

## Windows Transcription Stability

- On Windows, transcription now retries automatically with safer backend profiles when the isolated Whisper subprocess crashes (for example exit code `3221225477`).
- If a CUDA profile fails, El Secretario falls back to CPU profiles automatically before reporting an error.
- If native crashes persist, El Secretario retries automatically with smaller Whisper models (`large-v3` -> `medium` -> `base`).
- Dependencies pin `ctranslate2<4.7` on Windows to avoid known native crashes in newer builds.
- If all faster-whisper attempts crash on Windows, El Secretario uses an `openai-whisper` compatibility fallback.
- Transcription backend is configurable in Settings (`auto`, `faster-whisper`, `openai-whisper`).
- The shared transcription model selector is available across the application and now also supports `sherpa-onnx` for fully local inference.
- Sherpa-ONNX settings also support automatic first-run model download and a configurable archive URL.
- When a fallback path succeeds, El Secretario stores the working transcription configuration in Settings automatically.
- RAG auto-indexing is configurable in Settings (`auto_index_rag`) and enabled by default (`true`).
- On Windows, RAG indexing/search operations are isolated in subprocesses by default to reduce native Chroma crashes.
- The Welcome tab now adapts better to low-height Windows screens with an automatic compact layout and vertical scrolling when needed.
- The Recording in Progress tab now also adapts to low-height screens with vertical scrolling and an automatic compact mode.

## Data Export/Import

El Secretario allows you to export all your data (recordings, transcriptions, notebooks, chat sessions) to a JSON file and import it back on another installation.

### Exporting Data
1. Click **⚙️ Tools** from the Welcome screen
2. Go to the **📦 Data** tab
3. Click **Export All Data** and choose a location

**Note:** Audio files are NOT exported, only transcriptions and metadata.

### Importing Data
1. Go to **⚙️ Tools** → **📦 Data** tab
2. Click **Import Data** and select an exported JSON file
3. The system will automatically detect and skip duplicates

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Copyright

Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
