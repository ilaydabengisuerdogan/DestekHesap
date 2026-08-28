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
import zipfile
from pathlib import Path

KOK = Path(__file__).parent.resolve()
BETIK = KOK / 'kurulum.iss'
EXE = KOK / 'dist' / 'TeknoparkDestekHesaplama.exe'
KURULUM = KOK / 'dist' / 'TeknoparkDestekHesaplama_Kurulum.exe'

# .exe bunlardan biri değiştiğinde yeniden paketlenmelidir.
KAYNAKLAR = ['hesaplama.py', 'masaustu.py', 'paketle.py']

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


def exe_guncel_mi():
    """Paketlenmiş .exe, kaynak dosyalardan daha yeni mi?"""
    if not EXE.exists():
        return False
    exe_zamani = EXE.stat().st_mtime
    return all((KOK / ad).stat().st_mtime <= exe_zamani
               for ad in KAYNAKLAR if (KOK / ad).exists())


def zip_uret():
    """
    Kurulum dosyasını kullanım kılavuzuyla birlikte zipler.

    Zip elle üretildiğinde kurulum güncellenip zip eski kalıyordu; her
    derlemede birlikte üretilsin diye buraya alındı.
    """
    zip_yolu = KURULUM.with_suffix('.zip')
    zip_yolu.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_yolu, 'w', zipfile.ZIP_DEFLATED) as paket:
        paket.write(KURULUM, KURULUM.name)
        kilavuz = KOK / 'KULLANIM.txt'
        if kilavuz.exists():
            paket.write(kilavuz, kilavuz.name)
    return zip_yolu


def main():
    iscc = iscc_bul()

    if not exe_guncel_mi():
        neden = "henüz paketlenmemiş" if not EXE.exists() else "kaynak kod değişmiş"
        print(f"Uygulama {neden}, önce paketleniyor...\n")
        subprocess.run([sys.executable, str(KOK / 'paketle.py')], check=True, cwd=KOK)
        if not EXE.exists():
            sys.exit("Paketleme başarısız: .exe oluşmadı.")
    else:
        print("Paketlenmiş .exe güncel, doğrudan kurulum dosyası üretiliyor.\n")

    # Kural dosyası gömülü varsayılanlardan üretilip kurulumla birlikte gider;
    # böylece kurallar yeniden derlemeden düzenlenebilir.
    sys.path.insert(0, str(KOK))
    import hesaplama
    hesaplama.ayarlari_disa_aktar(KOK / 'dist' / 'ayarlar.json')
    print("Kural dosyası üretildi: dist/ayarlar.json\n")

    KURULUM.unlink(missing_ok=True)

    print("Kurulum dosyası üretiliyor...\n")
    sonuc = subprocess.run([str(iscc), str(BETIK)], cwd=KOK)
    if sonuc.returncode != 0 or not KURULUM.exists():
        sys.exit("\nKurulum dosyası üretilemedi.")

    zip_yolu = zip_uret()

    print(f"\nTamamlandı: {KURULUM}")
    print(f"Boyut: {KURULUM.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"Zip:   {zip_yolu.name} ({zip_yolu.stat().st_size / 1024 / 1024:.1f} MB)")
    print("\nBu dosyayı paylaşırken e-posta/WhatsApp yerine OneDrive veya")
    print("Teams bağlantısı kullanın; e-posta .exe dosyalarını engeller.")


if __name__ == '__main__':
    main()
