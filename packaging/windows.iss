; Compile depois de scripts/build.py, com Inno Setup 6.7.3.
#if PREPROCVER != EncodeVer(6, 7, 3, 0)
  #error Use exatamente Inno Setup 6.7.3 para gerar este instalador.
#endif
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppName "Monitor de Sinais Musculares"

[Setup]
AppId=MuscleMonitorV1
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=NGK-999
DefaultDirName={localappdata}\Programs\MuscleMonitor
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.17763
OutputDir=..\dist\installer
OutputBaseFilename=MonitorMuscular-Instalar
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\MuscleMonitor.exe

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\MuscleMonitor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\MuscleMonitor.exe"; WorkingDir: "{app}"
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\MuscleMonitor.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\MuscleMonitor.exe"; Description: "Abrir o monitor"; Flags: nowait postinstall skipifsilent
