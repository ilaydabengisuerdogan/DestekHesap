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
import os
import re

import pandas as pd

# Türkçe karakterleri sadeleştirir; kolon adlarını karşılaştırırken kullanılır.
TR_HARF_HARITASI = str.maketrans({
    'İ': 'i', 'I': 'i', 'ı': 'i', 'Ş': 's', 'ş': 's', 'Ğ': 'g', 'ğ': 'g',
    'Ü': 'u', 'ü': 'u', 'Ö': 'o', 'ö': 'o', 'Ç': 'c', 'ç': 'c',
})

# Başlık satırı aranırken taranacak satır sayısı (üstte logo/başlık bloğu olabilir).
BASLIK_ARAMA_DERINLIGI = 15

# --- Girdi şeması ---
KOLONLAR = [
    'Çalışan Numarası',
    'Şirket',
    'İzin Türü',
    'İzin Nedeni',
    'İzin Başlangıç Tarihi',
    'İzin Bitiş Tarihi',
    'quantityInDays',
    'quantityInHours',
]

# Kolon adı farklılıklarına tolerans. Birebir eşleşme bulunamazsa bu adlar
# denenir; büyük/küçük harf, Türkçe karakter ve noktalama farkları önemsizdir.
# 'Sicil No' burada çalışan numarasının karşılığıdır; dosyada ayrıca
# 'Çalışan Numarası' varsa o öncelikli olur, 'Sicil No' ek kolon olarak taşınır.
KOLON_ESANLAMLILARI = {
    'Çalışan Numarası': ['Sicil No', 'Sicil Numarası', 'Personel No', 'Personel Numarası',
                         'Çalışan No', 'Employee Id', 'Employee Number', 'TC', 'TC Kimlik No'],
    'Şirket': ['Firma', 'Şirket Adı', 'Company'],
    'İzin Türü': ['İzin Tipi', 'Devamsızlık Tipi', 'Leave Type'],
    'İzin Nedeni': ['İzin Sebebi', 'Neden', 'Açıklama', 'Leave Reason'],
    'İzin Başlangıç Tarihi': ['Başlangıç Tarihi', 'Başlangıç', 'İlk Gün', 'Start Date'],
    'İzin Bitiş Tarihi': ['Bitiş Tarihi', 'Bitiş', 'Son Gün', 'End Date'],
    'quantityInDays': ['Gün', 'Gün Sayısı', 'İzin Gün Sayısı', 'Days'],
    'quantityInHours': ['Saat', 'Saat Sayısı', 'İzin Saat Sayısı', 'Hours'],
}

# --- Kural sabitleri ---
RAPOR_IZIN_TURU = 'Şirket Dışında Olma Nedeni'
RAPOR_NEDENLERI = {'Hastalık Raporu', 'Kadın Doğum İstirahat Raporu'}

# Raporlu personelde teşvikten düşen izin türleri. Mazeret İzni (doktor
# randevusu, doğum günü izni vb.) ve Evlilik İzni buraya dahil değildir.
KESINTI_IZIN_TURLERI = {'Yıllık İzin'}

TESVIK_TABAN_GUN = 30
GUNLUK_SAAT = 8
YARIM_GUN_SAAT = GUNLUK_SAAT / 2

# Resmi tatil takvimi. Dini bayramlar yıldan yıla kaydığı için liste elle
# güncellenir; arayüzden de dönem bazında düzenlenebilir.
# Temmuz 2026 girdisiyle doğrulanan tarihler: 15.07 (dönem içi) ve 28-29.10.
# Ramazan/Kurban Bayramı tarihleri veriyle doğrulanmadı, kullanım öncesi kontrol edilmeli.
# Takvim eksikse tutarlilik_uyarisi() sapmayı çıktıdaki 'Uyarı' kolonunda bildirir.
RESMI_TATILLER = {
    dt.date(2026, 1, 1),    # Yılbaşı
    dt.date(2026, 3, 19),   # Ramazan Bayramı Arifesi (yarım gün, tam gün sayılıyor)
    dt.date(2026, 3, 20),   # Ramazan Bayramı 1. Gün
    dt.date(2026, 3, 21),   # Ramazan Bayramı 2. Gün
    dt.date(2026, 3, 22),   # Ramazan Bayramı 3. Gün
    dt.date(2026, 4, 23),   # Ulusal Egemenlik ve Çocuk Bayramı
    dt.date(2026, 5, 1),    # Emek ve Dayanışma Günü
    dt.date(2026, 5, 19),   # Atatürk'ü Anma, Gençlik ve Spor Bayramı
    dt.date(2026, 5, 26),   # Kurban Bayramı Arifesi
    dt.date(2026, 5, 27),   # Kurban Bayramı 1. Gün
    dt.date(2026, 5, 28),   # Kurban Bayramı 2. Gün
    dt.date(2026, 5, 29),   # Kurban Bayramı 3. Gün
    dt.date(2026, 5, 30),   # Kurban Bayramı 4. Gün
    dt.date(2026, 7, 15),   # Demokrasi ve Millî Birlik Günü
    dt.date(2026, 8, 30),   # Zafer Bayramı
    dt.date(2026, 10, 28),  # Cumhuriyet Bayramı Arifesi
    dt.date(2026, 10, 29),  # Cumhuriyet Bayramı
}


