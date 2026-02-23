<p align="center">
  <img src="logo.png" alt="El Secretario Logo" width="200"/>
</p>

# El Secretario

El Secretario es una herramienta inteligente de transcripción y organización de audio diseñada para ayudarte a gestionar tus grabaciones y notas de manera eficiente. Aprovecha modelos avanzados de IA para la transcripción, diarización y búsqueda semántica, permitiéndote encontrar e interactuar fácilmente con tu contenido de audio.

## Características

- **Grabación e Importación de Audio**: Graba audio directamente en la aplicación o importa archivos existentes.
- **Transcripción y Diarización**: Transcribe audio automáticamente e identifica diferentes hablantes (diarización) utilizando Whisper de OpenAI y pyannote.audio.
- **Búsqueda Inteligente (RAG)**: Utiliza Generación Aumentada por Recuperación (RAG) para chatear con tus grabaciones y encontrar información específica. Soporta Google Gemini y **Ollama** para ejecución local.
- **Libretas y Colecciones**: Organiza tus grabaciones en libretas y colecciones. Accede a ellas directamente desde la barra lateral.
- **Vista de Calendario**: Explora tus grabaciones por fecha.
- **Herramientas Unificadas**: Limpieza de almacenamiento, procesamiento por lotes y exportación/importación de datos en una sola pestaña.
- **Tema Personalizable**: Soporte para temas Claro, Oscuro y del Sistema.

## Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone https://github.com/hector/secretario.git
    cd secretario
    ```

2.  **Crear un entorno virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Instalar dependencias del sistema (Linux):**
    Es posible que necesites instalar las bibliotecas `ffmpeg` y `portaudio`.
    ```bash
    sudo apt-get install ffmpeg portaudio19-dev
    ```

    > **Usuarios de Windows:** Por favor consultad la [Guía de Instalación para Windows](docs/INSTALL_WINDOWS_ES.md).

## Configuración

Para utilizar plenamente las funciones de El Secretario, deberás configurar los tokens de API. Puedes hacerlo fácilmente a través del botón **🔧 Settings** en la pantalla de Bienvenida, o manualmente en la configuración de la aplicación.

1.  **Token de Hugging Face**: Requerido para la diarización de hablantes (identificar quién está hablando).
    -   Crea un token en: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    -   Asegúrate de haber aceptado las condiciones de usuario para el modelo `pyannote/speaker-diarization-3.1`.

2.  **Clave API de Gemini**: Requerida por defecto para las funciones del Asistente de IA (chat).
    -   Obtén tu clave API en: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

3.  **Ollama**: (Opcional) Alternativa para las funciones del Asistente de IA si prefieres ejecutar modelos localmente.
    -   Instala [Ollama](https://ollama.com/) en tu sistema.
    -   Asegúrate de que el servidor de Ollama esté funcionando antes de iniciar la aplicación.
    -   Puedes seleccionar tu modelo local preferido (ej. `llama3`, `mistral`) en la configuración de la aplicación.

## Uso

1.  **Ejecutar la aplicación:**
    ```bash
    ./run.sh
    ```

2.  **Iniciar Grabación**: Haz clic en el icono del micrófono para comenzar a grabar.
3.  **Importar Audio**: Usa el botón de importar para añadir archivos de audio existentes.
4.  **Chat**: Abre una grabación o una colección para comenzar a chatear con tus datos.

## Exportación/Importación de Datos

El Secretario te permite exportar todos tus datos (grabaciones, transcripciones, libretas, sesiones de chat) a un archivo JSON e importarlos en otra instalación.

### Exportar Datos
1. Haz clic en **⚙️ Tools** desde la pantalla de Bienvenida
2. Ve a la pestaña **📦 Data**
3. Haz clic en **Export All Data** y elige una ubicación

**Nota:** Los archivos de audio NO se exportan, solo las transcripciones y metadatos.

### Importar Datos
1. Ve a **⚙️ Tools** → pestaña **📦 Data**
2. Haz clic en **Import Data** y selecciona un archivo JSON exportado
3. El sistema detectará y omitirá automáticamente los duplicados

## Licencia

Este proyecto está licenciado bajo la Licencia Pública General GNU v3.0 - consulta el archivo [LICENSE](LICENSE) para más detalles.

## Copyright

Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
