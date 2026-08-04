"""
Uygulamayı tek dosya .exe olarak paketler.

Kullanım:
    python -m pip install pyinstaller     (bir kez, internet gerekir)
    python paketle.py

Sonuç: dist\\TeknoparkDestekHesaplama.exe
Bu dosya hedef bilgisayarda Python kurulumu ve internet bağlantısı gerektirmez.
"""

import shutil
import sys
from pathlib import Path

UYGULAMA_ADI = "TeknoparkDestekHesaplama"
KOK = Path(__file__).parent.resolve()

# Pakete girmesine gerek olmayan, boyutu şişiren modüller.
HARIC = [
    'streamlit', 'pytest', 'matplotlib', 'IPython', 'jupyter', 'notebook',
    'PIL', 'PyQt5', 'PySide2', 'tornado', 'altair', 'pyarrow', 'scipy',
    'sqlalchemy', 'numpy.f2py', 'pandas.tests', 'numpy.testing',
]

# PyInstaller'ın statik analizle yakalayamadığı, çalışma anında yüklenen modüller.
GIZLI = [
    'openpyxl.cell._writer',
    'pandas._libs.tslibs.base',
]


def main():
    try:
        import PyInstaller.__main__
    except ImportError:
        sys.exit("PyInstaller kurulu değil.\nÇalıştırın: python -m pip install pyinstaller")

    for klasor in ('build', 'dist'):
        shutil.rmtree(KOK / klasor, ignore_errors=True)
    spec = KOK / f"{UYGULAMA_ADI}.spec"
    spec.unlink(missing_ok=True)

    argumanlar = [
        str(KOK / 'masaustu.py'),
        '--name', UYGULAMA_ADI,
        '--onefile',      # tek dosya
        '--windowed',     # konsol penceresi açma
        '--noconfirm',
        '--clean',
        '--distpath', str(KOK / 'dist'),
        '--workpath', str(KOK / 'build'),
        '--specpath', str(KOK),
        '--paths', str(KOK),
    ]
    for ad in HARIC:
        argumanlar += ['--exclude-module', ad]
    for ad in GIZLI:
        argumanlar += ['--hidden-import', ad]

    ikon = KOK / 'ikon.ico'
    if ikon.exists():
        argumanlar += ['--icon', str(ikon)]

    print("Paketleniyor, bu birkaç dakika sürebilir...\n")
    PyInstaller.__main__.run(argumanlar)

    exe = KOK / 'dist' / f"{UYGULAMA_ADI}.exe"
    if not exe.exists():
        sys.exit("\nPaketleme başarısız: .exe oluşmadı.")
    print(f"\nTamamlandı: {exe}")
    print(f"Boyut: {exe.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
