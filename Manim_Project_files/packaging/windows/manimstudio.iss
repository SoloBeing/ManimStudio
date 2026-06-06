; Inno Setup script for ManimStudio.
;
; Packages the PyInstaller --onedir bundle into a Windows installer (.exe) that
; installs to Program Files, adds Start Menu (and optional desktop) shortcuts,
; and registers a clean uninstaller in Add/Remove Programs. This mirrors the
; Linux .deb: a single source-of-truth artwork, an optional LaTeX notice, and
; user data left untouched on uninstall.
;
; Compile (Windows only; ISCC is part of Inno Setup):
;   ISCC.exe /DMyAppVersion=2.0.19 /DDistDir=..\..\dist manimstudio.iss
; The build_installer.ps1 wrapper handles versioning and locating ISCC.

#define MyAppName "Manim Studio"
#define MyAppExeName "ManimStudio.exe"
#define MyAppPublisher "Abhishek"
#define MyAppURL "https://github.com/SoloBeing/ManimStudio"

#ifndef MyAppVersion
  #define MyAppVersion "2.0.19"
#endif

; Directory containing the built "ManimStudio\" bundle. Relative paths are
; resolved against this .iss file's location.
#ifndef DistDir
  #define DistDir "..\..\dist"
#endif

[Setup]
; AppId uniquely identifies the app for upgrades/uninstall — never change it.
AppId={{2100ED55-64B2-4EE0-9B1B-F89B22AFEDF2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\ManimStudio
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir={#DistDir}
OutputBaseFilename=ManimStudio-Setup-{#MyAppVersion}
SetupIconFile=manimstudio.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 64-bit only (the PyInstaller bundle is x64).
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Per-machine install by default (mirrors the .deb's system-wide /opt); a
; non-admin user can still choose a per-user location at the privileges prompt.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The whole PyInstaller bundle (ManimStudio.exe + _internal\...).
Source: "{#DistDir}\ManimStudio\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Icon used for the shortcuts (the bundled exe carries the default icon).
Source: "manimstudio.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\manimstudio.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\manimstudio.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
{ Return True if a `latex` executable is on PATH. Mirrors the .deb postinst
  check so we can nudge the user toward MiKTeX when math rendering won't work. }
function IsLatexAvailable: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C where latex', '', SW_HIDE,
                 ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not WizardSilent) then
  begin
    if not IsLatexAvailable then
      MsgBox(
        'LaTeX was not detected on this PC.' #13#10 #13#10 +
        'MathTex/Tex and coordinate labels need a LaTeX distribution such as ' +
        'MiKTeX (https://miktex.org). Plain Text() animations work without it.' #13#10 #13#10 +
        'You can install LaTeX later — ManimStudio will prompt you when a ' +
        'render needs it.',
        mbInformation, MB_OK);
  end;
end;
