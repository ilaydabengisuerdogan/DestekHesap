"""
Kural motoru testleri.

İki katman:
  1. Gerçek Temmuz 2026 dosyası üzerinde regresyon kilidi (dosya varsa).
  2. Kuralları tek tek izole eden sentetik senaryolar.
"""

import datetime as dt
import glob
import os

import pandas as pd
import pytest

import hesaplama

TEMMUZ = (2026, 7)
TATILLER = {dt.date(2026, 7, 15)}  # 15 Temmuz, Çarşamba


# ------------------------------------------------------------ yardımcılar

def satir(calisan, izin_turu, baslangic, bitis, gun, nedeni='', sirket='Test A.Ş.'):
    """Tek bir izin satırı üretir. Tarihler 'YYYY-MM-DD' string'i."""
    return {
        'Çalışan Numarası': calisan,
        'Şirket': sirket,
        'İzin Türü': izin_turu,
        'İzin Nedeni': nedeni,
        'İzin Başlangıç Tarihi': pd.Timestamp(baslangic),
        'İzin Bitiş Tarihi': pd.Timestamp(bitis),
        'quantityInDays': gun,
        'quantityInHours': gun * hesaplama.GUNLUK_SAAT,
    }


def rapor(calisan, baslangic, bitis, gun, nedeni='Hastalık Raporu'):
    return satir(calisan, hesaplama.RAPOR_IZIN_TURU, baslangic, bitis, gun, nedeni)


def hesapla(satirlar, donem=TEMMUZ, tatiller=TATILLER):
    """Satır listesini tek personel varsayımıyla hesaplayıp sonuç sözlüğünü döner."""
    sonuc = hesaplama.hesapla(pd.DataFrame(satirlar), donem, tatiller)
    assert len(sonuc) == 1, "yardımcı yalnızca tek personel için kullanılır"
    return sonuc.iloc[0]


# ------------------------------------------------- 1) gerçek veri regresyonu

# Gerçek dosyadan doğrulanmış beklenen değerler:
# (rapor günü, hafta sonu, yıllık izin, resmi tatil, kısmi rapor, destek günü)
GERCEK_BEKLENEN = {
    1043: (12, 4, 0, 1, 0.0, 13.0),
    1079: (1, 2, 5, 1, 0.0, 21.0),
    1179: (9, 2, 4, 1, 0.0, 14.0),
    1192: (1, 2, 2, 1, 0.0, 24.0),
    1297: (2, 2, 0, 1, 0.0, 25.0),
    1303: (1, 2, 2, 1, 0.0, 24.0),
    1333: (3, 0, 0, 1, 0.0, 26.0),
    1345: (1, 0, 2, 1, 0.0, 26.0),
}

GERCEK_PERSONEL_SAYISI = 215
GERCEK_TOPLAM_DESTEK = 6383.0


def _gercek_dosya():
    eslesenler = glob.glob(os.path.join(os.path.dirname(__file__), '*İzin Raporu*.xlsx'))
    return eslesenler[0] if eslesenler else None


@pytest.fixture(scope='module')
def gercek_sonuc():
    yol = _gercek_dosya()
    if yol is None:
        pytest.skip("Gerçek izin raporu dosyası bulunamadı")
    veri = hesaplama.oku(yol)
    return hesaplama.hesapla(veri, hesaplama.donem_tespit(veri))


def test_gercek_veri_donem_tespiti():
    yol = _gercek_dosya()
    if yol is None:
        pytest.skip("Gerçek izin raporu dosyası bulunamadı")
    assert hesaplama.donem_tespit(hesaplama.oku(yol)) == TEMMUZ


def test_gercek_veri_toplamlari(gercek_sonuc):
    assert len(gercek_sonuc) == GERCEK_PERSONEL_SAYISI
    assert (gercek_sonuc['Rapor Durumu'] == 'Raporlu').sum() == len(GERCEK_BEKLENEN)
    assert gercek_sonuc['Destek Gün'].sum() == pytest.approx(GERCEK_TOPLAM_DESTEK)


@pytest.mark.parametrize('calisan, beklenen', sorted(GERCEK_BEKLENEN.items()))
def test_gercek_veri_raporlu_personel(gercek_sonuc, calisan, beklenen):
    satir_ = gercek_sonuc.set_index('Çalışan Numarası').loc[calisan]
    assert (
        satir_['Rapor Gün'],
        satir_['Hafta Sonu Kesintisi'],
        satir_['Yıllık İzin Kesintisi'],
        satir_['Resmi Tatil Kesintisi'],
        satir_['Kısmi Rapor Kesintisi'],
        satir_['Destek Gün'],
    ) == pytest.approx(beklenen)


