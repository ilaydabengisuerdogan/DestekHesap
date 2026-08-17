"""
Teknopark destek gün/saat hesaplama kural motoru.

Girdi: İK'dan gelen aralık bazlı izin raporu Excel dosyası.
Çıktı: Personel bazında destek gün/saat ve kesinti kırılımı.

Bu modül Streamlit'ten bağımsızdır; arayüzsüz test edilebilir ve
CLI'dan da çağrılabilir (bkz. dosya sonundaki __main__ bloğu).
Kurallar tek yerde toplandığı için formül değişirse güncelleme tek noktadan yapılır.
"""

import calendar
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path

import pandas as pd

# Türkçe karakterleri sadeleştirir; kolon adlarını karşılaştırırken kullanılır.
TR_HARF_HARITASI = str.maketrans({
    'İ': 'i', 'I': 'i', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g',
    'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c',
})

# Başlık satırı aranırken taranacak satır sayısı (üstte logo/başlık bloğu olabilir).
BASLIK_ARAMA_DERINLIGI = 15

# --- Girdi şeması ---
# Personeli tanımlayan kolon. Dosyada çalışan numarası da ad soyad da olabilir;
# hangisi bulunursa o kullanılır ve çıktıda kendi adıyla yer alır.
KIMLIK_KOLONU = 'Personel'

KOLONLAR = [
    KIMLIK_KOLONU,
    'Şirket',
    'İzin Türü',
    'İzin Nedeni',
    'İzin Başlangıç Tarihi',
    'İzin Bitiş Tarihi',
]

# Süre kolonları zorunlu değildir. Dosyada yoksa izin tarihlerinden hesaplanır:
# aralıktaki hafta içi günler (resmi tatiller hariç) sayılır.
SURE_KOLONLARI = ['quantityInDays', 'quantityInHours']

# Zorunlu olmayan, bulunursa kurallarda kullanılan kolonlar.
ISE_BASLAMA_KOLONU = 'İşe Başlama Tarihi'
CIKIS_KOLONU = 'İşten Çıkış Tarihi'
ISTEGE_BAGLI_KOLONLAR = SURE_KOLONLARI + [ISE_BASLAMA_KOLONU, CIKIS_KOLONU]

# Yalnızca İşe Başlama Tarihi varsa doldurulabilen çıktı kolonları.
# Hiçbir personelde değer yoksa çıktıdan tamamen çıkarılır.
KIDEM_KOLONLARI = ['Kıdem Yılı', 'Risk']

# Çıktı Excel'inde kolon sırası. Baştaki kimlik ve bilgi kolonları (Ad Soyad,
# SGK vb.) dosyadaki adlarıyla geldiği için burada yer almaz; onlar en başta
# kalır. Listede olmayan kolonlar sona eklenir.
CIKTI_KOLON_SIRASI = [
    'Şirket',
    'İzin Türü', 'İzin Nedeni',
    'İzin Başlangıç Tarihi', 'İzin Bitiş Tarihi',
    ISE_BASLAMA_KOLONU, CIKIS_KOLONU,
    'Teşvik Gün Sayısı', 'Kıdem Yılı', 'Risk',
    # --- kesinti kırılımı ---
    'Dönem', 'Rapor Durumu', 'Rapor Türü',
    'Rapor Gün', 'Hafta Sonu Kesintisi', 'Yıllık İzin Kesintisi',
    'Resmi Tatiller', 'Resmi Tatil Kesintisi',
    'Kısmi Rapor Kesintisi', 'Ücretsiz İzin Kesintisi',
    'Toplam Kesinti', 'Teşvik Saat Sayısı',
    'Uyarı',
]

# Hesapta kullanılan ama çıktıda gösterilmeyen kolonlar. Teşvik tabanı tam ay
# çalışanda hep 30 çıktığı ve kısmi ayda değiştiği için tabloyu karıştırıyordu;
# bilgi zaten 'Uyarı' kolonunda veriliyor.
CIKTIDA_GIZLENEN = ['Teşvik Tabanı']

# Kimliğin hemen yanında durması istenen bilgi kolonları (normalize edilmiş
# adında bu ifadelerden biri geçenler). Diğer tanınmayan kolonlar sona gider.
KIMLIK_YANI_IFADELER = ['ad soyad', 'adi soyadi', 'isim', 'name']

# Kolon adı farklılıklarına tolerans. Birebir eşleşme bulunamazsa bu adlar
# denenir; büyük/küçük harf, Türkçe karakter ve noktalama farkları önemsizdir.
# Kimlik için önce numara alanları, bulunamazsa ad soyad alanları denenir.
KOLON_ESANLAMLILARI = {
    KIMLIK_KOLONU: ['Çalışan Numarası', 'Çalışan Sicil Numarası', 'Çalışan Sicil',
                    'Çalışan Sicil No', 'Sicil', 'Sicil No', 'Sicil Numarası',
                    'Personel No', 'Personel Sicil', 'Personel Numarası',
                    'Çalışan No', 'Employee Id', 'Employee Number',
                    'TC', 'TC Kimlik No',
                    'Ad Soyad', 'Adı Soyadı', 'Çalışan Adı Soyadı', 'Ad ve Soyad',
                    'İsim', 'Personel Adı', 'Çalışan Adı', 'Ad-Soyad',
                    'Full Name', 'Employee Name'],
    'Şirket': ['Firma', 'Şirket Adı', 'Company'],
    'İzin Türü': ['İzin Tipi', 'Devamsızlık Tipi', 'Leave Type'],
    'İzin Nedeni': ['İzin Neden', 'İzin Sebebi', 'Neden', 'Açıklama', 'Leave Reason'],
    'İzin Başlangıç Tarihi': ['Başlangıç Tarihi', 'Başlangıç', 'İlk Gün', 'Start Date'],
    'İzin Bitiş Tarihi': ['Bitiş Tarihi', 'Bitiş', 'Son Gün', 'End Date'],
    'quantityInDays': ['Süre/Gün', 'Süre Gün', 'Gün', 'Gün Sayısı',
                       'İzin Gün Sayısı', 'Days'],
    'quantityInHours': ['Süre/Saat', 'Süre Saat', 'Saat', 'Saat Sayısı',
                        'İzin Saat Sayısı', 'Hours'],
    # 'İzne/İşe Esas Tarihi': İK sisteminin çıktısında işe başlama tarihini taşıyor
    # (personel başına sabit, kıdem hesabının dayanağı). İK ile teyit edildi.
    ISE_BASLAMA_KOLONU: ['İzne Esas Tarihi', 'İşe Esas Tarihi', 'İşe Giriş Tarihi',
                         'İşe Başlangıç Tarihi', 'Giriş Tarihi',
                         'Start Of Employment', 'Hire Date'],
    # Personel ay içinde işten ayrıldıysa teşvik tabanı o güne kadar sayılır.
    CIKIS_KOLONU: ['Çıkış Tarihi', 'işten çıkış tarihi', 'Ayrılış Tarihi',
                   'İşten Ayrılış Tarihi', 'Termination Date', 'End Of Employment'],
}

# --- Kural sabitleri ---
RAPOR_IZIN_TURU = 'Şirket Dışında Olma Nedeni'
RAPOR_NEDENLERI = {'Hastalık Raporu', 'Kadın Doğum İstirahat Raporu'}

# Raporlu personelde teşvikten düşen izin türleri. Mazeret İzni (doktor
# randevusu, doğum günü izni vb.) ve Evlilik İzni buraya dahil değildir.
KESINTI_IZIN_TURLERI = {'Yıllık İzin'}

# Rapor durumundan bağımsız olarak her personelde düşen izin türleri.
# Ücretsiz izinde ücret ödenmediği ve SGK primi yatmadığı için o günlerde
# teşvikten yararlanılamaz (İK kural dokümanı, Kural 2).
HER_KOSULDA_KESINTI_TURLERI = {'Ücretsiz İzin'}

# Yıllık ücretli izin hakkı için gereken kıdem (İş Kanunu Madde 53), yıl olarak.
# Bir yılını doldurmamış personelin "Yıllık İzin" kaydı, aynı dönemde raporu
# olsa dahi teşvikten düşülmez; yasal olarak hak edilmemiş bir izindir.
YILLIK_IZIN_KIDEM_YIL = 1

TESVIK_TABAN_GUN = 30
GUNLUK_SAAT = 8
YARIM_GUN_SAAT = GUNLUK_SAAT / 2

# Yıllık izinde gün sayımı (İK kural dokümanı, Kural 3):
# Bir günde bu eşiğin üzerinde izin kullanılırsa o gün tam gün sayılır,
# altındaysa yarım gün sayılır. Yarım günler ay boyunca toplanıp yukarı
# yuvarlanır: 0,5 + 0,5 = 1 tam gün (iki ayrı tam gün değil).
YILLIK_IZIN_TAM_GUN_ESIGI_SAAT = 4.5

# Yıllık ücretli izin hakkı kademeleri (İş Kanunu Madde 53).
# (asgari kıdem yılı, hak edilen gün) — büyükten küçüğe denenir.
YILLIK_IZIN_HAK_KADEMELERI = [
    (15, 26),
    (5, 20),
    (1, 14),
    (0, 0),
]

