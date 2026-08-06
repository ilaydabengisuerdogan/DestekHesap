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
    'quantityInDays',
    'quantityInHours',
]

# Zorunlu olmayan, bulunursa kurallarda kullanılan kolonlar.
ISE_BASLAMA_KOLONU = 'İşe Başlama Tarihi'
ISTEGE_BAGLI_KOLONLAR = [ISE_BASLAMA_KOLONU]

# Kolon adı farklılıklarına tolerans. Birebir eşleşme bulunamazsa bu adlar
# denenir; büyük/küçük harf, Türkçe karakter ve noktalama farkları önemsizdir.
# Kimlik için önce numara alanları, bulunamazsa ad soyad alanları denenir.
KOLON_ESANLAMLILARI = {
    KIMLIK_KOLONU: ['Çalışan Numarası', 'Sicil No', 'Sicil Numarası', 'Personel No',
                    'Personel Numarası', 'Çalışan No', 'Employee Id', 'Employee Number',
                    'TC', 'TC Kimlik No',
                    'Ad Soyad', 'Adı Soyadı', 'Ad ve Soyad', 'İsim', 'Personel Adı',
                    'Çalışan Adı', 'Ad-Soyad', 'Full Name', 'Employee Name'],
    'Şirket': ['Firma', 'Şirket Adı', 'Company'],
    'İzin Türü': ['İzin Tipi', 'Devamsızlık Tipi', 'Leave Type'],
    'İzin Nedeni': ['İzin Sebebi', 'Neden', 'Açıklama', 'Leave Reason'],
    'İzin Başlangıç Tarihi': ['Başlangıç Tarihi', 'Başlangıç', 'İlk Gün', 'Start Date'],
    'İzin Bitiş Tarihi': ['Bitiş Tarihi', 'Bitiş', 'Son Gün', 'End Date'],
    'quantityInDays': ['Gün', 'Gün Sayısı', 'İzin Gün Sayısı', 'Days'],
    'quantityInHours': ['Saat', 'Saat Sayısı', 'İzin Saat Sayısı', 'Hours'],
    ISE_BASLAMA_KOLONU: ['İşe Giriş Tarihi', 'İşe Başlangıç Tarihi', 'Giriş Tarihi',
                         'Start Of Employment', 'Hire Date'],
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

# (ay, gün) — her yıl sabit olan resmi tatiller. Arife günleri, İK sisteminin
# davranışına uygun olarak tam gün tatil sayılır (Temmuz 2026 verisinden doğrulandı).
SABIT_TATILLER = [
    (1, 1),     # Yılbaşı
    (4, 23),    # Ulusal Egemenlik ve Çocuk Bayramı
    (5, 1),     # Emek ve Dayanışma Günü
    (5, 19),    # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    (7, 15),    # Demokrasi ve Millî Birlik Günü
    (8, 30),    # Zafer Bayramı
    (10, 28),   # Cumhuriyet Bayramı Arifesi
    (10, 29),   # Cumhuriyet Bayramı
]

# Dini bayramların 1. günü (arife bir önceki gündür).
# Ramazan 3 gün + arife, Kurban 4 gün + arife sürer.
# Buraya yalnızca Diyanet takvimiyle KONTROL EDİLMİŞ yıllar yazılmalıdır.
DOGRULANMIS_DINI_BAYRAMLAR = {
    2026: {'ramazan': (3, 20), 'kurban': (5, 27)},
}

# Takvimin önceden hesaplanacağı yıl aralığı.
TAKVIM_ILK_YIL = 2020
TAKVIM_SON_YIL = 2040


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


def resmi_tatiller_yil(yil):
    """Verilen yılın tüm resmi tatilleri. Döner: (tarih kümesi, dogrulandi_mi)."""
    tatiller = {dt.date(yil, ay, gun) for ay, gun in SABIT_TATILLER}

    bayramlar, dogrulandi = _dini_bayram_baslangiclari(yil)
    for ad, baslangic in bayramlar:
        # Arife (-1) dahil, bayramın tüm günleri
        for kayma in range(-1, _bayram_suresi(ad)):
            tatiller.add(baslangic + dt.timedelta(days=kayma))

    return tatiller, dogrulandi


def takvim_uret(ilk_yil=None, son_yil=None):
    """Yıl aralığı için tüm resmi tatilleri tek kümede toplar."""
    ilk_yil = ilk_yil or TAKVIM_ILK_YIL
    son_yil = son_yil or TAKVIM_SON_YIL
    tatiller = set()
    for yil in range(ilk_yil, son_yil + 1):
        tatiller |= resmi_tatiller_yil(yil)[0]
    return tatiller


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
            DOGRULANMIS_DINI_BAYRAMLAR = cozulen
            RESMI_TATILLER = takvim_uret()

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
RESMI_TATILLER = takvim_uret()

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
    """Hafta içi ve resmi tatil değilse iş günüdür."""
    return gun.weekday() < 5 and gun not in tatiller


def hafta_basi(gun):
    """Günün ait olduğu haftanın Pazartesi'si."""
    return gun - dt.timedelta(days=gun.weekday())


def donem_sinirlari(donem):
    """(yıl, ay) ikilisini ayın ilk ve son tarihine çevirir."""
    yil, ay = donem
    return dt.date(yil, ay, 1), dt.date(yil, ay, calendar.monthrange(yil, ay)[1])


def donem_tatilleri(donem, tatiller=None):
    """Dönem ayına düşen resmi tatilleri sıralı liste olarak döner."""
    ilk, son = donem_sinirlari(donem)
    kaynak = RESMI_TATILLER if tatiller is None else tatiller
    return sorted(g for g in kaynak if ilk <= g <= son)


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


def rapor_mu(satir):
    """Satır hastalık raporu ya da doğum istirahati mi?"""
    return (
        satir['İzin Türü'] == RAPOR_IZIN_TURU
        and satir['İzin Nedeni'] in RAPOR_NEDENLERI
    )


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

    # Adsız/boş kolonları at, başlıkları beklenen adlara eşle.
    df = df.loc[:, [k for k in df.columns if not str(k).startswith('Unnamed:')]]
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

    tarih_kolonlari = ['İzin Başlangıç Tarihi', 'İzin Bitiş Tarihi'] + istege_bagli
    for kolon in tarih_kolonlari:
        df[kolon] = pd.to_datetime(df[kolon], errors='coerce')

    df['İzin Türü'] = df['İzin Türü'].fillna('').astype(str).str.strip()
    df['İzin Nedeni'] = df['İzin Nedeni'].fillna('').astype(str).str.strip()
    df['Şirket'] = df['Şirket'].fillna('').astype(str).str.strip()

    for kolon in ('quantityInDays', 'quantityInHours'):
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
    return df


def donem_tespit(df):
    """İzin başlangıç tarihlerinin en sık görüldüğü (yıl, ay) ikilisini döner."""
    donemler = df['İzin Başlangıç Tarihi'].dt.to_period('M')
    en_sik = donemler.mode()
    secilen = en_sik.iloc[0] if not en_sik.empty else donemler.min()
    return int(secilen.year), int(secilen.month)


# ---------------------------------------------------------------- hesaplama

def tutarlilik_uyarisi(satir, tatiller):
    """
    Dosyadaki quantityInDays ile hesaplanan iş günü sayısını karşılaştırır.

    Sapma genellikle resmi tatil takviminin eksik/fazla olduğunu gösterir.
    Yalnızca tam gün satırlarında anlamlıdır; kısmi izinlerde kontrol edilmez.
    """
    gun_sayisi = satir['quantityInDays']
    if gun_sayisi < 1 or gun_sayisi != int(gun_sayisi):
        return None

    baslangic = satir['İzin Başlangıç Tarihi'].date()
    bitis = satir['İzin Bitiş Tarihi'].date()
    hesaplanan = sum(1 for g in gun_araligi(baslangic, bitis) if is_gunu(g, tatiller))
    if hesaplanan == int(gun_sayisi):
        return None
    return (
        f"{baslangic:%d.%m.%Y}-{bitis:%d.%m.%Y} aralığı: dosyada {int(gun_sayisi)} gün, "
        f"tatil takvimine göre {hesaplanan} gün (resmi tatil listesi kontrol edilmeli)"
    )


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


def hesapla_personel(satirlar, donem, tatiller, ek_kolonlar=(), kimlik_ad=None):
    """
    Tek personelin dönem içi destek gün/saatini ve kesinti kırılımını hesaplar.

    satirlar: personele ait izin satırları (DataFrame).
    ek_kolonlar: girdide bulunan, çıktıya taşınacak bilgi kolonları
                 (Sicil No, Departman, İşe Başlama Tarihi vb.).
    kimlik_ad:  kimlik kolonunun çıktıda kullanılacak adı (Ad Soyad, Sicil No...).

    Ücretsiz izin her personelde düşer. Yıllık izin ve resmi tatil yalnızca
    raporlu personelde düşer; yıllık izinde ayrıca kıdem şartı aranır.
    """
    donem_ilk, donem_son = donem_sinirlari(donem)
    ise_baslama = None
    if ISE_BASLAMA_KOLONU in satirlar.columns:
        gecerli = satirlar[ISE_BASLAMA_KOLONU].dropna()
        if not gecerli.empty:
            ise_baslama = gecerli.iloc[0]

    uyarilar = []
    rapor_satirlari, diger_satirlar = [], []
    for _, satir in satirlar.iterrows():
        uyari = tutarlilik_uyarisi(satir, tatiller)
        if uyari:
            uyarilar.append(uyari)

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
    yillik_izinli_mi = any(s['İzin Türü'] in KESINTI_IZIN_TURLERI
                           for s, _, _ in diger_satirlar)

    sonuc = {(kimlik_ad or KIMLIK_KOLONU): satirlar[KIMLIK_KOLONU].iloc[0]}
    # Bilgi kolonları (Sicil No, Departman vb.) kimliğin hemen yanında.
    for kolon in ek_kolonlar:
        sonuc[kolon] = _ek_kolon_degeri(satirlar, kolon)
    sonuc.update({
        'Şirket': satirlar['Şirket'].iloc[0],
        'Dönem': f"{donem[0]}-{donem[1]:02d}",
        'Kıdem (Yıl)': '' if kidem is None else kidem,
        'Yıllık İzin Hakkı': '' if hak is None else hak,
        # 1 yılını doldurmamış personelin yıllık izin kaydı yasal olarak hak
        # edilmemiştir; İK'nın gözden geçirmesi için işaretlenir.
        'Riskli': 'Evet' if (kidem is not None and kidem < 1 and yillik_izinli_mi) else '',
        'Rapor Durumu': 'Raporlu' if rapor_satirlari else 'Raporsuz',
        'Rapor Türü': ', '.join(sorted({s['İzin Nedeni'] for s, _, _ in rapor_satirlari})),
        'Rapor Gün': 0.0,
        'Hafta Sonu Kesintisi': 0.0,
        'Yıllık İzin Kesintisi': 0.0,
        'Resmi Tatil Kesintisi': 0.0,
        'Kısmi Rapor Kesintisi': 0.0,
        'Ücretsiz İzin Kesintisi': 0.0,
        'Toplam Kesinti': 0.0,
        'Destek Gün': float(TESVIK_TABAN_GUN),
        'Destek Saat': float(TESVIK_TABAN_GUN * GUNLUK_SAAT),
        'Uyarı': '',
    })

    # (0) Ücretsiz izin: ücret ödenmediği ve SGK primi yatmadığı için rapor
    # durumundan bağımsız olarak her personelde düşer.
    ucretsiz_gunleri = set()
    for satir, baslangic, bitis in diger_satirlar:
        if satir['İzin Türü'] not in HER_KOSULDA_KESINTI_TURLERI:
            continue
        for gun in gun_araligi(baslangic, bitis):
            if is_gunu(gun, tatiller):
                ucretsiz_gunleri.add(gun)

    if not rapor_satirlari:
        # Raporu olmayan personelde yıllık izin ve resmi tatil düşmez.
        toplam = float(len(ucretsiz_gunleri))
        destek = max(0.0, TESVIK_TABAN_GUN - toplam)
        sonuc.update({
            'Ücretsiz İzin Kesintisi': toplam,
            'Toplam Kesinti': toplam,
            'Destek Gün': destek,
            'Destek Saat': destek * GUNLUK_SAAT,
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
        if satir['İzin Türü'] not in KESINTI_IZIN_TURLERI:
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

    # (d) Dönem içindeki hafta içine denk gelen resmi tatiller.
    resmi_tatil_gunleri = {
        g for g in gun_araligi(donem_ilk, donem_son)
        if g in tatiller and g.weekday() < 5
    }

    # Aynı gün birden çok kategoride işaretlenmiş olabilir; mükerrer saymamak
    # için rapor günleri kazanır. Hafta sonları Cmt-Paz, resmi tatiller ise
    # iş günü kümelerinin dışında olduğu için tanımı gereği ayrık.
    izin_gunleri -= rapor_gunleri
    ucretsiz_gunleri -= rapor_gunleri | izin_gunleri

    kismi_kesinti = kismi_gun_kesintisi(kismi_saat)
    yillik_kesinti = len(izin_gunleri) + yillik_izin_kismi_kesintisi(yarim_gun_toplami)
    toplam_kesinti = (
        len(rapor_gunleri) + len(hafta_sonlari) + yillik_kesinti
        + len(resmi_tatil_gunleri) + len(ucretsiz_gunleri) + kismi_kesinti
    )
    destek_gun = max(0.0, TESVIK_TABAN_GUN - toplam_kesinti)

    sonuc.update({
        'Rapor Gün': float(len(rapor_gunleri)),
        'Hafta Sonu Kesintisi': float(len(hafta_sonlari)),
        'Yıllık İzin Kesintisi': float(yillik_kesinti),
        'Resmi Tatil Kesintisi': float(len(resmi_tatil_gunleri)),
        'Kısmi Rapor Kesintisi': kismi_kesinti,
        'Ücretsiz İzin Kesintisi': float(len(ucretsiz_gunleri)),
        'Toplam Kesinti': float(toplam_kesinti),
        'Destek Gün': destek_gun,
        'Destek Saat': destek_gun * GUNLUK_SAAT,
        'Uyarı': ' | '.join(uyarilar),
    })
    return sonuc


def hesapla(df, donem=None, tatiller=None):
    """
    Tüm personel için destek gün/saat tablosunu üretir.

    donem: (yıl, ay); verilmezse veriden tespit edilir.
    tatiller: resmi tatil tarihleri kümesi; verilmezse RESMI_TATILLER kullanılır.
    """
    if donem is None:
        donem = donem_tespit(df)
    tatiller = set(RESMI_TATILLER if tatiller is None else tatiller)

    # Girdideki tanınmayan kolonlar bilgi kolonu kabul edilip çıktıya taşınır.
    ek_kolonlar = [k for k in df.columns if k not in KOLONLAR]
    kimlik_ad = df.attrs.get('kimlik_ad', KIMLIK_KOLONU)

    sonuclar = [
        hesapla_personel(satirlar, donem, tatiller, ek_kolonlar, kimlik_ad)
        for _, satirlar in df.groupby(KIMLIK_KOLONU, sort=True)
    ]
    return pd.DataFrame(sonuclar)


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
    print(f"Toplam destek günü: {sonuc['Destek Gün'].sum():g}")
    print(f"Çıktı (tüm personel): {ana_yol}")
    if kesintili_yol:
        print(f"Çıktı (kesintili personel): {kesintili_yol}")