def test_gercek_veri_raporsuz_personel_tam_destek(gercek_sonuc):
    raporsuz = gercek_sonuc[gercek_sonuc['Rapor Durumu'] == 'Raporsuz']
    assert (raporsuz['Destek Gün'] == hesaplama.TESVIK_TABAN_GUN).all()
    assert (raporsuz['Toplam Kesinti'] == 0).all()


def test_gercek_veri_tatil_takvimi_tutarli(gercek_sonuc):
    """Varsayılan takvimle hiçbir satırda quantityInDays sapması olmamalı."""
    assert (gercek_sonuc['Uyarı'] == '').all()


def test_gercek_veri_kirilim_toplami_tutarli(gercek_sonuc):
    assert (gercek_sonuc['Toplam Kesinti'] + gercek_sonuc['Destek Gün'] == hesaplama.TESVIK_TABAN_GUN).all()
    assert (gercek_sonuc['Destek Saat'] == gercek_sonuc['Destek Gün'] * hesaplama.GUNLUK_SAAT).all()


# ------------------------------------------------------ 2) sentetik senaryolar

def test_raporsuz_personelde_hicbir_izin_dusmez():
    """Yıllık izin, kısmi mazeret izni ve ay içindeki resmi tatil teşviki azaltmaz."""
    sonuc = hesapla([
        satir(1, 'Yıllık İzin', '2026-07-06', '2026-07-10', 5),
        satir(1, 'Mazeret İzni', '2026-07-22', '2026-07-22', 0.25, 'Doktor Randevusu'),
    ])
    assert sonuc['Rapor Durumu'] == 'Raporsuz'
    assert sonuc['Toplam Kesinti'] == 0
    assert sonuc['Destek Gün'] == 30
    assert sonuc['Destek Saat'] == 240


def test_dogum_istirahati_de_rapor_sayilir():
    sonuc = hesapla([rapor(1, '2026-07-09', '2026-07-09', 1, 'Kadın Doğum İstirahat Raporu')])
    assert sonuc['Rapor Durumu'] == 'Raporlu'
    assert sonuc['Rapor Türü'] == 'Kadın Doğum İstirahat Raporu'


def test_tek_gunluk_rapor_hafta_sonu_ve_resmi_tatili_dusurur():
    """Perşembe 9 Temmuz raporu: 1 rapor + 2 hafta sonu (11-12) + 1 resmi tatil (15)."""
    sonuc = hesapla([rapor(1, '2026-07-09', '2026-07-09', 1)])
    assert sonuc['Rapor Gün'] == 1
    assert sonuc['Hafta Sonu Kesintisi'] == 2
    assert sonuc['Resmi Tatil Kesintisi'] == 1
    assert sonuc['Destek Gün'] == 26


def test_rapor_her_degdigi_haftanin_hafta_sonunu_dusurur():
    """9-20 Temmuz raporu 3 haftaya yayılır: 6-12, 13-19, 20-26 -> 6 hafta sonu günü."""
    sonuc = hesapla([rapor(1, '2026-07-09', '2026-07-20', 7)])
    assert sonuc['Hafta Sonu Kesintisi'] == 6
    # 9,10,13,14,16,17,20 iş günü (15 Temmuz resmi tatil, rapor günü sayılmaz)
    assert sonuc['Rapor Gün'] == 7
    assert sonuc['Resmi Tatil Kesintisi'] == 1


def test_ay_disina_tasan_hafta_sonu_sayilmaz():
    """29-31 Temmuz raporu: o haftanın hafta sonu 1-2 Ağustos, Temmuz'dan düşmez."""
    sonuc = hesapla([rapor(1, '2026-07-29', '2026-07-31', 3)])
    assert sonuc['Rapor Gün'] == 3
    assert sonuc['Hafta Sonu Kesintisi'] == 0


def test_onceki_aydan_baslayan_haftanin_ay_ici_hafta_sonu_sayilir():
    """1-2 Temmuz raporu: hafta Haziran'da başlasa da hafta sonu (4-5 Tem) Temmuz'da."""
    sonuc = hesapla([rapor(1, '2026-07-01', '2026-07-02', 2)])
    assert sonuc['Rapor Gün'] == 2
    assert sonuc['Hafta Sonu Kesintisi'] == 2


