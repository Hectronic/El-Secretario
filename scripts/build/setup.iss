; Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License, version 3 or later.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
; You should have received a copy of the GNU General Public License along with
; this program.  If not, see <https://www.gnu.org/licenses/>.

; Inno Setup Compiler Script for El Secretario

[Setup]
AppId={{E58E298C-DFFB-4A2D-BEA3-488686616C2D}
AppName=El Secretario
AppVersion=1.0.0
AppPublisher=Héctor Álvarez López
AppPublisherURL=https://github.com/Hectronic/El-Secretario
AppSupportURL=https://github.com/Hectronic/El-Secretario/issues
AppUpdatesURL=https://github.com/Hectronic/El-Secretario
DefaultDirName={userappdata}\El-Secretario
DefaultGroupName=El Secretario
OutputDir=..\..\dist
OutputBaseFilename=el-secretario-windows-setup
SetupIconFile=..\..\resources\logo.ico
Compression=lzma
SolidCompression=yes
; "PrivilegesRequired=lowest" allows installation in AppData without UAC admin prompt!
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy source files, ignoring developer/temp folders
Source: "..\..\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs; ExcludeFiles: ".venv\*,.pytest_cache\*,__pycache__\*,venv\*,dist\*,build\*,run.json,.git\*"

[Icons]
Name: "{group}\El Secretario"; Filename: "{app}\run.bat"; IconFilename: "{app}\resources\logo.ico"; WorkingDir: "{app}"
Name: "{group}\Uninstall El Secretario"; Filename: "{uninstallexe}"
Name: "{userdesktop}\El Secretario"; Filename: "{app}\run.bat"; IconFilename: "{app}\resources\logo.ico"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
; Run the silent installer bootstrapper after files are copied to set up python venv
Filename: "{app}\scripts\install\install.bat"; Description: "Initializing virtual environment and dependencies..."; Flags: runhidden
Filename: "{app}\run.bat"; Description: "{cm:LaunchProgram,El Secretario}"; Flags: shellexec postinstall nowait skipifsilent
