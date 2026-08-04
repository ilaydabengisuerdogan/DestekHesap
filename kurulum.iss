; Teknopark Destek Hesaplama - Inno Setup kurulum betigi
;
; Uretmek icin:  python kurulum_yap.py
; Cikti:         dist\TeknoparkDestekHesaplama_Kurulum.exe
;
; Yonetici yetkisi GEREKTIRMEZ: uygulama kullanicinin kendi klasorune kurulur,
; boylece sirket bilgisayarlarinda yetki sorunu cikmaz.

#define Uygulama    "Teknopark Destek Hesaplama"
#define Surum       "1.0.0"
#define Yayimci     "Netas"
#define CalisanExe  "TeknoparkDestekHesaplama.exe"

[Setup]
AppId={{8C3F1A62-4D7B-4E19-9F5A-2B6E8D0C71A4}
AppName={#Uygulama}
AppVersion={#Surum}
AppVerName={#Uygulama} {#Surum}
AppPublisher={#Yayimci}
DefaultDirName={autopf}\TeknoparkDestekHesaplama
DefaultGroupName={#Uygulama}
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir=dist
OutputBaseFilename=TeknoparkDestekHesaplama_Kurulum
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Yonetici yetkisi istemeden, kullanici klasorune kur.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Windows 10 ve uzeri
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

UninstallDisplayName={#Uygulama}
UninstallDisplayIcon={app}\{#CalisanExe}

[Languages]
Name: "turkce"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaüstüne kısayol oluştur"; GroupDescription: "Ek kısayollar:"

[Files]
Source: "dist\{#CalisanExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "KULLANIM.txt";       DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#Uygulama}";           Filename: "{app}\{#CalisanExe}"
Name: "{group}\Kullanım Kılavuzu";     Filename: "{app}\KULLANIM.txt"
Name: "{group}\{#Uygulama} Kaldır";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Uygulama}";     Filename: "{app}\{#CalisanExe}"; Tasks: masaustu

[Run]
Filename: "{app}\{#CalisanExe}"; Description: "Uygulamayı şimdi başlat"; Flags: nowait postinstall skipifsilent
Filename: "{app}\KULLANIM.txt"; Description: "Kullanım kılavuzunu aç"; Flags: shellexec nowait postinstall skipifsilent unchecked
