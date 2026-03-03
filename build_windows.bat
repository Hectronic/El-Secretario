@echo off
setlocal

echo [1/5] Comprobando entorno virtual...
if not exist venv (
    echo [ERROR] No se encuentra la carpeta 'venv'. 
    echo Por favor, crea el entorno virtual (python -m venv venv) e instala las dependencias 
    echo (pip install -r requirements.txt) antes de ejecutar este script.
    pause
    exit /b 1
)

echo [2/5] Verificando PyInstaller...
venv\Scripts\python -m PyInstaller --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller no detectado. Instalando en el entorno virtual...
    venv\Scripts\python -m pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] No se pudo instalar PyInstaller. Revisa tu conexion a internet.
        pause
        exit /b 1
    )
) else (
    echo PyInstaller ya esta instalado.
)

echo [3/5] Limpiando carpetas de compilacion previas...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [4/5] Iniciando PyInstaller (ElSecretario.spec)...
echo ATENCION: Esto puede tardar varios minutos debido a Torch y Faster-Whisper.
echo No cierres esta ventana.
venv\Scripts\python -m PyInstaller --clean ElSecretario.spec

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] La compilacion ha fallado. Revisa los mensajes de arriba.
    pause
    exit /b %ERRORLEVEL%
)

echo [5/5] Compilacion completada con exito.
echo.
echo ============================================================
echo EJECUTABLE GENERADO: dist\ElSecretario\ElSecretario.exe
echo ============================================================
echo.
echo Recuerda que debes distribuir TODA la carpeta 'dist\ElSecretario'
echo (puedes comprimirla en un archivo .ZIP o .RAR).

pause