# --- Resmi tatil takvimi ---------------------------------------------------
# Takvim üç katmandan oluşur:
#   1. Sabit tarihli tatiller — her yıl aynı gündedir, koddan üretilir.
#   2. Dini bayramlar — yıldan yıla kayar. Diyanet takvimiyle doğrulanmış yıllar
#      DOGRULANMIS_DINI_BAYRAMLAR'da tutulur; tanımlı olmayan yıllar için
#      aritmetik Hicri takvimden hesaplanır ve "doğrulanmamış" sayılır.
#   3. ayarlar.json — yukarıdakilerin hepsini ezebilir.
# Doğrulanmamış bir yıl için hesap yapılırsa arayüz uyarı gösterir; sessizce
# yanlış takvimle hesaplanmaz.

# (ay, gün) — her yıl sabit olan TAM GÜN resmi tatiller.
SABIT_TATILLER = [
    (1, 1),     # Yılbaşı
    (4, 23),    # Ulusal Egemenlik ve Çocuk Bayramı
    (5, 1),     # Emek ve Dayanışma Günü
    (5, 19),    # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    (7, 15),    # Demokrasi ve Millî Birlik Günü
    (8, 30),    # Zafer Bayramı
    (10, 29),   # Cumhuriyet Bayramı
]

# Sabit tarihli YARIM GÜN tatiller (arife). Kanunen öğleden sonra başlar.
SABIT_YARIM_TATILLER = [
    (10, 28),   # Cumhuriyet Bayramı Arifesi
]

# Dini bayram arifeleri de yarım gün sayılır (bayramın 1. gününden bir önceki gün).
ARIFE_YARIM_GUN = True

# Dini bayramların 1. günü (arife bir önceki gündür).
# Ramazan 3 gün + arife, Kurban 4 gün + arife sürer.
# Buraya yalnızca Diyanet takvimiyle KONTROL EDİLMİŞ yıllar yazılmalıdır.
DOGRULANMIS_DINI_BAYRAMLAR = {
    2026: {'ramazan': (3, 20), 'kurban': (5, 27)},
}

# Takvimin önceden hesaplanacağı yıl aralığı. Üst sınır bugüne göre kayar;
# sabit bir yıl yazılırsa o yıl geldiğinde takvim sessizce boşalır.
TAKVIM_ILK_YIL = 2020
TAKVIM_ILERI_YIL = 25          # bugünden kaç yıl ileriye kadar üretilsin


def takvim_son_yil():
    """Takvimin kapsayacağı son yıl (bugünden ileriye doğru kayar)."""
    return dt.date.today().year + TAKVIM_ILERI_YIL


class GirdiHatasi(Exception):
    """Girdi dosyası beklenen şemaya uymadığında fırlatılır."""


# --------------------------------------------------------------- takvim

def _hicri_gregoryen(hicri_yil, hicri_ay, hicri_gun):
    """
    Aritmetik (tabular) Hicri takvimden Gregoryen tarihe çevirir.

    Diyanet astronomik hesap kullandığı için bazı yıllarda 1 gün sapabilir;
    bu yüzden buradan üretilen tarihler "doğrulanmamış" sayılır.
    """
    gun_sayisi = (int((11 * hicri_yil + 3) / 30) + 354 * hicri_yil + 30 * hicri_ay
                  - int((hicri_ay - 1) / 2) + hicri_gun + 1948440 - 385)
    l = gun_sayisi + 68569
    n = int((4 * l) / 146097)
    l -= int((146097 * n + 3) / 4)
    i = int((4000 * (l + 1)) / 1461001)
    l = l - int((1461 * i) / 4) + 31
    j = int((80 * l) / 2447)
    g = l - int((2447 * j) / 80)
    l = int(j / 11)
    a = j + 2 - 12 * l
    y = 100 * (n - 49) + i + l
    return dt.date(y, a, g)


# Bayram adı -> resmi tatil gün sayısı (arife ayrıca eklenir).
BAYRAM_SURELERI = {'ramazan': 3, 'kurban': 4}


def _bayram_suresi(ad):
    """Ad 'ramazan2' gibi numaralı da olabilir; baştaki kelimeye bakılır."""
    for anahtar, sure in BAYRAM_SURELERI.items():
        if str(ad).lower().startswith(anahtar):
            return sure
    return 1


def _dini_bayram_baslangiclari(yil):
    """
    Verilen yıla düşen dini bayramların 1. günlerini döner.

    Bir Gregoryen yılda aynı bayram iki kez geçebilir (örn. 2033'te Ramazan
    Bayramı hem Ocak hem Aralık ayında), bu yüzden liste döner.

    Döner: ([(ad, date), ...], dogrulandi_mi)
    """
    elle = DOGRULANMIS_DINI_BAYRAMLAR.get(yil)
    if elle:
        return (sorted(((ad, dt.date(yil, *gun)) for ad, gun in elle.items()),
                       key=lambda x: x[1]), True)

    # Hicri yıl kabaca: (Gregoryen - 622) * 33 / 32
    yaklasik = int((yil - 622) * 33 / 32)
    bulunan = []
    for hicri_yil in range(yaklasik - 2, yaklasik + 3):
        for ad, (ay, gun) in (('ramazan', (10, 1)), ('kurban', (12, 10))):
            try:
                tarih = _hicri_gregoryen(hicri_yil, ay, gun)
            except (ValueError, OverflowError):
                continue
            if tarih.year == yil and (ad, tarih) not in bulunan:
                bulunan.append((ad, tarih))
    return (sorted(bulunan, key=lambda x: x[1]), False)


def resmi_tatiller_yil(yil, yarim_dahil=False):
    """
    Verilen yılın resmi tatilleri.

    yarim_dahil=False → (tam gün tatiller, dogrulandi_mi)
    yarim_dahil=True  → (tam gün tatiller, yarım gün tatiller, dogrulandi_mi)
    """
    tatiller = {dt.date(yil, ay, gun) for ay, gun in SABIT_TATILLER}
    yarimlar = {dt.date(yil, ay, gun) for ay, gun in SABIT_YARIM_TATILLER}

    bayramlar, dogrulandi = _dini_bayram_baslangiclari(yil)
    for ad, baslangic in bayramlar:
        for kayma in range(_bayram_suresi(ad)):
            tatiller.add(baslangic + dt.timedelta(days=kayma))
        arife = baslangic - dt.timedelta(days=1)
        (yarimlar if ARIFE_YARIM_GUN else tatiller).add(arife)

    yarimlar -= tatiller          # tam gün tatil, yarım günün önüne geçer
    if yarim_dahil:
        return tatiller, yarimlar, dogrulandi
    return tatiller, dogrulandi


def takvim_uret(ilk_yil=None, son_yil=None):
    """
    Yıl aralığı için tatilleri üretir.

    Döner: (tam gün tatiller, yarım gün tatiller)
    """
    ilk_yil = ilk_yil or TAKVIM_ILK_YIL
    son_yil = son_yil or takvim_son_yil()
    tam, yarim = set(), set()
    for yil in range(ilk_yil, son_yil + 1):
        t, y, _ = resmi_tatiller_yil(yil, yarim_dahil=True)
        tam |= t
        yarim |= y
    return tam, yarim


def takvim_dogrulandi_mi(yil):
    """Verilen yılın dini bayram tarihleri Diyanet takvimiyle teyit edildi mi?"""
    return yil in DOGRULANMIS_DINI_BAYRAMLAR


def takvim_uyarisi(donem):
    """
    Dönemin takvimi güvenilir mi? Değilse kullanıcıya gösterilecek metin döner.

    Doğrulanmamış bir yılın dini bayram tarihleri hesaplanmıştır; Diyanet'in
    ilan ettiği tarihten bir gün sapabilir.
    """
    yil = donem[0]
    if takvim_dogrulandi_mi(yil):
        return None
    bayramlar, _ = _dini_bayram_baslangiclari(yil)
    if not bayramlar:
        return (f"{yil} yılı için dini bayram tarihleri hesaplanamadı. "
                f"Resmi tatilleri elle kontrol edin.")
    ozet = " · ".join(f"{ad.capitalize()} Bayramı {tarih:%d.%m.%Y}"
                      for ad, tarih in bayramlar)
    return (f"{yil} yılının dini bayram tarihleri Diyanet takvimiyle "
            f"doğrulanmadı, hesaplanarak bulundu ({ozet}). Bir gün sapabilir; "
            f"dönem bu tarihlere denk geliyorsa kontrol edin.")


# ------------------------------------------------------------ ayar dosyası

AYAR_DOSYASI = 'ayarlar.json'

# Ayar dosyasından değiştirilebilen alanlar: {json anahtarı: modül değişkeni}
AYARLANABILIR = {
    'kolon_esanlamlilari': 'KOLON_ESANLAMLILARI',
    'rapor_izin_turu': 'RAPOR_IZIN_TURU',
    'rapor_nedenleri': 'RAPOR_NEDENLERI',
    'kesinti_izin_turleri': 'KESINTI_IZIN_TURLERI',
    'her_kosulda_kesinti_turleri': 'HER_KOSULDA_KESINTI_TURLERI',
    'tesvik_taban_gun': 'TESVIK_TABAN_GUN',
    'gunluk_saat': 'GUNLUK_SAAT',
    'yillik_izin_kidem_yil': 'YILLIK_IZIN_KIDEM_YIL',
    'yillik_izin_tam_gun_esigi_saat': 'YILLIK_IZIN_TAM_GUN_ESIGI_SAAT',
    'yillik_izin_hak_kademeleri': 'YILLIK_IZIN_HAK_KADEMELERI',
}