def test_ay_disina_tasan_rapor_kirpilir():
    """21 Temmuz - 19 Ağustos raporunda yalnızca Temmuz günleri sayılır."""
    sonuc = hesapla([rapor(1, '2026-07-21', '2026-08-19', 22)])
    # 21-24, 27-31 -> 9 iş günü. Haftalar: 20-26 (hafta sonu 25-26 Temmuz'da)
    # ve 27-31 (hafta sonu 1-2 Ağustos, ay dışı) -> yalnızca 2 gün.
    assert sonuc['Rapor Gün'] == 9
    assert sonuc['Hafta Sonu Kesintisi'] == 2


def test_rapor_ve_yillik_izin_ayni_gunde_mukerrer_sayilmaz():
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-10', 2),
        satir(1, 'Yıllık İzin', '2026-07-09', '2026-07-10', 2),
    ])
    assert sonuc['Rapor Gün'] == 2
    assert sonuc['Yıllık İzin Kesintisi'] == 0
    # 2 rapor + 2 hafta sonu + 1 resmi tatil
    assert sonuc['Toplam Kesinti'] == 5


def test_raporluda_yillik_izin_duser():
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-09', 1),
        satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2),
    ])
    assert sonuc['Yıllık İzin Kesintisi'] == 2
    # Yıllık izin haftası (20-26) rapor haftası olmadığı için hafta sonu düşmez.
    assert sonuc['Hafta Sonu Kesintisi'] == 2


@pytest.mark.parametrize('izin_turu, nedeni, gun', [
    ('Mazeret İzni', 'Doğum Günü İzni', 1),        # tam gün mazeret
    ('Mazeret İzni', 'Doktor Randevusu', 0.5),     # saatlik mazeret
    ('Evlilik İzni', '', 3),
])
def test_raporluda_mazeret_ve_evlilik_izni_dusmez(izin_turu, nedeni, gun):
    """Yalnızca yıllık izin ve resmi tatil düşer; diğer izin türleri düşmez."""
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-09', 1),
        satir(1, izin_turu, '2026-07-20', '2026-07-22', gun, nedeni),
    ])
    assert sonuc['Yıllık İzin Kesintisi'] == 0
    assert sonuc['Kısmi Rapor Kesintisi'] == 0
    # yalnızca 1 rapor + 2 hafta sonu (11-12 Tem) + 1 resmi tatil (15 Tem)
    assert sonuc['Toplam Kesinti'] == 4


def test_tam_ay_rapor_destek_sifira_dusmez_negatife():
    sonuc = hesapla([rapor(1, '2026-07-01', '2026-07-31', 22)])
    assert sonuc['Destek Gün'] == 0
    assert sonuc['Destek Saat'] == 0


@pytest.mark.parametrize('saat, beklenen', [
    (0, 0.0),
    (1, 0.5),      # yarım günün altı -> yarım gün
    (4, 0.5),      # tam yarım gün
    (5, 1.0),      # yarım günden fazla -> tam gün
    (8, 1.0),
    (12, 1.5),     # 1 tam gün + 4 saat
    (13, 2.0),     # 1 tam gün + 5 saat
    (16, 2.0),
])
def test_kismi_gun_yuvarlama(saat, beklenen):
    assert hesaplama.kismi_gun_kesintisi(saat) == beklenen


def test_kismi_raporlar_aylik_birikimli_toplanir():
    """3 ayrı 2 saatlik rapor = 6 saat -> yarım günü aştığı için 1 tam gün."""
    sonuc = hesapla([
        rapor(1, '2026-07-06', '2026-07-06', 0.25),
        rapor(1, '2026-07-20', '2026-07-20', 0.25),
        rapor(1, '2026-07-22', '2026-07-22', 0.25),
    ])
    assert sonuc['Rapor Gün'] == 0          # hiçbiri tam gün değil
    assert sonuc['Kısmi Rapor Kesintisi'] == 1.0


def test_kullanici_ornegi():
    """
    Kullanıcının verdiği örnek: 2. haftada 2 saatlik eksik çalışma, farklı bir
    haftada 2 gün yıllık izin, yine farklı bir haftada 1 gün resmi tatil.
    Beklenen kayıp: 0,5 + 2 (hafta sonu) + 2 (yıllık izin) + 1 (resmi tatil) = 5,5 gün.
    """
    sonuc = hesapla([
        # 2. hafta (6-12 Temmuz) içinde eksik çalışmaya yol açan rapor
        rapor(1, '2026-07-08', '2026-07-08', 0.25),
        satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2),
    ])
    # 0,5 gün eksik çalışma + 2 gün hafta sonu (11-12) + 2 gün yıllık izin + 1 gün 15 Temmuz
    assert sonuc['Toplam Kesinti'] == 5.5
    assert sonuc['Destek Gün'] == 24.5


