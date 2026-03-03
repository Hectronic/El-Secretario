#!/bin/bash

# Salir inmediatamente si algún comando falla
set -e

echo "[1/6] Comprobando entorno virtual..."
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "[ERROR] No se encuentra la carpeta 'venv' o '.venv'."
    echo "Por favor, crea el entorno virtual (python3 -m venv venv) e instala las dependencias."
    exit 1
fi

# Detectar el nombre correcto del entorno virtual
VENV_DIR="venv"
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
fi

source $VENV_DIR/bin/activate

echo "[2/6] Verificando dependencias (PyInstaller)..."
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller no detectado. Instalando..."
    pip install pyinstaller
fi

echo "[3/6] Limpiando carpetas de compilación previas..."
rm -rf build dist

echo "[4/6] Iniciando PyInstaller (ElSecretario.spec)..."
echo "ATENCIÓN: Esto puede tardar varios minutos y consumir mucha RAM."
pyinstaller --clean ElSecretario.spec

echo "[5/6] Preparando el instalador para el usuario final..."
DIST_DIR="dist/ElSecretario"

# 1. Copiar el logo a la carpeta del programa para el icono del sistema
cp logo.png "$DIST_DIR/"

# 2. Crear el script de instalación (install.sh) para el usuario
cat << 'EOF' > "$DIST_DIR/install.sh"
#!/bin/bash
set -e

echo "Instalando El Secretario..."
APP_DIR="$HOME/.local/share/ElSecretario"
DESKTOP_DIR="$HOME/.local/share/applications"

# Crear directorios
mkdir -p "$APP_DIR"
mkdir -p "$DESKTOP_DIR"

# Copiar archivos
echo "Copiando archivos a $APP_DIR..."
cp -r * "$APP_DIR/"

# Dar permisos de ejecución
chmod +x "$APP_DIR/ElSecretario"

# Crear archivo .desktop (Acceso directo para el menú de Ubuntu)
echo "Creando acceso directo..."
cat << DESKTOP > "$DESKTOP_DIR/elsecretario.desktop"
[Desktop Entry]
Name=El Secretario
Comment=Tu asistente y transcriptor de IA
Exec="$APP_DIR/ElSecretario"
Icon=$APP_DIR/logo.png
Terminal=false
Type=Application
Categories=Office;AudioVideo;Utility;
DESKTOP

# Actualizar base de datos de aplicaciones
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ""
echo "=========================================================="
echo "✅ ¡Instalación completada con éxito!"
echo "Puedes encontrar 'El Secretario' en tu menú de aplicaciones."
echo "=========================================================="
EOF

# Dar permisos de ejecución al instalador
chmod +x "$DIST_DIR/install.sh"

echo "[6/6] Comprimiendo el paquete final..."
cd dist
tar -czvf ElSecretario-Ubuntu.tar.gz ElSecretario/
cd ..

echo ""
echo "============================================================"
echo "🎉 COMPILACIÓN COMPLETADA"
echo "============================================================"
echo "El paquete distribuible está en: dist/ElSecretario-Ubuntu.tar.gz"
echo "El usuario solo debe extraer el .tar.gz y ejecutar ./install.sh"