# Küme olarak tutulan alanlar (JSON'da liste gelir).
KUME_ALANLARI = {'RAPOR_NEDENLERI', 'KESINTI_IZIN_TURLERI', 'HER_KOSULDA_KESINTI_TURLERI'}

ayar_uyarisi = None   # ayar dosyası okunamazsa nedeni burada tutulur


def ayar_dosyasi_yolu():
    """
    Ayar dosyasının aranacağı yer.

    Paketlenmiş .exe'de dosyanın yanına, kaynaktan çalışırken proje klasörüne
    bakılır; böylece kural değişikliği için yeniden derleme gerekmez.
    """
    if getattr(sys, 'frozen', False):
        kok = Path(sys.executable).parent
    else:
        kok = Path(__file__).parent
    return kok / AYAR_DOSYASI


def _esanlamlilari_birlestir(gomulu, dosyadan):
    """
    Gömülü kolon eşanlamlılarıyla ayar dosyasındakileri birleştirir.

    Gömülü liste önce gelir (öncelik sırası korunur), ardından ayar
    dosyasındaki fazladan adlar eklenir. Böylece kullanıcı yeni ad
    tanımlayabilir ama programa sonradan eklenen adları kaybetmez.
    """
    birlesik = {ad: list(liste) for ad, liste in gomulu.items()}
    for ad, liste in (dosyadan or {}).items():
        mevcut = birlesik.setdefault(ad, [])
        for esanlamli in liste:
            if esanlamli not in mevcut:
                mevcut.append(esanlamli)
    return birlesik


def ayarlari_yukle(yol=None):
    """
    Varsa ayar dosyasını okuyup modül sabitlerinin üzerine yazar.

    Dosya yoksa gömülü varsayılanlar kullanılır — bu normal durumdur.
    Dosya bozuksa varsayılanlara dönülür ve `ayar_uyarisi` doldurulur;
    sessizce yanlış kuralla hesaplamaktansa durumu görünür kılmak için.
    """
    global ayar_uyarisi, RESMI_TATILLER
    ayar_uyarisi = None
    yol = Path(yol) if yol else ayar_dosyasi_yolu()
    if not yol.exists():
        return False

    try:
        # utf-8-sig: Not Defteri gibi editörler dosyayı BOM ile kaydedebilir;
        # BOM'lu dosya düz utf-8 ile okunduğunda ayarlar sessizce yok sayılırdı.
        with open(yol, encoding='utf-8-sig') as dosya:
            ayarlar = json.load(dosya)
    except Exception as hata:
        ayar_uyarisi = f"{yol.name} okunamadı, gömülü kurallar kullanılıyor: {hata}"
        return False

    hatali = []
    for anahtar, degisken in AYARLANABILIR.items():
        if anahtar not in ayarlar:
            continue
        deger = ayarlar[anahtar]
        if degisken in KUME_ALANLARI:
            deger = set(deger)
        elif degisken == 'YILLIK_IZIN_HAK_KADEMELERI':
            deger = [tuple(k) for k in deger]
        elif degisken == 'KOLON_ESANLAMLILARI':
            # Kolon tanıma listesi EZİLMEZ, birleştirilir. Aksi halde eski bir
            # ayar dosyası, programa sonradan eklenen kolon adlarını görünmez
            # kılar ve dosya tanınmıyormuş gibi davranır.
            deger = _esanlamlilari_birlestir(KOLON_ESANLAMLILARI, deger)
        globals()[degisken] = deger

    # Diyanet takviminden teyit edilmiş dini bayram tarihleri.
    # Biçim: {"2027": {"ramazan": "10.03.2027", "kurban": "17.05.2027"}}
    if 'dogrulanmis_dini_bayramlar' in ayarlar:
        global DOGRULANMIS_DINI_BAYRAMLAR
        cozulen = {}
        for yil, bayramlar in ayarlar['dogrulanmis_dini_bayramlar'].items():
            for ad, metin in bayramlar.items():
                try:
                    tarih = dt.datetime.strptime(str(metin), '%d.%m.%Y').date()
                    cozulen.setdefault(int(yil), {})[ad] = (tarih.month, tarih.day)
                except ValueError:
                    hatali.append(f"{yil} {ad}: {metin}")
        if cozulen:
            global YARIM_GUN_TATILLER
            DOGRULANMIS_DINI_BAYRAMLAR = cozulen
            RESMI_TATILLER, YARIM_GUN_TATILLER = takvim_uret()

    # Açık tatil listesi verilmişse üretilen takvimin yerine geçer.
    if 'resmi_tatiller' in ayarlar:
        tatiller = set()
        for metin in ayarlar['resmi_tatiller']:
            try:
                tatiller.add(dt.datetime.strptime(str(metin), '%d.%m.%Y').date())
            except ValueError:
                hatali.append(str(metin))
        if tatiller:
            RESMI_TATILLER = tatiller

    if hatali:
        ayar_uyarisi = (f"{yol.name}: tarih olarak okunamayan resmi tatil girdileri "
                        f"yok sayıldı ({', '.join(hatali)})")
    return True


def dini_bayramlari_kaydet(yil, ramazan, kurban, yol=None):
    """
    Bir yılın dini bayram tarihlerini ayar dosyasına yazar ve takvimi yeniler.

    ramazan / kurban: bayramın 1. günü (date). Arife ve kalan günler otomatik
    eklenir. Kaydedilen yıl "doğrulanmış" sayılır, uyarı gösterilmez.
    None verilirse o bayram takvimden hesaplanmaya devam eder.
    """
    global DOGRULANMIS_DINI_BAYRAMLAR, RESMI_TATILLER, YARIM_GUN_TATILLER
    yol = Path(yol) if yol else ayar_dosyasi_yolu()

    mevcut = {}
    if yol.exists():
        try:
            with open(yol, encoding='utf-8-sig') as dosya:
                mevcut = json.load(dosya)
        except Exception:
            mevcut = {}

    bayramlar = {}
    for ad, tarih in (('ramazan', ramazan), ('kurban', kurban)):
        if tarih is not None:
            bayramlar[ad] = f"{tarih:%d.%m.%Y}"

    kayitli = mevcut.get('dogrulanmis_dini_bayramlar') or {}
    if bayramlar:
        kayitli[str(yil)] = bayramlar
    else:
        kayitli.pop(str(yil), None)
    mevcut['dogrulanmis_dini_bayramlar'] = kayitli

    with open(yol, 'w', encoding='utf-8') as dosya:
        json.dump(mevcut, dosya, ensure_ascii=False, indent=2)

    # Bellekteki takvimi de güncelle
    DOGRULANMIS_DINI_BAYRAMLAR = {
        int(y): {ad: tuple(int(p) for p in reversed(t.split('.')[:2]))
                 for ad, t in b.items()}
        for y, b in kayitli.items()
    }
    RESMI_TATILLER, YARIM_GUN_TATILLER = takvim_uret()
    return yol


def ayarlari_disa_aktar(yol=None):
    """Yürürlükteki kuralları düzenlenebilir bir ayar dosyası olarak yazar."""
    yol = Path(yol) if yol else ayar_dosyasi_yolu()
    ayarlar = {
        '_aciklama': 'Bu dosyayı düzenleyerek kuralları yeniden derlemeden '
                     'değiştirebilirsiniz. Silerseniz gömülü varsayılanlar kullanılır.',
        '_dini_bayram_notu': 'Sabit tarihli tatiller (1 Ocak, 23 Nisan, 15 Temmuz vb.) '
                             'her yıl otomatik üretilir, buraya yazmaya gerek yoktur. '
                             'Dini bayramlar kayar: Diyanet takviminden teyit ettiğiniz '
                             'yılı aşağıya ekleyin. Eklenmeyen yıllar hesaplanır ve '
                             'programda "doğrulanmadı" uyarısı gösterilir. '
                             'Takvimi tamamen elle yönetmek isterseniz "resmi_tatiller" '
                             'anahtarını gg.aa.yyyy listesi olarak ekleyin.',
        'dogrulanmis_dini_bayramlar': {
            str(yil): {ad: f"{gun[1]:02d}.{gun[0]:02d}.{yil}"
                       for ad, gun in bayramlar.items()}
            for yil, bayramlar in sorted(DOGRULANMIS_DINI_BAYRAMLAR.items())
        },
        'kolon_esanlamlilari': KOLON_ESANLAMLILARI,
        'rapor_izin_turu': RAPOR_IZIN_TURU,
        'rapor_nedenleri': sorted(RAPOR_NEDENLERI),
        'kesinti_izin_turleri': sorted(KESINTI_IZIN_TURLERI),
        'her_kosulda_kesinti_turleri': sorted(HER_KOSULDA_KESINTI_TURLERI),
        'tesvik_taban_gun': TESVIK_TABAN_GUN,
        'gunluk_saat': GUNLUK_SAAT,
        'yillik_izin_kidem_yil': YILLIK_IZIN_KIDEM_YIL,
        'yillik_izin_tam_gun_esigi_saat': YILLIK_IZIN_TAM_GUN_ESIGI_SAAT,
        'yillik_izin_hak_kademeleri': [list(k) for k in YILLIK_IZIN_HAK_KADEMELERI],
    }
    with open(yol, 'w', encoding='utf-8') as dosya:
        json.dump(ayarlar, dosya, ensure_ascii=False, indent=2)
    return yol


