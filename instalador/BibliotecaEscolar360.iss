; Compilar despues de generar dist\BibliotecaEscolar.exe con crear_exe.bat.
#define MyAppName "Biblioteca Escolar 360"
#define MyAppVersion "1.0.0"
#define MyAppExeName "BibliotecaEscolar.exe"

[Setup]
; Este AppId debe permanecer igual en todas las actualizaciones.
AppId={{F66C6067-820A-4BE0-B8EA-6035A8413260}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Andrés Darío Verdún
AppPublisherURL=https://github.com/Andres-Verdun/biblioteca-escolar
DefaultDirName={localappdata}\Programs\BibliotecaEscolar360
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\instaladores
OutputBaseFilename=BibliotecaEscolar360-Instalador-{#MyAppVersion}-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; Lista explicita: nunca incluir bases de datos ni el directorio del proyecto.
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME_INSTALACION.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

; No se crean entradas de borrado para LOCALAPPDATA\BibliotecaEscolar360.
; Los datos pertenecen a la bibliotecaria y sobreviven a la desinstalacion.
