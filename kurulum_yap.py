"""
Kurulum dosyası (setup) üretir.

Önce uygulamayı paketler, sonra Inno Setup ile kurulum dosyasına dönüştürür.

Kullanım:
    python kurulum_yap.py

Sonuç: dist\\TeknoparkDestekHesaplama_Kurulum.exe

Gereksinim: Inno Setup 6 — https://jrsoftware.org/isdl.php (bir kez kurulur)
"""

import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).parent.resolve()
BETIK = KOK / 'kurulum.iss'
EXE = KOK / 'dist' / 'TeknoparkDestekHesaplama.exe'
KURULUM = KOK / 'dist' / 'TeknoparkDestekHesaplama_Kurulum.exe'

ISCC_ADAYLARI = [
    Path(r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'),
    Path(r'C:\Program Files\Inno Setup 6\ISCC.exe'),
]


def iscc_bul():
    for yol in ISCC_ADAYLARI:
        if yol.exists():
            return yol
    sys.exit(
        "Inno Setup 6 bulunamadı.\n"
        "https://jrsoftware.org/isdl.php adresinden kurup tekrar deneyin."
    )


def main():
    iscc = iscc_bul()

    if not EXE.exists():
        print("Uygulama henüz paketlenmemiş, önce paketleniyor...\n")
        subprocess.run([sys.executable, str(KOK / 'paketle.py')], check=True, cwd=KOK)
        if not EXE.exists():
            sys.exit("Paketleme başarısız: .exe oluşmadı.")

    KURULUM.unlink(missing_ok=True)

    print("Kurulum dosyası üretiliyor...\n")
    sonuc = subprocess.run([str(iscc), str(BETIK)], cwd=KOK)
    if sonuc.returncode != 0 or not KURULUM.exists():
        sys.exit("\nKurulum dosyası üretilemedi.")

    print(f"\nTamamlandı: {KURULUM}")
    print(f"Boyut: {KURULUM.stat().st_size / 1024 / 1024:.1f} MB")
    print("\nBu dosyayı paylaşırken e-posta/WhatsApp yerine OneDrive veya")
    print("Teams bağlantısı kullanın; e-posta .exe dosyalarını engeller.")


if __name__ == '__main__':
    main()