# Sabit tatiller ve dini bayramlardan yıl aralığı için takvim üretilir.
# RESMI_TATILLER: tam gün tatiller · YARIM_GUN_TATILLER: arife günleri
RESMI_TATILLER, YARIM_GUN_TATILLER = takvim_uret()

# Varsa ayar dosyasındaki kurallar gömülü varsayılanların üzerine yazılır.
ayarlari_yukle()


# ---------------------------------------------------------------- yardımcılar

def gun_araligi(baslangic, bitis):
    """baslangic ve bitis dahil olmak üzere tarihleri üretir."""
    gun = baslangic
    while gun <= bitis:
        yield gun
        gun += dt.timedelta(days=1)


def is_gunu(gun, tatiller):
    """Hafta içi ve tam gün resmi tatil değilse iş günüdür (arife dahildir)."""
    return gun.weekday() < 5 and gun not in tatiller


def gun_agirligi(gun, tatiller, yarim_tatiller=None):
    """
    Günün kaç iş günü değerinde olduğunu döner.

    1.0 normal iş günü · 0.5 arife (yarım gün) · 0.0 hafta sonu veya tam tatil
    """
    if not is_gunu(gun, tatiller):
        return 0.0
    if yarim_tatiller and gun in yarim_tatiller:
        return 0.5
    return 1.0


def gun_toplami(gunler, tatiller, yarim_tatiller=None):
    """Gün kümesinin iş günü karşılığı (arifeler yarım sayılır)."""
    return sum(gun_agirligi(g, tatiller, yarim_tatiller) for g in gunler)


def hafta_basi(gun):
    """Günün ait olduğu haftanın Pazartesi'si."""
    return gun - dt.timedelta(days=gun.weekday())


def donem_sinirlari(donem):
    """(yıl, ay) ikilisini ayın ilk ve son tarihine çevirir."""
    yil, ay = donem
    return dt.date(yil, ay, 1), dt.date(yil, ay, calendar.monthrange(yil, ay)[1])


def _yil_takvimi(yil, tatiller=None, yarim_tatiller=None):
    """
    Bir yılın tatilleri. Açıkça küme verilmediyse o yıl için üretilir.

    Önceden hesaplanmış kümeye güvenmek yerine yılı doğrudan üretmek,
    takvim aralığının dışına çıkıldığında sessizce "hiç tatil yok"
    durumuna düşmeyi engeller.
    """
    if tatiller is None and yarim_tatiller is None:
        tam, yarim, _ = resmi_tatiller_yil(yil, yarim_dahil=True)
        return tam, yarim
    return (set(tatiller or ()), set(yarim_tatiller or ()))


def donem_tatilleri(donem, tatiller=None):
    """Dönem ayına düşen TAM GÜN resmi tatilleri sıralı liste olarak döner."""
    ilk, son = donem_sinirlari(donem)
    kaynak = _yil_takvimi(donem[0], tatiller)[0] if tatiller is None else tatiller
    return sorted(g for g in kaynak if ilk <= g <= son)


YARIM_ETIKETI = 'yarım'


def donem_tatil_listesi(donem, tatiller=None, yarim_tatiller=None):
    """
    Dönemin tüm tatillerini yarım gün bilgisiyle birlikte döner.

    Döner: [(tarih, yarim_mi), ...] — tarihe göre sıralı.
    Arayüzdeki tatil kutusu bunu kullanır; arife günleri de görünsün diye.
    """
    ilk, son = donem_sinirlari(donem)
    tam, yarim = _yil_takvimi(donem[0], tatiller, yarim_tatiller)
    liste = [(g, False) for g in tam if ilk <= g <= son]
    liste += [(g, True) for g in yarim if ilk <= g <= son and g not in tam]
    return sorted(liste)


def tatil_listesi_metni(liste):
    """Tatil listesini kullanıcıya gösterilecek metne çevirir."""
    return ", ".join(f"{g:%d.%m.%Y}" + (f" ({YARIM_ETIKETI})" if y else "")
                     for g, y in liste)


def tatil_listesi_coz(metin):
    """
    Kullanıcının yazdığı tatil metnini çözer.

    '15.07.2026, 28.10.2026 (yarım)' → ({15.07}, {28.10}, [])
    Döner: (tam gün kümesi, yarım gün kümesi, okunamayan girdiler)
    """
    tam, yarim, hatali = set(), set(), []
    for parca in (metin or '').split(','):
        parca = parca.strip()
        if not parca:
            continue
        yarim_mi = _normalize_baslik(YARIM_ETIKETI) in _normalize_baslik(parca)
        tarih_metni = re.sub(r'\(.*?\)', '', parca).strip()
        try:
            tarih = dt.datetime.strptime(tarih_metni, '%d.%m.%Y').date()
        except ValueError:
            hatali.append(parca)
            continue
        (yarim if yarim_mi else tam).add(tarih)
    return tam, yarim - tam, hatali


def kismi_gun_kesintisi(toplam_saat):
    """
    Kısmi izin saatlerini gün kaybına çevirir.

    Eksik saat yarım günün altındaysa yarım gün, fazlaysa tam gün kaybettirir.
    Aylık birikimli uygulanır: 8 saatin katları tam gün, artan kısım yuvarlanır.
    """
    toplam_saat = round(toplam_saat, 6)
    if toplam_saat <= 0:
        return 0.0
    tam_gun, kalan = divmod(toplam_saat, GUNLUK_SAAT)
    if kalan == 0:
        ek = 0.0
    elif kalan <= YARIM_GUN_SAAT:
        ek = 0.5
    else:
        ek = 1.0
    return float(tam_gun) + ek


def kidem_yili(ise_baslama, tarih):
    """İşe başlama tarihinden verilen tarihe kadar tamamlanmış yıl sayısı."""
    if ise_baslama is None or pd.isna(ise_baslama):
        return None
    if hasattr(ise_baslama, 'date'):
        ise_baslama = ise_baslama.date()
    yil = tarih.year - ise_baslama.year
    if (tarih.month, tarih.day) < (ise_baslama.month, ise_baslama.day):
        yil -= 1
    return max(0, yil)


def yillik_izin_hakki(kidem):
    """Kıdeme göre yıllık ücretli izin hakkı, gün (İş Kanunu Madde 53)."""
    if kidem is None:
        return None
    for asgari, gun in YILLIK_IZIN_HAK_KADEMELERI:
        if kidem >= asgari:
            return gun
    return 0


def yillik_izin_kismi_kesintisi(toplam_gun):
    """
    Yıllık izindeki yarım günlerin toplamını tam güne yuvarlar (Kural 3).

    0,5 -> 1 gün · 0,5 + 0,5 -> 1 gün (iki ayrı tam gün değil) · 1,5 -> 2 gün
    """
    toplam_gun = round(toplam_gun, 6)
    if toplam_gun <= 0:
        return 0
    return math.ceil(toplam_gun)


def tatil_notu(baslangic, bitis, tatiller, yarim_tatiller=None):
    """
    Aralıktaki resmi tatilleri, kesintiye girip girmediklerini belirterek listeler.

    Bilgi amaçlıdır; hesabı değiştirmez. Kesintiye girmeyen tatiller de
    görünsün diye hafta sonuna denk gelenler de yazılır ve nedeni belirtilir.
    """
    yarim_tatiller = yarim_tatiller or set()
    notlar = []
    for gun in gun_araligi(baslangic, bitis):
        if gun in tatiller:
            etiket = " (hafta sonu — sayılmadı)" if gun.weekday() >= 5 else ""
        elif gun in yarim_tatiller:
            etiket = (" (arife, hafta sonu — sayılmadı)" if gun.weekday() >= 5
                      else " (arife — yarım gün)")
        else:
            continue
        notlar.append(f"{gun:%d.%m.%Y}{etiket}")
    return ", ".join(notlar)


def deger_esit(deger, hedef):
    """
    İki metni büyük/küçük harf ve Türkçe karakter farkını yok sayarak karşılaştırır.

    'YILLIK İZİN', 'Yıllık İzin' ve 'yillik izin' aynı sayılır; böylece İK
    sistemi yazımı değiştirdiğinde kural sessizce çalışmayı bırakmaz.
    """
    return _normalize_baslik(deger) == _normalize_baslik(hedef)


def deger_iceriyor(deger, hedefler):
    """Metin, verilen kümedeki değerlerden biriyle eşleşiyor mu? (harf duyarsız)"""
    normalize = _normalize_baslik(deger)
    return any(normalize == _normalize_baslik(h) for h in hedefler)


def rapor_mu(satir):
    """
    Satır hastalık raporu ya da doğum istirahati mi?

    Belirleyici alan İzin Nedeni'dir. İzin Türü boş bırakılmış olabilir
    (İK dosyalarında görüldü); bu durumda yalnızca nedene bakılır.
    Tür dolu ama farklı bir değerse çelişkili veri sayılır ve rapor kabul
    edilmez — tutarsizlik_notu() bunu uyarı olarak bildirir.
    """
    if not deger_iceriyor(satir['İzin Nedeni'], RAPOR_NEDENLERI):
        return False
    turu = str(satir['İzin Türü'] or '').strip()
    return not turu or deger_esit(turu, RAPOR_IZIN_TURU)


