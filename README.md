<p align="center">
  <img src="logo.png" alt="El Secretario Logo" width="200"/>
</p>

# El Secretario

El Secretario is an intelligent audio transcription and organization tool designed to help you manage your recordings and notes efficiently. It leverages advanced AI models for transcription, diarization, and semantic search, allowing you to easily find and interact with your audio content.

Read this in [Español](README_ES.md) | [Asturianu](README_AST.md)

## Features

- **Audio Recording & Import**: Record audio directly within the app or import existing files.
- **Transcription & Diarization**: Automatically transcribe audio and identify different speakers (diarization) using OpenAI's Whisper and pyannote.audio.
- **Intelligent Search (RAG)**: Use Retrieval-Augmented Generation (RAG) to chat with your recordings and find specific information.
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

## Configuration

To fully utilize the features of El Secretario, you will need to configure the API tokens. You can do this easily via the **🔧 Settings** button on the Welcome screen, or manually in the application settings.

1.  **Hugging Face Token**: Required for speaker diarization (identifying who is speaking).
    -   Create a token at: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    -   Ensure you have accepted the user conditions for the `pyannote/speaker-diarization-3.1` model.

2.  **Gemini API Key**: Required for the AI Assistant (chat) features.
    -   Get your API key at: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

## Usage

1.  **Run the application:**
    ```bash
    ./run.sh
    ```

2.  **Start Recording**: Click the microphone icon to start recording.
3.  **Import Audio**: Use the import button to add existing audio files.
4.  **Chat**: Open a recording or a collection to start chatting with your data.

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
