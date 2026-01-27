; Inno Setup Script for Bloc Fantome
; This script creates a Windows installer for the application
;
; Requirements:
; 1. Inno Setup 6.x installed (https://jrsoftware.org/isinfo.php)
; 2. Build the exe first: python build_exe.py
;
; To compile:
;   iscc installer.iss
;
; Or use Inno Setup Compiler GUI

#define MyAppName "Bloc Fantome"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Jeffrey Morais"
#define MyAppURL "https://github.com/IsolatedSingularity/Bloc-Fantome"
#define MyAppExeName "BlocFantome.exe"
#define MyAppAssocName "Bloc Fantome Structure"
#define MyAppAssocExt ".bsms"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A7B8C9D0-E1F2-3456-7890-ABCDEF123456}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output settings
OutputDir=build\installer
OutputBaseFilename=BlocFantome_Setup_{#MyAppVersion}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
; Visual settings
SetupIconFile=..\Assets\Icons\End_Stone.ico
WizardStyle=modern
WizardImageFile=compiler:WizModernImage.bmp
WizardSmallImageFile=compiler:WizModernSmallImage.bmp
; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Misc
DisableWelcomePage=no
DisableProgramGroupPage=yes
LicenseFile=..\References\LICENSE.txt
; File association (optional)
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable
Source: "build\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Configuration file
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; Assets folder (required)
Source: "..\Assets\Texture Hub\*"; DestDir: "{app}\Assets\Texture Hub"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\Assets\Sound Hub\*"; DestDir: "{app}\Assets\Sound Hub"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\Assets\Icons\*"; DestDir: "{app}\Assets\Icons"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\Assets\Fonts\*"; DestDir: "{app}\Assets\Fonts"; Flags: ignoreversion recursesubdirs createallsubdirs

; Optional: Extensive Library (comment out if not needed - saves space)
; Source: "..\Assets\Extensive Library\*"; DestDir: "{app}\Assets\Extensive Library"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create directories for user data
Name: "{app}\saves"
Name: "{app}\screenshots"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; File association (optional - for .bsms structure files)
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".bsms"; ValueData: ""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom code for additional installer logic

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Add any initialization checks here
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-install tasks
    // For example, migrate old settings
  end;
end;

// Check if another instance is running
function IsAppRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('tasklist', '/FI "IMAGENAME eq {#MyAppExeName}" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := (ResultCode = 0);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  // Could add checks here, e.g., close running instance
end;
