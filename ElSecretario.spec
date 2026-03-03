# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Recolectar datos de librerías de IA y UI
datas = [('logo.png', '.')]
datas += collect_data_files('faster_whisper')
datas += collect_data_files('pyannote.audio')
datas += collect_data_files('torch')
datas += collect_data_files('sentence_transformers')
datas += collect_data_files('onnxruntime')

# Si decides incluir FFmpeg en una carpeta 'bin', descomenta la siguiente línea:
# if os.path.exists('bin'): datas += [('bin/*', 'bin')]

hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'faster_whisper',
    'sentence_transformers',
    'onnxruntime',
    'markdown',
    'numpy',
    'sounddevice',
    'soundfile',
]
# Recolectar dinámicamente submódulos de torch para evitar errores de importación
hiddenimports += collect_submodules('torch')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'], # Excluir librerías innecesarias para reducir tamaño
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ElSecretario',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Ponlo en True si necesitas ver errores en una ventana negra al depurar
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ElSecretario',
)