def celiskili_rapor_mu(satir):
    """İzin Nedeni rapor diyor ama İzin Türü başka bir şey mi?"""
    if not deger_iceriyor(satir['İzin Nedeni'], RAPOR_NEDENLERI):
        return False
    turu = str(satir['İzin Türü'] or '').strip()
    return bool(turu) and not deger_esit(turu, RAPOR_IZIN_TURU)


# ------------------------------------------------------------------- okuma

def _normalize_baslik(metin):
    """Kolon adını karşılaştırılabilir hale getirir (Türkçe karakter, harf, boşluk)."""
    metin = str(metin).translate(TR_HARF_HARITASI).lower()
    return re.sub(r'[^a-z0-9]+', ' ', metin).strip()


def _kolonlari_esle(basliklar):
    """
    Dosyadaki başlıkları beklenen kolon adlarına eşler.

    Önce birebir, sonra eşanlamlı adlar denenir. Eşanlamlı listesinin sırası
    önceliği belirler: kimlik için önce çalışan numarası alanları, bulunamazsa
    ad soyad alanları seçilir.
    Döner: {dosyadaki_baslik: beklenen_kolon}
    """
    normalize = {b: _normalize_baslik(b) for b in basliklar}
    eslesme = {}
    kullanilan = set()

    # 1. tur: beklenen adın kendisiyle birebir eşleşme
    for beklenen in KOLONLAR + ISTEGE_BAGLI_KOLONLAR:
        hedef = _normalize_baslik(beklenen)
        for baslik, norm in normalize.items():
            if baslik not in kullanilan and norm == hedef:
                eslesme[baslik] = beklenen
                kullanilan.add(baslik)
                break

    # 2. tur: eşanlamlı adlar
    for beklenen, esanlamlilar in KOLON_ESANLAMLILARI.items():
        if beklenen in eslesme.values():
            continue
        for esanlamli in esanlamlilar:
            hedef = _normalize_baslik(esanlamli)
            bulundu = next((b for b, n in normalize.items()
                            if b not in kullanilan and n == hedef), None)
            if bulundu:
                eslesme[bulundu] = beklenen
                kullanilan.add(bulundu)
                break

    return eslesme


def _sayfa_ve_baslik_bul(kaynak):
    """
    Çok sayfalı dosyada veri sayfasını ve başlık satırını bulur.

    Her sayfanın ilk BASLIK_ARAMA_DERINLIGI satırı taranır; beklenen
    kolonlardan en çoğunu içeren satır başlık kabul edilir. Böylece
    "Kurallar", "Açıklama" gibi yardımcı sayfalar atlanır.
    Döner: (sayfa_adi, baslik_satir_no)
    """
    sayfalar = pd.read_excel(kaynak, header=None, nrows=BASLIK_ARAMA_DERINLIGI,
                             sheet_name=None)
    en_iyi = (None, 0, -1)  # (sayfa, satir, skor)
    for sayfa_adi, ham in sayfalar.items():
        for i in range(len(ham)):
            basliklar = [h for h in ham.iloc[i].tolist() if pd.notna(h)]
            skor = len(set(_kolonlari_esle(basliklar).values()))
            if skor > en_iyi[2]:
                en_iyi = (sayfa_adi, i, skor)
    return en_iyi[0], en_iyi[1]


def kolonlari_incele(kaynak):
    """
    Dosyayı okumadan önce kolon yapısını çıkarır.

    Arayüz, eksik kolon varsa kullanıcıya eşleştirme ekranı gösterebilsin diye
    kullanılır. Döner: (dosyadaki_basliklar, otomatik_eslesme, eksik_kolonlar)
    """
    def _geri_sar():
        if hasattr(kaynak, 'seek'):
            kaynak.seek(0)

    try:
        _geri_sar()
        sayfa, baslik_satiri = _sayfa_ve_baslik_bul(kaynak)
        _geri_sar()
        df = pd.read_excel(kaynak, header=baslik_satiri, sheet_name=sayfa, nrows=5)
    except Exception as hata:
        raise GirdiHatasi(f"Excel dosyası okunamadı: {hata}") from hata

    basliklar = [str(k) for k in df.columns if not str(k).startswith('Unnamed:')]
    eslesme = _kolonlari_esle(basliklar)
    eksik = [k for k in KOLONLAR if k not in eslesme.values()]
    return basliklar, eslesme, eksik


def oku(kaynak, elle_eslesme=None):
    """
    İzin raporu Excel'ini okur, doğrular ve normalize eder.

    kaynak: dosya yolu veya dosya benzeri nesne (Streamlit upload).
    elle_eslesme: {dosyadaki_baslik: beklenen_kolon} — otomatik tanınmayan
                  kolonlar için kullanıcının yaptığı eşleştirme.

    Kolon adlarında büyük/küçük harf, Türkçe karakter ve yaygın eşanlamlı
    farkları tolere edilir. Personel kimliği olarak çalışan numarası ya da
    ad soyad kabul edilir. Beklenenlerin dışındaki kolonlar korunur ve
    çıktıya taşınır.
    """
    def _geri_sar():
        if hasattr(kaynak, 'seek'):
            kaynak.seek(0)

    try:
        _geri_sar()
        sayfa, baslik_satiri = _sayfa_ve_baslik_bul(kaynak)
        _geri_sar()
        df = pd.read_excel(kaynak, header=baslik_satiri, sheet_name=sayfa)
    except Exception as hata:
        raise GirdiHatasi(f"Excel dosyası okunamadı: {hata}") from hata

    # Adsız/boş kolonları at, başlıklardaki fazla boşluğu temizle.
    df = df.loc[:, [k for k in df.columns if not str(k).startswith('Unnamed:')]]
    df = df.rename(columns={k: str(k).strip() for k in df.columns})
    eslesme = _kolonlari_esle(df.columns)
    if elle_eslesme:
        # Kullanıcının eşleştirmesi otomatik tanımanın önüne geçer.
        ezilen = set(elle_eslesme.values())
        eslesme = {k: v for k, v in eslesme.items() if v not in ezilen}
        eslesme.update({k: v for k, v in elle_eslesme.items() if k in df.columns})

    # Kimlik kolonunun dosyadaki özgün adı çıktıda korunur (Ad Soyad, Sicil No...).
    kimlik_ozgun_ad = next((k for k, v in eslesme.items() if v == KIMLIK_KOLONU), None)
    df = df.rename(columns=eslesme)

    eksik = [k for k in KOLONLAR if k not in df.columns]
    if eksik:
        gorunen = [KIMLIK_KOLONU + " (çalışan numarası veya ad soyad)"
                   if k == KIMLIK_KOLONU else k for k in eksik]
        raise GirdiHatasi(
            "Yüklenen dosyada şu kolonlar bulunamadı: " + ", ".join(gorunen)
            + ".\n\nDosyada bulunanlar: " + ", ".join(str(k) for k in df.columns)
        )

    # Beklenen kolonlar önce, tanınmayan ek kolonlar (kimlik bilgileri) sonra.
    istege_bagli = [k for k in ISTEGE_BAGLI_KOLONLAR if k in df.columns]
    ek_kolonlar = [k for k in df.columns
                   if k not in KOLONLAR and k not in istege_bagli]
    df = df[KOLONLAR + istege_bagli + ek_kolonlar].copy()

    # dayfirst=True: metin tarihler Türkçe gg.aa.yyyy biçiminde gelir.
    # Bu olmadan '05.08.2026' sessizce 8 Mayıs olarak okunur; '28.08.2026'
    # gibi ayrık olmayanlar doğru okunduğu için hata fark edilmez.
    tarih_kolonlari = ['İzin Başlangıç Tarihi', 'İzin Bitiş Tarihi'] + istege_bagli
    for kolon in tarih_kolonlari:
        if kolon in SURE_KOLONLARI:
            continue
        df[kolon] = pd.to_datetime(df[kolon], errors='coerce', dayfirst=True)

    df['İzin Türü'] = df['İzin Türü'].fillna('').astype(str).str.strip()
    df['İzin Nedeni'] = df['İzin Nedeni'].fillna('').astype(str).str.strip()
    df['Şirket'] = df['Şirket'].fillna('').astype(str).str.strip()

    # Süre kolonları dosyada yoksa izin tarihlerinden hesaplanır (hesapla()
    # içinde, yürürlükteki resmi tatil takvimiyle).
    sure_hesaplanacak = [k for k in SURE_KOLONLARI if k not in df.columns]
    for kolon in SURE_KOLONLARI:
        if kolon in df.columns:
            df[kolon] = pd.to_numeric(df[kolon], errors='coerce').fillna(0.0)

    # Kimliği ya da tarihi olmayan satırlar hesaba alınamaz.
    df = df.dropna(subset=[KIMLIK_KOLONU, 'İzin Başlangıç Tarihi', 'İzin Bitiş Tarihi'])
    if df.empty:
        raise GirdiHatasi("Dosyada işlenebilir veri satırı bulunamadı.")

    # Bitiş başlangıçtan önceyse tek günlük kayıt olarak ele al.
    ters = df['İzin Bitiş Tarihi'] < df['İzin Başlangıç Tarihi']
    df.loc[ters, 'İzin Bitiş Tarihi'] = df.loc[ters, 'İzin Başlangıç Tarihi']

    df = df.drop_duplicates()
    df = df.reset_index(drop=True)
    df.attrs['kimlik_ad'] = kimlik_ozgun_ad or KIMLIK_KOLONU
    df.attrs['sure_hesaplanacak'] = sure_hesaplanacak
    return df


