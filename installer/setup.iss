; 商工会議所メール配信システム（部会版） Inno Setup スクリプト
#ifndef AppVersion
#define AppVersion "0.0.0"
#endif

[Setup]
; 既存の議員用アプリと並べて導入できるよう、専用のAppIdとインストール先を持つ
AppId={{9F2A6C74-3B58-4E1D-9A0C-7D5B21E4C8F3}
AppName=商工会議所メール配信システム（部会版）
AppVersion={#AppVersion}
AppPublisher=mozu93
AppPublisherURL=https://github.com/mozu93/cci_mail_multi
AppSupportURL=https://github.com/mozu93/cci_mail_multi/issues
DefaultDirName={localappdata}\CCIMailMulti
DefaultGroupName=商工会議所メール配信システム（部会版）
DisableDirPage=yes
OutputDir={#SourcePath}\..\installer_output
OutputBaseFilename=CCIMailMulti_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加タスク:"

[Files]
Source: "{#SourcePath}\..\dist\CCIMailMulti\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\商工会議所メール配信システム（部会版）"; Filename: "{app}\CCIMailMulti.exe"
Name: "{group}\会を選んで起動"; Filename: "{app}\CCIMailMulti.exe"; Parameters: "--select-profile"
Name: "{group}\アンインストール"; Filename: "{uninstallexe}"
Name: "{autodesktop}\商工会議所メール配信システム（部会版）"; Filename: "{app}\CCIMailMulti.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CCIMailMulti.exe"; Description: "商工会議所メール配信システム（部会版）を起動する"; Flags: nowait postinstall skipifsilent
