#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId=VisrtxRendererForBasic.polar2251
AppName=Visrtx Renderer for basic
AppVersion={#AppVersion}
AppPublisher=polar2251
AppPublisherURL=https://github.com/polar2251/visrtx-renderer-for-basic
DefaultDirName={localappdata}\Programs\Visrtx Renderer for basic
DefaultGroupName=Visrtx Renderer for basic
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=VisrtxRendererForBasic-Setup-x64
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\VisrtxRendererForBasic.exe
WizardStyle=modern

[Files]
Source: "..\dist\VisrtxRendererForBasic\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Visrtx Renderer for basic"; Filename: "{app}\VisrtxRendererForBasic.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\VisrtxRendererForBasic.exe"; Description: "Launch Visrtx Renderer for basic"; Flags: nowait postinstall skipifsilent