def sureleri_hesapla(df, tatiller, yarim_tatiller=None):
    """
    Süre kolonları dosyada yoksa izin tarihlerinden üretir.

    Gün sayısı = aralıktaki iş günleri (tam tatiller hariç, arifeler yarım),
    saat = gün × günlük çalışma saati.

    Not: Tarihlerden saatlik izin ayırt edilemez; her kayıt tam gün sayılır.
    Dosyada süre kolonu varsa bu fonksiyon hiçbir şey yapmaz.
    """
    # attrs bazı pandas işlemlerinde kaybolabildiği için kolonun gerçekten
    # var olup olmadığına da bakılır; aksi halde hesap sırasında çökme olur.
    eksik = [k for k in (df.attrs.get('sure_hesaplanacak') or SURE_KOLONLARI)
             if k not in df.columns]
    if not eksik:
        return df

    df = df.copy()
    gunler = df.apply(
        lambda s: gun_toplami(
            gun_araligi(s['İzin Başlangıç Tarihi'].date(),
                        s['İzin Bitiş Tarihi'].date()),
            tatiller, yarim_tatiller),
        axis=1,
    ).astype(float)

    if 'quantityInDays' in eksik:
        df['quantityInDays'] = gunler
    if 'quantityInHours' in eksik:
        df['quantityInHours'] = df['quantityInDays'] * GUNLUK_SAAT
    return df


def donem_tespit(df):
    """İzin başlangıç tarihlerinin en sık görüldüğü (yıl, ay) ikilisini döner."""
    donemler = df['İzin Başlangıç Tarihi'].dt.to_period('M')
    en_sik = donemler.mode()
    secilen = en_sik.iloc[0] if not en_sik.empty else donemler.min()
    return int(secilen.year), int(secilen.month)


# ---------------------------------------------------------------- hesaplama

def tutarlilik_uyarisi(satir, tatiller, yarim_tatiller=None):
    """
    Dosyadaki quantityInDays ile hesaplanan iş günü sayısını karşılaştırır.

    Sapma genellikle resmi tatil takviminin eksik/fazla olduğunu gösterir.
    Arife günleri yarım sayıldığı için 0,5'lik farklar da anlamlıdır.
    Saatlik izinlerde (1 günden az) kontrol edilmez.
    """
    gun_sayisi = satir['quantityInDays']
    if gun_sayisi < 1:
        return None

    baslangic = satir['İzin Başlangıç Tarihi'].date()
    bitis = satir['İzin Bitiş Tarihi'].date()
    hesaplanan = gun_toplami(gun_araligi(baslangic, bitis), tatiller, yarim_tatiller)
    if hesaplanan == gun_sayisi:
        return None

    mesaj = (f"{baslangic:%d.%m.%Y}-{bitis:%d.%m.%Y} aralığı: dosyada "
             f"{gun_sayisi:g} gün, tatil takvimine göre {hesaplanan:g} gün")

    # Fark tam olarak arife günlerinden geliyorsa sebebi açıkça söyle; kullanıcı
    # "neden 0,5 fark var" diye aramasın.
    araliktaki_arifeler = sorted(
        g for g in (yarim_tatiller or ())
        if baslangic <= g <= bitis and g.weekday() < 5 and g not in tatiller
    )
    if araliktaki_arifeler and hesaplanan - gun_sayisi == 0.5 * len(araliktaki_arifeler):
        tarihler = ", ".join(f"{g:%d.%m.%Y}" for g in araliktaki_arifeler)
        return (mesaj + f". BEKLENEN FARK: {tarihler} arife günleri kural gereği "
                        f"yarım gün sayılır, dosyayı üreten sistem tam gün saymış. "
                        f"İşlem yapmanız gerekmez")

    return mesaj + " (resmi tatil listesi kontrol edilmeli)"


def _ek_kolon_degeri(satirlar, kolon):
    """
    Ek (kimlik) kolonunun personel için tek değerini döner.

    Değer personel içinde sabitse aynen; satırdan satıra değişiyorsa
    tüm farklı değerler ' / ' ile birleştirilir — sessizce yanlış tek bir
    değer göstermek yerine durum görünür kalsın.
    """
    ham = satirlar[kolon].dropna()
    if pd.api.types.is_datetime64_any_dtype(ham):
        # Tarihler saat kısmı olmadan, gg.aa.yyyy biçiminde okunsun.
        degerler = ham.dt.strftime('%d.%m.%Y').tolist()
    else:
        degerler = ham.astype(str).str.strip().tolist()
    degerler = [d for d in dict.fromkeys(degerler) if d]
    if not degerler:
        return ''
    if len(degerler) == 1:
        return degerler[0]
    return ' / '.join(degerler)[:200]


def calisma_araligi(donem, ise_baslama=None, cikis=None):
    """
    Personelin dönem içinde şirkette bulunduğu tarih aralığını döner.

    İşe başlama ayın içindeyse aralık o günden, işten çıkış ayın içindeyse
    o güne kadar sürer. Her ikisi de ay dışındaysa tüm ay döner.
    Aralık hiç oluşmuyorsa (örn. çıkış aydan önce) None döner.
    """
    donem_ilk, donem_son = donem_sinirlari(donem)
    baslangic, bitis = donem_ilk, donem_son

    for tarih, ref in ((ise_baslama, 'giris'), (cikis, 'cikis')):
        if tarih is None or pd.isna(tarih):
            continue
        if hasattr(tarih, 'date'):
            tarih = tarih.date()
        if ref == 'giris':
            baslangic = max(baslangic, tarih)
        else:
            bitis = min(bitis, tarih)

    return (baslangic, bitis) if baslangic <= bitis else None


def tesvik_tabani(donem, ise_baslama=None, cikis=None):
    """
    Personelin bu dönemde kaç gün üzerinden teşvik alacağını döner.

    Tam ay çalışan personelde taban sabit 30 gündür (SGK'nın yaklaşımı;
    ayın 28 veya 31 gün olması sonucu değiştirmez). Ay içinde işe giren
    veya işten çıkan personelde şirkette bulunduğu gün sayısı kullanılır.
    """
    aralik = calisma_araligi(donem, ise_baslama, cikis)
    if aralik is None:
        return 0
    donem_ilk, donem_son = donem_sinirlari(donem)
    if aralik == (donem_ilk, donem_son):
        return TESVIK_TABAN_GUN                     # tam ay
    gun = (aralik[1] - aralik[0]).days + 1          # her iki uç dahil
    return min(TESVIK_TABAN_GUN, gun)


def kidem_yeterli_mi(ise_baslama, izin_baslangic):
    """
    Yıllık ücretli izin hakkı için kıdem yeterli mi? (İş Kanunu Madde 53)

    ise_baslama: işe başlama tarihi (None ise kural uygulanamaz, True döner)
    Bir yılını doldurmamış personelin yıllık izni hak edilmemiş sayılır.

    Gün sayısı yerine takvim yıldönümü karşılaştırılır; artık yıllarda gün
    hesabı bir gün kaydığı için sınır tarihlerde yanlış sonuç verirdi.
    """
    if ise_baslama is None or pd.isna(ise_baslama):
        return True  # bilgi yoksa kural uygulanamaz
    if hasattr(ise_baslama, 'date'):
        ise_baslama = ise_baslama.date()

    hedef_yil = ise_baslama.year + YILLIK_IZIN_KIDEM_YIL
    try:
        yildonumu = ise_baslama.replace(year=hedef_yil)
    except ValueError:  # 29 Şubat'ta işe başlayıp artık olmayan yıl
        yildonumu = ise_baslama.replace(year=hedef_yil, day=28)
    return izin_baslangic >= yildonumu