class GirdiHatasi(Exception):
    """Girdi dosyası beklenen şemaya uymadığında fırlatılır."""


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

    Önce birebir, sonra eşanlamlı adlar denenir. Bir kolon adı birden çok
    beklenen kolona uyuyorsa (örn. 'Sicil No') öncelik sırası korunur.
    Döner: {dosyadaki_baslik: beklenen_kolon}
    """
    normalize = {b: _normalize_baslik(b) for b in basliklar}
    eslesme = {}
    kullanilan = set()

    # 1. tur: beklenen adın kendisiyle birebir eşleşme
    for beklenen in KOLONLAR:
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


def _basligi_bul(kaynak):
    """
    Başlık satırı ilk satırda değilse (üstte logo/başlık blokları varsa) bulur.

    İlk BASLIK_ARAMA_DERINLIGI satır taranır, beklenen kolonlardan en çoğunu
    içeren satır başlık kabul edilir. Döner: (df, baslik_satir_no)
    """
    ham = pd.read_excel(kaynak, header=None, nrows=BASLIK_ARAMA_DERINLIGI)
    en_iyi_satir, en_iyi_skor = 0, -1
    for i in range(len(ham)):
        basliklar = [h for h in ham.iloc[i].tolist() if pd.notna(h)]
        skor = len(set(_kolonlari_esle(basliklar).values()))
        if skor > en_iyi_skor:
            en_iyi_satir, en_iyi_skor = i, skor
    return en_iyi_satir


def oku(kaynak):
    """
    İzin raporu Excel'ini okur, doğrular ve normalize eder.

    kaynak: dosya yolu veya dosya benzeri nesne (Streamlit upload).

    Kolon adlarında büyük/küçük harf, Türkçe karakter ve yaygın eşanlamlı
    farkları tolere edilir. Beklenenlerin dışındaki kolonlar (Ad Soyad,
    Sicil No, Departman vb.) korunur ve çıktıya taşınır.
    """
    def _geri_sar():
        if hasattr(kaynak, 'seek'):
            kaynak.seek(0)

    try:
        _geri_sar()
        baslik_satiri = _basligi_bul(kaynak)
        _geri_sar()
        df = pd.read_excel(kaynak, header=baslik_satiri)
    except Exception as hata:
        raise GirdiHatasi(f"Excel dosyası okunamadı: {hata}") from hata

    # Adsız/boş kolonları at, başlıkları beklenen adlara eşle.
    df = df.loc[:, [k for k in df.columns if not str(k).startswith('Unnamed:')]]
    df = df.rename(columns=_kolonlari_esle(df.columns))

    eksik = [k for k in KOLONLAR if k not in df.columns]
    if eksik:
        raise GirdiHatasi(
            "Yüklenen dosyada şu kolonlar eksik: " + ", ".join(eksik)
            + ".\nBeklenen kolonlar: " + ", ".join(KOLONLAR)
            + ".\nDosyada bulunanlar: " + ", ".join(str(k) for k in df.columns)
        )

    # Beklenen kolonlar önce, tanınmayan ek kolonlar (kimlik bilgileri) sonra.
    ek_kolonlar = [k for k in df.columns if k not in KOLONLAR]
    df = df[KOLONLAR + ek_kolonlar].copy()

    for kolon in ('İzin Başlangıç Tarihi', 'İzin Bitiş Tarihi'):
        df[kolon] = pd.to_datetime(df[kolon], errors='coerce')

    df['İzin Türü'] = df['İzin Türü'].fillna('').astype(str).str.strip()
    df['İzin Nedeni'] = df['İzin Nedeni'].fillna('').astype(str).str.strip()
    df['Şirket'] = df['Şirket'].fillna('').astype(str).str.strip()

    for kolon in ('quantityInDays', 'quantityInHours'):
        df[kolon] = pd.to_numeric(df[kolon], errors='coerce').fillna(0.0)

    # Çalışan numarası ya da tarihi olmayan satırlar hesaba alınamaz.
    df = df.dropna(subset=['Çalışan Numarası', 'İzin Başlangıç Tarihi', 'İzin Bitiş Tarihi'])
    if df.empty:
        raise GirdiHatasi("Dosyada işlenebilir veri satırı bulunamadı.")

    # Bitiş başlangıçtan önceyse tek günlük kayıt olarak ele al.
    ters = df['İzin Bitiş Tarihi'] < df['İzin Başlangıç Tarihi']
    df.loc[ters, 'İzin Bitiş Tarihi'] = df.loc[ters, 'İzin Başlangıç Tarihi']

    df = df.drop_duplicates()
    return df.reset_index(drop=True)


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
    degerler = satirlar[kolon].dropna().astype(str).str.strip()
    degerler = [d for d in dict.fromkeys(degerler) if d]
    if not degerler:
        return ''
    if len(degerler) == 1:
        return degerler[0]
    return ' / '.join(degerler)[:200]


def hesapla_personel(satirlar, donem, tatiller, ek_kolonlar=()):
    """
    Tek personelin dönem içi destek gün/saatini ve kesinti kırılımını hesaplar.

    satirlar: personele ait izin satırları (DataFrame).
    ek_kolonlar: girdide bulunan, çıktıya taşınacak kimlik kolonları
                 (Ad Soyad, Sicil No, Departman vb.).
    Raporu olmayan personelde hiçbir izin türü teşvikten düşmez.
    """
    donem_ilk, donem_son = donem_sinirlari(donem)

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

    sonuc = {'Çalışan Numarası': satirlar['Çalışan Numarası'].iloc[0]}
    # Kimlik kolonları (Ad Soyad, Sicil No vb.) çalışan numarasının hemen yanında.
    for kolon in ek_kolonlar:
        sonuc[kolon] = _ek_kolon_degeri(satirlar, kolon)
    sonuc.update({
        'Şirket': satirlar['Şirket'].iloc[0],
        'Dönem': f"{donem[0]}-{donem[1]:02d}",
        'Rapor Durumu': 'Raporlu' if rapor_satirlari else 'Raporsuz',
        'Rapor Türü': ', '.join(sorted({s['İzin Nedeni'] for s, _, _ in rapor_satirlari})),
        'Rapor Gün': 0.0,
        'Hafta Sonu Kesintisi': 0.0,
        'Yıllık İzin Kesintisi': 0.0,
        'Resmi Tatil Kesintisi': 0.0,
        'Kısmi Rapor Kesintisi': 0.0,
        'Toplam Kesinti': 0.0,
        'Destek Gün': float(TESVIK_TABAN_GUN),
        'Destek Saat': float(TESVIK_TABAN_GUN * GUNLUK_SAAT),
        'Uyarı': ' | '.join(uyarilar),
    })

    # Raporu olmayan personelde yıllık izin ve resmi tatil düşmez.
    if not rapor_satirlari:
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

    # (c) Yıllık izin günleri. Mazeret İzni, Evlilik İzni gibi diğer izin
    # türleri teşvikten düşmez; yalnızca yıllık izin ve resmi tatil düşer.
    izin_gunleri = set()
    for satir, baslangic, bitis in diger_satirlar:
        if satir['İzin Türü'] not in KESINTI_IZIN_TURLERI:
            continue
        for gun in gun_araligi(baslangic, bitis):
            if is_gunu(gun, tatiller):
                izin_gunleri.add(gun)

    # (d) Dönem içindeki hafta içine denk gelen resmi tatiller.
    resmi_tatil_gunleri = {
        g for g in gun_araligi(donem_ilk, donem_son)
        if g in tatiller and g.weekday() < 5
    }

    # Aynı gün hem rapor hem yıllık izin olarak işaretlenmiş olabilir; mükerrer
    # saymamak için rapor günleri kazanır. Diğer kümeler tanımı gereği ayrık:
    # hafta sonları Cmt-Paz, resmi tatiller ise iş günü kümelerinin dışında.
    izin_gunleri -= rapor_gunleri

    kismi_kesinti = kismi_gun_kesintisi(kismi_saat)
    toplam_kesinti = (
        len(rapor_gunleri) + len(hafta_sonlari) + len(izin_gunleri)
        + len(resmi_tatil_gunleri) + kismi_kesinti
    )
    destek_gun = max(0.0, TESVIK_TABAN_GUN - toplam_kesinti)

    sonuc.update({
        'Rapor Gün': float(len(rapor_gunleri)),
        'Hafta Sonu Kesintisi': float(len(hafta_sonlari)),
        'Yıllık İzin Kesintisi': float(len(izin_gunleri)),
        'Resmi Tatil Kesintisi': float(len(resmi_tatil_gunleri)),
        'Kısmi Rapor Kesintisi': kismi_kesinti,
        'Toplam Kesinti': float(toplam_kesinti),
        'Destek Gün': destek_gun,
        'Destek Saat': destek_gun * GUNLUK_SAAT,
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

    # Girdideki tanınmayan kolonlar kimlik bilgisi kabul edilip çıktıya taşınır.
    ek_kolonlar = [k for k in df.columns if k not in KOLONLAR]

    sonuclar = [
        hesapla_personel(satirlar, donem, tatiller, ek_kolonlar)
        for _, satirlar in df.groupby('Çalışan Numarası', sort=True)
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
