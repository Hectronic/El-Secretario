<p align="center">
  <img src="logo.png" alt="El Secretario Logo" width="200"/>
</p>

# El Secretario

El Secretario ye una ferramienta intelixente de trescripción y organización d'audio diseñada p'ayudate a xestionar les tos grabaciones y notes de manera eficiente. Aprovecha modelos avanzaos d'IA pa la trescripción, diarización y gueta semántica, permitiéndote alcontrar y interactuar fácilmente col to conteníu d'audio.

## Carauterístiques

- **Grabación ya Importación d'Audio**: Graba audio direutamente na aplicación o importa archivos esistentes.
- **Edición de grabaciones**: Abre una grabación nuna segunda pestaña d'edición, recorta segmentos d'audio y torna a trescribir automáticamente'l clip editáu. El primer recorte caltién una copia `.orig` del archivu orixinal.
- **Trescripción y Diarización**: Trescribe audio automáticamente, copia la trescripción completa con un clic ya identifica distintos falantes (diarización) usando backends llocales de Whisper, `sherpa-onnx` y pyannote.audio.
- **Gueta Intelixente (RAG)**: Usa Xeneración Aumentada por Recuperación (RAG) pa charrar coles tos grabaciones y alcontrar información específica. Soporta Google Gemini y **Ollama** pa execución llocal.
- **Ventanes de Chat Flexibles**: Los chats pueden quedar como pestañes normales, movese a la barra flotante y minimizase en fiches compactes pa restauralos rápido.
- **Contéutu Activo del Chat na Barra Llateral**: Cuando una pestaña de chat ta activa, la barra llateral derecha de la app amuesa una copia desplegable y abierta por defeutu del contéutu del chat, y anúlase al cambiar de pestaña o zarrar el chat.
- **Cuadernos y Coleiciones**: Organiza les tos grabaciones en cuadernos y coleiciones. Accede a elles direutamente dende la barra llateral.
- **Vista de Calendariu**: Esplora les tos grabaciones per fecha.
- **Ferramientes Unificaes**: Llimpieza d'almacenamientu, procesamientu per llotes y esportación/importación de datos nuna sola pestaña.
- **Tema Personalizable**: Sofitu pa temes Claru, Escuru y del Sistema.

## Arquitectura y Specs

- Notes d'arquitectura: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Rexistru de funcionalidaes orientáu a spec-driven development: [docs/specs/README.md](docs/specs/README.md)

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
    > Usái Python `3.12` (recomendáu) o `3.11`. Python `3.14` nun ye compatible anguaño con dependencies de ML fixaes como `torch==2.5.1`.

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

4.  **Sherpa-ONNX**: (Opcional) Backend alternativu de trescripción llocal.
    -   Instala les dependencies de `requirements.txt` pa disponer del paquete Python `sherpa-onnx`.
    -   Descarga un modelu offline compatible nun direutoriu llocal, por exemplu `models/sherpa-onnx`.
    -   Configura la ruta del modelu y el so tipu en **Ajustes -> Audio** si seleiciones `sherpa-onnx` como opción de trescripción.
    -   Si falta'l modelu llocal configuráu, El Secretario pue descargar automáticamente nel primer usu l'archivu oficial por defeutu `sherpa-onnx-whisper-tiny`.

## Usu

1.  **Executar l'aplicación:**
    ```bash
    ./run.sh
    ```

2.  **Entamar Grabación**: Fai clic nel iconu del micrófonu pa entamar a grabar.
3.  **Importar Audio**: Usa'l botón d'importar p'añader archivos d'audio esistentes.
4.  **Chat**: Abre una grabación o una coleición pa entamar a charrar colos tos datos.
5.  **Editar Grabaciones**: Fai clic derechu sobre una grabación nel historial o nuna pestaña abierta y escueye la opción pa duplicar l'editor. Usa los controles d'**Audio Edit** pa marcar entamu y fin, recortar el clip y dexar que l'aplicación lo vuelva a trescribir.
6.  **Barra Llateral de Contéutu Activu**: Cuando una pestaña de chat ta activa, la barra llateral derecha de la app amuesa'l mesmu panel de contéutu que ves dientro del chat. Ábrese por defeutu y desapaez al camudar a otra pestaña o zarrar el chat.

**Nota:** l'editor actual usa marcadores de tiempu (`entamu`/`fin`) y botones pa fixar el puntu de reproducción. Entá nun ufierta una selección por waveform nin una llinia de tiempu arrastrable.

**Nota:** esta barra llateral ye una copia de solo llectura del contéutu del chat activu. Nun queda visible pa chats inactivos nin pa ventanes flotantes/minimizaes.

## Estabilidá de trescripción en Windows

- En Windows, la trescripción agora reintenta automáticamente con perfiles de backend más seguros cuando'l subprocesu aisláu de Whisper se cai (por exemplu, códigu de salida `3221225477`).
- Si falla un perfil CUDA, El Secretario camuda automáticamente a perfiles de CPU enantes de reportar error.
- Si los fallos nativos persisten, El Secretario reintenta automáticamente con modelos Whisper más pequeños (`large-v3` -> `medium` -> `base`).
- Les dependencies fixen `ctranslate2<4.7` en Windows pa evitar crashes nativos conocíos en versiones más nueves.
- Si tolos intentos con faster-whisper se cayen en Windows, El Secretario usa un fallback de compatibilidá con `openai-whisper`.
- El backend de trescripción pue configurase en Ajustes (`auto`, `faster-whisper`, `openai-whisper`).
- El selector compartíu de trescripción ta unificáu en tola aplicación y agora tamién soporta `sherpa-onnx` pa inferencia totalmente llocal.
- Los axustes de Sherpa-ONNX tamién soporten autodescarga del modelu nel primer usu y una URL d'archivu configurable.
- Cuando un fallback funciona, El Secretario guarda automáticamente nos Ajustes la configuración de trescripción que funcionó.
- L'autoindexáu RAG pue configurase n'Ajustes (`auto_index_rag`) y ta activáu por defeutu (`true`).
- En Windows, les operaciones d'indexáu/gueta RAG aíllense en subprocesos por defeutu pa amenorgar crashes nativos de Chroma.
- La pestaña Welcome agora adáptase meyor a pantalles de Windows con poca altura, con mou compactu automáticu y scroll vertical cuando fai falta.
- La pestaña Recording in Progress agora tamién s'adapta a pantalles con poca altura con scroll vertical y mou compactu automáticu.

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