def hesapla_personel(satirlar, donem, tatiller, ek_kolonlar=(), kimlik_ad=None,
                     yarim_tatiller=None):
    """
    Tek personelin dönem içi destek gün/saatini ve kesinti kırılımını hesaplar.

    satirlar: personele ait izin satırları (DataFrame).
    ek_kolonlar: girdide bulunan, çıktıya taşınacak bilgi kolonları
                 (Sicil No, Departman, İşe Başlama Tarihi vb.).
    kimlik_ad:  kimlik kolonunun çıktıda kullanılacak adı (Ad Soyad, Sicil No...).

    Ücretsiz izin her personelde düşer. Yıllık izin ve resmi tatil yalnızca
    raporlu personelde düşer; yıllık izinde ayrıca kıdem şartı aranır.
    """
    ay_ilk, ay_son = donem_sinirlari(donem)
    yarim_tatiller = set(yarim_tatiller or ())

    def _ilk_deger(kolon):
        if kolon not in satirlar.columns:
            return None
        gecerli = satirlar[kolon].dropna()
        return gecerli.iloc[0] if not gecerli.empty else None

    ise_baslama = _ilk_deger(ISE_BASLAMA_KOLONU)
    cikis = _ilk_deger(CIKIS_KOLONU)

    # Personel ay içinde işe girdiyse/çıktıysa hem teşvik tabanı hem de
    # kesintilerin sayılacağı aralık şirkette bulunduğu güne göre daralır.
    taban = tesvik_tabani(donem, ise_baslama, cikis)
    aralik = calisma_araligi(donem, ise_baslama, cikis)
    donem_ilk, donem_son = aralik if aralik else (ay_ilk, ay_ilk - dt.timedelta(days=1))

    uyarilar = []
    rapor_satirlari, diger_satirlar = [], []
    for _, satir in satirlar.iterrows():
        uyari = tutarlilik_uyarisi(satir, tatiller, yarim_tatiller)
        if uyari:
            uyarilar.append(uyari)
        if celiskili_rapor_mu(satir):
            uyarilar.append(
                f"'{satir['İzin Nedeni']}' rapor gibi görünüyor ama İzin Türü "
                f"'{satir['İzin Türü']}' yazıyor; rapor sayılmadı, kontrol edin")

        baslangic = max(satir['İzin Başlangıç Tarihi'].date(), donem_ilk)
        bitis = min(satir['İzin Bitiş Tarihi'].date(), donem_son)
        if baslangic > bitis:
            continue  # izin tamamen dönem dışında
        (rapor_satirlari if rapor_mu(satir) else diger_satirlar).append(
            (satir, baslangic, bitis)
        )

    # Kıdem, dönemin ilk gününe göre hesaplanır (İş Kanunu Md. 53 kademeleri).
    kidem = kidem_yili(ise_baslama, donem_ilk)
    hak = yillik_izin_hakki(kidem)
    yillik_izinli_mi = any(deger_iceriyor(s['İzin Türü'], KESINTI_IZIN_TURLERI)
                           for s, _, _ in diger_satirlar)

    def _birlestir(degerler):
        """Personelin birden çok izni varsa değerleri okunur biçimde birleştirir."""
        tekil = [d for d in dict.fromkeys(degerler) if d]
        return ", ".join(tekil)[:250]

    sonuc = {(kimlik_ad or KIMLIK_KOLONU): satirlar[KIMLIK_KOLONU].iloc[0]}
    # Bilgi kolonları (Ad Soyad, SGK, Departman vb.) kimliğin hemen yanında.
    for kolon in ek_kolonlar:
        sonuc[kolon] = _ek_kolon_degeri(satirlar, kolon)
    sonuc.update({
        'Şirket': satirlar['Şirket'].iloc[0],
        # İzin bilgileri personel başına birleştirilir; başlangıç ve bitiş
        # tarihleri aynı sırada yazılır, böylece karşılıklı okunabilir.
        'İzin Türü': _birlestir(satirlar['İzin Türü']),
        'İzin Nedeni': _birlestir(satirlar['İzin Nedeni']),
        'İzin Başlangıç Tarihi': _birlestir(
            satirlar['İzin Başlangıç Tarihi'].dt.strftime('%d.%m.%Y')),
        'İzin Bitiş Tarihi': _birlestir(
            satirlar['İzin Bitiş Tarihi'].dt.strftime('%d.%m.%Y')),
        'Dönem': f"{donem[0]}-{donem[1]:02d}",
        'Kıdem Yılı': '' if kidem is None else kidem,
        # 1 yılını doldurmamış personelin yıllık izin kaydı yasal olarak hak
        # edilmemiştir; İK'nın gözden geçirmesi için işaretlenir.
        'Risk': 'Riskli' if (kidem is not None and kidem < 1 and yillik_izinli_mi) else '',
        'Rapor Durumu': 'Raporlu' if rapor_satirlari else 'Raporsuz',
        'Rapor Türü': ', '.join(sorted({s['İzin Nedeni'] for s, _, _ in rapor_satirlari})),
        'Rapor Gün': 0.0,
        'Hafta Sonu Kesintisi': 0.0,
        'Yıllık İzin Kesintisi': 0.0,
        # Bilgi amaçlı: dönemdeki tatiller, kesintiye girmeseler de görünür.
        'Resmi Tatiller': (tatil_notu(donem_ilk, donem_son, tatiller, yarim_tatiller)
                           if aralik else ''),
        'Resmi Tatil Kesintisi': 0.0,
        'Kısmi Rapor Kesintisi': 0.0,
        'Ücretsiz İzin Kesintisi': 0.0,
        'Teşvik Tabanı': float(taban),
        'Toplam Kesinti': 0.0,
        'Teşvik Gün Sayısı': float(taban),
        'Teşvik Saat Sayısı': float(taban * GUNLUK_SAAT),
        'Uyarı': '',
    })

    if taban < TESVIK_TABAN_GUN:
        uyarilar.append(
            f"Personel dönemin tamamında çalışmadığı için teşvik {taban} gün "
            f"üzerinden hesaplandı ({donem_ilk:%d.%m}-{donem_son:%d.%m})"
            if aralik else
            f"Personel bu dönemde çalışmıyor, teşvik hesaplanmadı"
        )

    # (0) Ücretsiz izin: ücret ödenmediği ve SGK primi yatmadığı için rapor
    # durumundan bağımsız olarak her personelde düşer.
    ucretsiz_gunleri = set()
    for satir, baslangic, bitis in diger_satirlar:
        if not deger_iceriyor(satir['İzin Türü'], HER_KOSULDA_KESINTI_TURLERI):
            continue
        for gun in gun_araligi(baslangic, bitis):
            if is_gunu(gun, tatiller):
                ucretsiz_gunleri.add(gun)

    if not rapor_satirlari:
        # Raporu olmayan personelde yıllık izin ve resmi tatil düşmez.
        toplam = gun_toplami(ucretsiz_gunleri, tatiller, yarim_tatiller)
        destek = max(0.0, taban - toplam)
        sonuc.update({
            'Ücretsiz İzin Kesintisi': toplam,
            'Toplam Kesinti': toplam,
            'Teşvik Gün Sayısı': destek,
            'Teşvik Saat Sayısı': destek * GUNLUK_SAAT,
            'Uyarı': ' | '.join(uyarilar),
        })
        return sonuc

    # (a) Rapor günleri: dönem içindeki iş günleri. Saatlik rapor tam gün
    # kaybettirmez, kısmi gün havuzuna gider; ancak haftalık çalışma saati yine
    # tamamlanmadığı için o haftanın hafta sonu her durumda düşer.
    rapor_gunleri = set()
    rapor_haftalari = set()
    kismi_saat = 0.0
    for satir, baslangic, bitis in rapor_satirlari:
        tam_gun_mu = satir['quantityInDays'] >= 1
        for gun in gun_araligi(baslangic, bitis):
            if tam_gun_mu and is_gunu(gun, tatiller):
                rapor_gunleri.add(gun)
            rapor_haftalari.add(hafta_basi(gun))
        if not tam_gun_mu:
            kismi_saat += satir['quantityInHours']

    # (b) Raporun değdiği her haftanın hafta sonu; yalnızca dönem ayına düşen
    # günler sayılır. Ay sonu haftasının hafta sonu bir sonraki aya taşıyorsa
    # bu dönemden düşmez (örn. 27-31 Temmuz haftasının 1-2 Ağustos'u).
    hafta_sonlari = set()
    for pazartesi in rapor_haftalari:
        for kayma in (5, 6):
            gun = pazartesi + dt.timedelta(days=kayma)
            if donem_ilk <= gun <= donem_son:
                hafta_sonlari.add(gun)

    # (c) Yıllık izin günleri. Mazeret ve evlilik izni düşmez. Bir yılını
    # doldurmamış personelin yıllık izni hak edilmemiş sayıldığı için düşmez.
    # Tam gün kayıtları takvime, yarım günler ayrı havuza gider: yarım günler
    # ay boyunca toplanıp yukarı yuvarlanır (Kural 3).
    izin_gunleri = set()
    yarim_gun_toplami = 0.0
    kidemsiz_atlanan = 0
    for satir, baslangic, bitis in diger_satirlar:
        if not deger_iceriyor(satir['İzin Türü'], KESINTI_IZIN_TURLERI):
            continue
        if not kidem_yeterli_mi(ise_baslama, satir['İzin Başlangıç Tarihi'].date()):
            kidemsiz_atlanan += 1
            continue
        if satir['quantityInDays'] < 1:
            # Eşiğin üzerindeki kısmi izin tam gün, altındaki yarım gün sayılır.
            yarim_gun_toplami += (
                1.0 if satir['quantityInHours'] > YILLIK_IZIN_TAM_GUN_ESIGI_SAAT else 0.5
            )
            continue
        for gun in gun_araligi(baslangic, bitis):
            if is_gunu(gun, tatiller):
                izin_gunleri.add(gun)

    if kidemsiz_atlanan:
        uyarilar.append(
            f"{kidemsiz_atlanan} yıllık izin kaydı, 1 yıllık kıdem şartı "
            f"dolmadığı için kesintiye dahil edilmedi (İş Kanunu Md. 53)"
        )

    # Aynı gün birden çok kategoride işaretlenmiş olabilir; mükerrer saymamak
    # için rapor günleri kazanır. Hafta sonları Cmt-Paz olduğu için ayrıktır.
    izin_gunleri -= rapor_gunleri
    ucretsiz_gunleri -= rapor_gunleri | izin_gunleri

    # (d) Dönem içindeki hafta içine denk gelen resmi tatiller. Tam gün tatiller
    # tanımı gereği izin/rapor kümelerine giremez; arife ise yarım iş günü
    # olduğundan girebilir, o yüzden çıkarılır.
    tam_tatil_gunleri = {
        g for g in gun_araligi(donem_ilk, donem_son)
        if g in tatiller and g.weekday() < 5
    }
    arife_gunleri = {
        g for g in gun_araligi(donem_ilk, donem_son)
        if g in yarim_tatiller and g.weekday() < 5 and g not in tatiller
    } - (rapor_gunleri | izin_gunleri | ucretsiz_gunleri)
    resmi_tatil_kesintisi = len(tam_tatil_gunleri) + 0.5 * len(arife_gunleri)

    # Arifeye denk gelen izin/rapor günleri yarım sayılır.
    rapor_kesintisi = gun_toplami(rapor_gunleri, tatiller, yarim_tatiller)
    ucretsiz_kesintisi = gun_toplami(ucretsiz_gunleri, tatiller, yarim_tatiller)
    kismi_kesinti = kismi_gun_kesintisi(kismi_saat)
    yillik_kesinti = (gun_toplami(izin_gunleri, tatiller, yarim_tatiller)
                      + yillik_izin_kismi_kesintisi(yarim_gun_toplami))

    toplam_kesinti = (
        rapor_kesintisi + len(hafta_sonlari) + yillik_kesinti
        + resmi_tatil_kesintisi + ucretsiz_kesintisi + kismi_kesinti
    )
    destek_gun = max(0.0, taban - toplam_kesinti)

    sonuc.update({
        'Rapor Gün': float(rapor_kesintisi),
        'Hafta Sonu Kesintisi': float(len(hafta_sonlari)),
        'Yıllık İzin Kesintisi': float(yillik_kesinti),
        'Resmi Tatil Kesintisi': float(resmi_tatil_kesintisi),
        'Kısmi Rapor Kesintisi': kismi_kesinti,
        'Ücretsiz İzin Kesintisi': float(ucretsiz_kesintisi),
        'Toplam Kesinti': float(toplam_kesinti),
        'Teşvik Gün Sayısı': destek_gun,
        'Teşvik Saat Sayısı': destek_gun * GUNLUK_SAAT,
        'Uyarı': ' | '.join(uyarilar),
    })
    return sonuc


