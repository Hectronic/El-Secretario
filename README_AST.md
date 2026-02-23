<p align="center">
  <img src="logo.png" alt="El Secretario Logo" width="200"/>
</p>

# El Secretario

El Secretario ye una ferramienta intelixente de trescripción y organización d'audio diseñada p'ayudate a xestionar les tos grabaciones y notes de manera eficiente. Aprovecha modelos avanzaos d'IA pa la trescripción, diarización y gueta semántica, permitiéndote alcontrar y interactuar fácilmente col to conteníu d'audio.

## Carauterístiques

- **Grabación ya Importación d'Audio**: Graba audio direutamente na aplicación o importa archivos esistentes.
- **Trescripción y Diarización**: Trescribe audio automáticamente ya identifica distintos falantes (diarización) usando Whisper d'OpenAI y pyannote.audio.
- **Gueta Intelixente (RAG)**: Usa Xeneración Aumentada por Recuperación (RAG) pa charrar coles tos grabaciones y alcontrar información específica. Soporta Google Gemini y **Ollama** pa execución llocal.
- **Cuadernos y Coleiciones**: Organiza les tos grabaciones en cuadernos y coleiciones. Accede a elles direutamente dende la barra llateral.
- **Vista de Calendariu**: Esplora les tos grabaciones per fecha.
- **Ferramientes Unificaes**: Llimpieza d'almacenamientu, procesamientu per llotes y esportación/importación de datos nuna sola pestaña.
- **Tema Personalizable**: Sofitu pa temes Claru, Escuru y del Sistema.

## Instalación

1.  **Clonar el repositoriu:**
    ```bash
    git clone https://github.com/hector/secretario.git
    cd secretario
    ```

2.  **Crear un entornu virtual:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Instalar dependencies del sistema (Linux):**
    Ye posible que necesites instalar les biblioteques `ffmpeg` y `portaudio`.
    ```bash
    sudo apt-get install ffmpeg portaudio19-dev
    ```

    > **Usuarios de Windows:** Por favor consultái la [Guía d'Instalación pa Windows](docs/INSTALL_WINDOWS_AST.md).

## Configuración

Pa utilizar dafechu les funciones d'El Secretario, deberás configurar los tokens d'API. Pues facelo fácilmente al traviés del botón **🔧 Settings** na pantalla de Bienvenida, o manualmente na configuración de l'aplicación.

1.  **Token de Hugging Face**: Requeríu pa la diarización de falantes (identificar quién ta falando).
    -   Crea un token en: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    -   Asegúrate de tener aceptao les condiciones d'usuariu pal modelu `pyannote/speaker-diarization-3.1`.

2.  **Clave API de Gemini**: Requerida por defeutu pa les funciones del Asistente d'IA (chat).
    -   Llogra la to clave API en: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

3.  **Ollama**: (Opcional) Alternativa pa les funciones del Asistente d'IA si prefieres executar modelos llocalmente.
    -   Instala [Ollama](https://ollama.com/) nel to sistema.
    -   Asegúrate de que'l servidor d'Ollama tea funcionante antes d'entamar l'aplicación.
    -   Pues seleicionar el to modelu llocal preferíu (ex. `llama3`, `mistral`) na configuración de l'aplicación.

## Usu

1.  **Executar l'aplicación:**
    ```bash
    ./run.sh
    ```

2.  **Entamar Grabación**: Fai clic nel iconu del micrófonu pa entamar a grabar.
3.  **Importar Audio**: Usa'l botón d'importar p'añader archivos d'audio esistentes.
4.  **Chat**: Abre una grabación o una coleición pa entamar a charrar colos tos datos.

## Esportación/Importación de Datos

El Secretario permítete esportar tolos tos datos (grabaciones, trescripciones, cuadernos, sesiones de chat) a un archivu JSON ya importarlos n'otra instalación.

### Esportar Datos
1. Fai clic en **⚙️ Tools** dende la pantalla de Bienvenida
2. Ve a la pestaña **📦 Data**
3. Fai clic en **Export All Data** y escueye una ubicación

**Nota:** Los archivos d'audio NUN s'esporten, namás les trescripciones y metadatos.

### Importar Datos
1. Ve a **⚙️ Tools** → pestaña **📦 Data**
2. Fai clic en **Import Data** y seleiciona un archivu JSON esportáu
3. El sistema detectará y omitirá automáticamente los duplicaos

## Llicencia

Esti proyeutu ta licenciáu baxo la Llicencia Pública Xeneral GNU v3.0 - consulta l'archivu [LICENSE](LICENSE) pa más detalles.

## Copyright

Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
