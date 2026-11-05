; Inno Setup Script para Luke-Grabber
; Autor: Antigravity para Lucas

#define MyAppName "Luke-Grabber"
#define MyAppVersion "1.1.1"
#define MyAppPublisher "Luke"
#define MyAppExeName "Luke-Grabber.exe"

[Setup]
AppId={{C47F8B2E-5D3A-4F8A-9A2E-8E1A3D6F7C9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=release
OutputBaseFilename=Luke-Grabber_Setup_v{#MyAppVersion}
SetupIconFile=frontend\app-icon.ico
UninstallDisplayIcon={app}\app-icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Luke-Grabber\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "frontend\app-icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "frontend\app-icon.ico"; DestDir: "{app}\frontend"; Flags: ignoreversion
Source: "frontend\app-icon.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app-icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app-icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