def hesapla(df, donem=None, tatiller=None, yarim_tatiller=None):
    """
    Tüm personel için destek gün/saat tablosunu üretir.

    donem: (yıl, ay); verilmezse veriden tespit edilir.
    tatiller: tam gün resmi tatiller; verilmezse RESMI_TATILLER kullanılır.
    yarim_tatiller: arife günleri (yarım gün); verilmezse YARIM_GUN_TATILLER.
    """
    if donem is None:
        donem = donem_tespit(df)
    # Takvim verilmediyse dönemin yılı doğrudan üretilir; önceden hesaplanan
    # aralığın dışına çıkıldığında sessizce tatilsiz hesaplamamak için.
    # Kullanıcı açıkça takvim verdiyse (arayüzden düzenlemişse) ona dokunulmaz.
    if tatiller is None and yarim_tatiller is None:
        tatiller, yarim_tatiller = _yil_takvimi(donem[0])
        tatiller = set(tatiller) | set(RESMI_TATILLER)
        yarim_tatiller = set(yarim_tatiller) | set(YARIM_GUN_TATILLER)
    else:
        tatiller = set(RESMI_TATILLER if tatiller is None else tatiller)
        yarim_tatiller = set(
            YARIM_GUN_TATILLER if yarim_tatiller is None else yarim_tatiller)
    yarim_tatiller -= tatiller

    # Süre kolonları dosyada yoksa tarihlerden üretilir.
    sure_hesaplandi = bool(df.attrs.get('sure_hesaplanacak'))
    kimlik_ad = df.attrs.get('kimlik_ad', KIMLIK_KOLONU)
    df = sureleri_hesapla(df, tatiller, yarim_tatiller)

    # Girdideki tanınmayan kolonlar bilgi kolonu kabul edilip çıktıya taşınır.
    ek_kolonlar = [k for k in df.columns
                   if k not in KOLONLAR and k not in SURE_KOLONLARI]

    sonuclar = [
        hesapla_personel(satirlar, donem, tatiller, ek_kolonlar, kimlik_ad,
                         yarim_tatiller)
        for _, satirlar in df.groupby(KIMLIK_KOLONU, sort=True)
    ]
    sonuc_df = pd.DataFrame(sonuclar)

    # Kıdeme bağlı kolonlar yalnızca İşe Başlama Tarihi varsa anlamlıdır.
    # Hiçbir personelde kıdem bilgisi yoksa üçü birlikte kaldırılır; kıdem
    # biliniyorsa boş 'Risk' de anlamlıdır ("riskli kayıt yok") ve kalır.
    kidem_kolonu = KIDEM_KOLONLARI[0]
    if kidem_kolonu in sonuc_df.columns and (sonuc_df[kidem_kolonu] == '').all():
        sonuc_df = sonuc_df.drop(columns=[k for k in KIDEM_KOLONLARI
                                          if k in sonuc_df.columns])

    sonuc_df = sonuc_df.drop(columns=[k for k in CIKTIDA_GIZLENEN
                                      if k in sonuc_df.columns])
    sonuc_df = sonuc_df[_kolonlari_sirala(sonuc_df.columns)]
    sonuc_df.attrs['sure_hesaplandi'] = sure_hesaplandi
    return sonuc_df


def _kolonlari_sirala(kolonlar):
    """
    Çıktı kolonlarını istenen sıraya dizer.

    Kimlik ve bilgi kolonları (Ad Soyad, SGK vb.) dosyadaki adlarıyla geldiği
    için CIKTI_KOLON_SIRASI'nda yer almaz; onlar baştaki sıralarını korur.
    """
    kolonlar = list(kolonlar)
    bilinen = [k for k in CIKTI_KOLON_SIRASI if k in kolonlar]
    taninmayan = [k for k in kolonlar if k not in bilinen]

    # Kimlik kolonu (ilk sıradaki) ve ad soyad gibi tanımlayıcı bilgiler başta.
    bastakiler = taninmayan[:1]
    for kolon in taninmayan[1:]:
        norm = _normalize_baslik(kolon)
        if any(ifade in norm for ifade in KIMLIK_YANI_IFADELER):
            bastakiler.append(kolon)

    kalan = [k for k in taninmayan if k not in bastakiler]
    return bastakiler + bilinen + kalan


def kesintili_personel(sonuc_df):
    """Teşvikten kesinti yapılan personeli döner (kesintisi 0 olanlar hariç)."""
    return sonuc_df[sonuc_df['Toplam Kesinti'] > 0].reset_index(drop=True)


def kesintili_dosya_yolu(yol):
    """Ana çıktının yanına yazılacak kesintili personel dosyasının yolu."""
    kok, uzanti = os.path.splitext(str(yol))
    return f"{kok}_kesintili{uzanti or '.xlsx'}"


def excel_yaz(sonuc_df, hedef, sayfa_adi='Destek_Sonuclari'):
    """Sonuç tablosunu biçimlendirilmiş bir Excel dosyasına/tamponuna yazar."""
    with pd.ExcelWriter(hedef, engine='openpyxl') as writer:
        sonuc_df.to_excel(writer, index=False, sheet_name=sayfa_adi)
        sayfa = writer.sheets[sayfa_adi]
        for sutun in sayfa.columns:
            harf = sutun[0].column_letter
            genislik = max(len(str(h.value)) if h.value is not None else 0 for h in sutun)
            sayfa.column_dimensions[harf].width = min(max(genislik + 2, 12), 60)
    return hedef


def excel_yaz_ikili(sonuc_df, yol):
    """
    İki Excel dosyası yazar ve yollarını döner:
      1. Ana dosya  — tüm personel
      2. '_kesintili' dosyası — yalnızca kesintisi olan personel

    Kesintisi olan personel yoksa ikinci dosya oluşturulmaz (None döner).
    """
    excel_yaz(sonuc_df, yol)
    kesintililer = kesintili_personel(sonuc_df)
    if kesintililer.empty:
        return str(yol), None
    kesintili_yol = kesintili_dosya_yolu(yol)
    excel_yaz(kesintililer, kesintili_yol, sayfa_adi='Kesintili_Personel')
    return str(yol), kesintili_yol


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Kullanım: python hesaplama.py <girdi.xlsx> [cikti.xlsx]")
        raise SystemExit(1)

    girdi = sys.argv[1]
    cikti = sys.argv[2] if len(sys.argv) > 2 else 'teknopark_destek_sonuclari.xlsx'

    veri = oku(girdi)
    secilen_donem = donem_tespit(veri)
    sonuc = hesapla(veri, secilen_donem)
    ana_yol, kesintili_yol = excel_yaz_ikili(sonuc, cikti)

    raporlu = (sonuc['Rapor Durumu'] == 'Raporlu').sum()
    print(f"Dönem: {secilen_donem[0]}-{secilen_donem[1]:02d}")
    print(f"Personel: {len(sonuc)} | Raporlu: {raporlu}")
    print(f"Toplam destek günü: {sonuc['Teşvik Gün Sayısı'].sum():g}")
    print(f"Çıktı (tüm personel): {ana_yol}")
    if kesintili_yol:
        print(f"Çıktı (kesintili personel): {kesintili_yol}")