def test_resmi_tatil_hafta_sonuna_denk_gelirse_sayilmaz():
    sonuc = hesapla(
        [rapor(1, '2026-07-09', '2026-07-09', 1)],
        tatiller={dt.date(2026, 7, 18)},  # Cumartesi
    )
    assert sonuc['Resmi Tatil Kesintisi'] == 0


# ------------------------------------------------------------ okuma/doğrulama

def test_eksik_kolon_anlamli_hata_verir(tmp_path):
    yol = tmp_path / 'bozuk.xlsx'
    pd.DataFrame({'Ad Soyad': ['Test'], 'Tarih': ['2026-07-01']}).to_excel(yol, index=False)
    with pytest.raises(hesaplama.GirdiHatasi) as hata:
        hesaplama.oku(yol)
    assert 'Çalışan Numarası' in str(hata.value)


def test_bos_dosya_hata_verir(tmp_path):
    yol = tmp_path / 'bos.xlsx'
    pd.DataFrame(columns=hesaplama.KOLONLAR).to_excel(yol, index=False)
    with pytest.raises(hesaplama.GirdiHatasi):
        hesaplama.oku(yol)


def test_mukerrer_satirlar_bir_kez_sayilir(tmp_path):
    yol = tmp_path / 'mukerrer.xlsx'
    kayit = satir(1, hesaplama.RAPOR_IZIN_TURU, '2026-07-09', '2026-07-09', 1, 'Hastalık Raporu')
    pd.DataFrame([kayit, dict(kayit)]).to_excel(yol, index=False)
    assert len(hesaplama.oku(yol)) == 1


def test_ters_tarih_araligi_tek_gune_cevrilir(tmp_path):
    yol = tmp_path / 'ters.xlsx'
    pd.DataFrame([satir(1, 'Yıllık İzin', '2026-07-10', '2026-07-09', 1)]).to_excel(yol, index=False)
    veri = hesaplama.oku(yol)
    assert veri['İzin Bitiş Tarihi'].iloc[0] == veri['İzin Başlangıç Tarihi'].iloc[0]


def test_ikili_excel_ciktisi(tmp_path, gercek_sonuc):
    """Kaydetme, tüm personel ve kesintili personel için iki dosya üretmeli."""
    yol = tmp_path / 'destek.xlsx'
    ana, kesintili = hesaplama.excel_yaz_ikili(gercek_sonuc, yol)

    assert os.path.exists(ana)
    assert os.path.exists(kesintili)
    assert kesintili.endswith('_kesintili.xlsx')

    tumu = pd.read_excel(ana)
    sadece = pd.read_excel(kesintili)
    assert len(tumu) == GERCEK_PERSONEL_SAYISI
    assert len(sadece) == len(GERCEK_BEKLENEN)
    assert list(tumu.columns) == list(sadece.columns)
    assert (sadece['Toplam Kesinti'] > 0).all()
    assert sorted(sadece['Çalışan Numarası']) == sorted(GERCEK_BEKLENEN)


def test_kesintili_personel_yoksa_ikinci_dosya_olusmaz(tmp_path):
    yol = tmp_path / 'destek.xlsx'
    sonuc = hesaplama.hesapla(
        pd.DataFrame([satir(1, 'Yıllık İzin', '2026-07-06', '2026-07-10', 5)]),
        TEMMUZ, TATILLER,
    )
    ana, kesintili = hesaplama.excel_yaz_ikili(sonuc, yol)
    assert os.path.exists(ana)
    assert kesintili is None
    assert not os.path.exists(hesaplama.kesintili_dosya_yolu(yol))


# ------------------------------------------- girdi dosyası esnekliği

def _yaz(tmp_path, kayitlar, ad='girdi.xlsx', ust_bloklar=0, kolon_adlari=None):
    """Test girdisi üretir; istenirse başlığın üstüne boş/başlık blokları koyar."""
    yol = tmp_path / ad
    df = pd.DataFrame(kayitlar)
    if kolon_adlari:
        df = df.rename(columns=kolon_adlari)
    if not ust_bloklar:
        df.to_excel(yol, index=False)
        return yol
    with pd.ExcelWriter(yol, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, startrow=ust_bloklar, sheet_name='Sheet1')
        sayfa = writer.sheets['Sheet1']
        sayfa.cell(row=1, column=1, value='NETAŞ İZİN RAPORU')
        sayfa.cell(row=2, column=1, value='Dönem: Temmuz 2026')
    return yol


