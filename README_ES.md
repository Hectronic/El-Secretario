<p align="center">
  <img src="logo.png" alt="El Secretario Logo" width="200"/>
</p>

# El Secretario

El Secretario es una herramienta inteligente de transcripción y organización de audio diseñada para ayudarte a gestionar tus grabaciones y notas de manera eficiente. Aprovecha modelos avanzados de IA para la transcripción, diarización y búsqueda semántica, permitiéndote encontrar e interactuar fácilmente con tu contenido de audio.

## Características

- **Grabación e Importación de Audio**: Graba audio directamente en la aplicación o importa archivos existentes.
- **Edición de grabaciones**: Abre una grabación en una segunda pestaña de edición, recorta segmentos de audio y vuelve a transcribir automáticamente el clip editado. El primer recorte conserva una copia `.orig` del archivo original.
- **Transcripción y Diarización**: Transcribe audio automáticamente, copia la transcripción completa con un clic e identifica diferentes hablantes (diarización) utilizando backends locales de Whisper, `sherpa-onnx` y pyannote.audio.
- **Búsqueda Inteligente (RAG)**: Utiliza Generación Aumentada por Recuperación (RAG) para chatear con tus grabaciones y encontrar información específica. Soporta Google Gemini y **Ollama** para ejecución local.
- **Ventanas de Chat Flexibles**: Los chats pueden quedarse como pestañas normales, moverse a la barra flotante y minimizarse en fichas compactas para restaurarlos rápido.
- **Contexto Activo del Chat en la Barra Lateral**: Cuando una pestaña de chat está activa, la barra lateral derecha de la app muestra una copia desplegable y abierta por defecto del contexto del chat, y la oculta al cambiar de pestaña o cerrar el chat.
- **Libretas y Colecciones**: Organiza tus grabaciones en libretas y colecciones. Accede a ellas directamente desde la barra lateral.
- **Vista de Calendario**: Explora tus grabaciones por fecha.
- **Herramientas Unificadas**: Limpieza de almacenamiento, procesamiento por lotes y exportación/importación de datos en una sola pestaña.
- **Tema Personalizable**: Soporte para temas Claro, Oscuro y del Sistema.

## Arquitectura y Specs

- Notas de arquitectura: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Registro de funcionalidades orientado a spec-driven development: [docs/specs/README.md](docs/specs/README.md)

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
    > Usad Python `3.12` (recomendado) o `3.11`. Python `3.14` no es compatible actualmente con dependencias de ML fijadas como `torch==2.5.1`.

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

4.  **Sherpa-ONNX**: (Opcional) Backend alternativo de transcripción local.
    -   Instala las dependencias de `requirements.txt` para disponer del paquete Python `sherpa-onnx`.
    -   Descarga un modelo offline compatible en un directorio local, por ejemplo `models/sherpa-onnx`.
    -   Configura la ruta del modelo y su tipo en **Ajustes -> Audio** si seleccionas `sherpa-onnx` como opción de transcripción.
    -   Si falta el modelo local configurado, El Secretario puede descargar automáticamente en el primer uso el archivo oficial por defecto `sherpa-onnx-whisper-tiny`.

## Uso

1.  **Ejecutar la aplicación:**
    ```bash
    ./run.sh
    ```

2.  **Iniciar Grabación**: Haz clic en el icono del micrófono para comenzar a grabar.
3.  **Importar Audio**: Usa el botón de importar para añadir archivos de audio existentes.
4.  **Chat**: Abre una grabación o una colección para comenzar a chatear con tus datos.
5.  **Editar Grabaciones**: Haz clic derecho sobre una grabación en el historial o en una pestaña abierta y elige la opción para duplicar el editor. Usa los controles de **Audio Edit** para marcar inicio y fin, recortar el clip y dejar que la app lo vuelva a transcribir.
6.  **Barra Lateral de Contexto Activo**: Cuando una pestaña de chat está activa, la barra lateral derecha de la app muestra el mismo panel de contexto que ves dentro del chat. Se abre por defecto y desaparece al cambiar a otra pestaña o cerrar el chat.

**Nota:** el editor actual usa marcadores de tiempo (`inicio`/`fin`) y botones para fijar el punto de reproducción. Todavía no incluye una forma de selección por waveform ni una línea de tiempo arrastrable.

**Nota:** esta barra lateral es una copia de solo lectura del contexto del chat activo. No permanece visible para chats inactivos ni para ventanas flotantes/minimizadas.

## Ejecutar Pruebas

Ejecuta las pruebas con el entorno virtual del proyecto para evitar diferencias con el Python global:

```bash
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m pytest -q
```

También puedes usar:

```bash
./run_with_test.sh
```

GitHub Actions ejecuta automáticamente esta suite completa en Ubuntu, Windows y macOS en cada pull request.

## Estabilidad de transcripción en Windows

- En Windows, la transcripción ahora reintenta automáticamente con perfiles de backend más seguros cuando el subproceso aislado de Whisper se cae (por ejemplo, código de salida `3221225477`).
- Si falla un perfil CUDA, El Secretario cambia automáticamente a perfiles de CPU antes de reportar error.
- Si los fallos nativos persisten, El Secretario reintenta automáticamente con modelos Whisper más pequeños (`large-v3` -> `medium` -> `base`).
- Las dependencias fijan `ctranslate2<4.7` en Windows para evitar crashes nativos conocidos en versiones más nuevas.
- Si todos los intentos con faster-whisper se caen en Windows, El Secretario usa un fallback de compatibilidad con `openai-whisper`.
- El backend de transcripción se puede configurar en Ajustes (`auto`, `faster-whisper`, `openai-whisper`).
- El selector compartido de transcripción está unificado en toda la aplicación y ahora también soporta `sherpa-onnx` para inferencia totalmente local.
- Los ajustes de Sherpa-ONNX también soportan autodescarga del modelo en el primer uso y una URL de archivo configurable.
- Cuando un fallback funciona, El Secretario guarda automáticamente en Ajustes la configuración de transcripción que funcionó.
- El autoindexado RAG se puede configurar en Ajustes (`auto_index_rag`) y está activado por defecto (`true`).
- En Windows, las operaciones de indexado/búsqueda RAG se aíslan en subprocesos por defecto para reducir crashes nativos de Chroma.
- La pestaña Welcome ahora se adapta mejor a pantallas de Windows con poca altura, con modo compacto automático y scroll vertical cuando hace falta.
- La pestaña Recording in Progress ahora también se adapta a pantallas con poca altura con scroll vertical y modo compacto automático.

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
