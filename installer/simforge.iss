; Installeur Windows de SimForge Studio (Inno Setup 6). Compilé par .github/workflows/release.yml :
;   iscc /DAppVer=3.1.0 installer\simforge.iss
#ifndef AppVer
  #define AppVer "0.0.0"
#endif
[Setup]
AppId={{8E0C6B1E-5B0B-4F0E-9C55-51F0A6E3D7A1}
AppName=SimForge Studio
AppVersion={#AppVer}
AppPublisher=Greg7900
AppPublisherURL=https://github.com/Greg7900/SimForge-Studio
DefaultDirName={autopf}\SimForge Studio
DefaultGroupName=SimForge Studio
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=SimForge-Studio-Setup-{#AppVer}
SetupIconFile=..\simforge-studio-v3\simforge_studio.ico
UninstallDisplayIcon={app}\SimForge Studio V3.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\simforge-studio-v3\firmware\LICENSE.txt

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"

[Files]
Source: "..\simforge-studio-v3\dist\SimForge Studio V3\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\SimForge Studio"; Filename: "{app}\SimForge Studio V3.exe"
Name: "{autodesktop}\SimForge Studio"; Filename: "{app}\SimForge Studio V3.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SimForge Studio V3.exe"; Description: "{cm:LaunchProgram,SimForge Studio}"; Flags: nowait postinstall skipifsilent