def test_ek_kolonlar_ciktiya_tasinir(tmp_path):
    """Ad Soyad, Sicil No gibi sonradan eklenen kolonlar çıktıda yer almalı."""
    kayit = rapor(1, '2026-07-09', '2026-07-09', 1)
    kayit.update({'Ad Soyad': 'Ayşe Yılmaz', 'Sicil No': 'S-4471', 'Departman': 'Ar-Ge'})
    sonuc = hesaplama.hesapla(hesaplama.oku(_yaz(tmp_path, [kayit])), TEMMUZ, TATILLER)

    assert sonuc['Ad Soyad'].iloc[0] == 'Ayşe Yılmaz'
    assert sonuc['Sicil No'].iloc[0] == 'S-4471'
    assert sonuc['Departman'].iloc[0] == 'Ar-Ge'
    # Kimlik kolonları çalışan numarasının hemen yanında olmalı.
    assert list(sonuc.columns)[:4] == ['Çalışan Numarası', 'Ad Soyad', 'Sicil No', 'Departman']
    assert sonuc['Destek Gün'].iloc[0] == 26


def test_ek_kolon_satirdan_satira_degisirse_hepsi_gosterilir(tmp_path):
    a = rapor(1, '2026-07-09', '2026-07-09', 1)
    b = satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2)
    a['Departman'], b['Departman'] = 'Ar-Ge', 'Üretim'
    sonuc = hesaplama.hesapla(hesaplama.oku(_yaz(tmp_path, [a, b])), TEMMUZ, TATILLER)
    assert sonuc['Departman'].iloc[0] == 'Ar-Ge / Üretim'


def test_esanlamli_kolon_adlari_taninir(tmp_path):
    """'Sicil No', 'Başlangıç Tarihi' gibi farklı adlandırmalar kabul edilmeli."""
    yol = _yaz(tmp_path, [rapor(1, '2026-07-09', '2026-07-09', 1)], kolon_adlari={
        'Çalışan Numarası': 'Sicil No',
        'İzin Başlangıç Tarihi': 'Başlangıç Tarihi',
        'İzin Bitiş Tarihi': 'Bitiş Tarihi',
        'İzin Türü': 'İzin Tipi',
        'quantityInDays': 'Gün Sayısı',
        'quantityInHours': 'Saat Sayısı',
    })
    sonuc = hesaplama.hesapla(hesaplama.oku(yol), TEMMUZ, TATILLER)
    assert sonuc['Çalışan Numarası'].iloc[0] == 1
    assert sonuc['Rapor Durumu'].iloc[0] == 'Raporlu'
    assert sonuc['Destek Gün'].iloc[0] == 26


def test_buyuk_kucuk_harf_ve_bosluk_farki_onemsiz(tmp_path):
    yol = _yaz(tmp_path, [rapor(1, '2026-07-09', '2026-07-09', 1)], kolon_adlari={
        'Çalışan Numarası': '  ÇALIŞAN NUMARASI ',
        'quantityInDays': 'QuantityInDays',
        'İzin Türü': 'izin türü',
    })
    assert list(hesaplama.oku(yol).columns)[:8] == hesaplama.KOLONLAR


def test_baslik_ustunde_blok_varsa_bulunur(tmp_path):
    """Başlık satırı ilk satırda değilse (üstte başlık bloğu varsa) bulunmalı."""
    yol = _yaz(tmp_path, [rapor(1, '2026-07-09', '2026-07-09', 1)], ust_bloklar=3)
    veri = hesaplama.oku(yol)
    assert list(veri.columns)[:8] == hesaplama.KOLONLAR
    assert len(veri) == 1
    assert hesaplama.hesapla(veri, TEMMUZ, TATILLER)['Destek Gün'].iloc[0] == 26


def test_gercek_dosya_ek_kolonsuz_calismaya_devam_eder(gercek_sonuc):
    """Ek kolon olmayan mevcut dosyada çıktı kolonları değişmemeli."""
    assert list(gercek_sonuc.columns)[:2] == ['Çalışan Numarası', 'Şirket']


def test_eksik_tatil_takvimi_uyari_uretir():
    """15 Temmuz takvimden çıkarılırsa 13-17 Temmuz aralığı sapma bildirmeli."""
    sonuc = hesapla(
        [satir(1, 'Yıllık İzin', '2026-07-13', '2026-07-17', 4)],
        tatiller=set(),
    )
    assert 'resmi tatil listesi' in sonuc['Uyarı']


def test_dogru_takvimde_uyari_uretilmez():
    sonuc = hesapla([satir(1, 'Yıllık İzin', '2026-07-13', '2026-07-17', 4)])
    assert sonuc['Uyarı'] == ''
