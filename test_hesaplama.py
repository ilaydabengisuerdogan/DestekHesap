"""
Kural motoru testleri.

İki katman:
  1. Gerçek Temmuz 2026 dosyası üzerinde regresyon kilidi (dosya varsa).
  2. Kuralları tek tek izole eden sentetik senaryolar.
"""

import datetime as dt
import glob
import json
import os

import pandas as pd
import pytest

import hesaplama

TEMMUZ = (2026, 7)
TATILLER = {dt.date(2026, 7, 15)}  # 15 Temmuz, Çarşamba


# ------------------------------------------------------------ yardımcılar

KIMLIK = hesaplama.KIMLIK_KOLONU


def satir(calisan, izin_turu, baslangic, bitis, gun, nedeni='', sirket='Test A.Ş.'):
    """Tek bir izin satırı üretir. Tarihler 'YYYY-MM-DD' string'i."""
    return {
        KIMLIK: calisan,
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
    assert not gercek_sonuc['Uyarı'].str.contains('resmi tatil listesi').any()


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


# ------------------------------------------- ücretsiz izin ve kıdem şartı

def test_ucretsiz_izin_raporsuz_personelde_de_duser():
    """Ücret ödenmediği ve SGK primi yatmadığı için rapor aranmaz."""
    sonuc = hesapla([satir(1, 'Ücretsiz İzin', '2026-07-27', '2026-07-31', 5,
                           'Kişisel Nedenler')])
    assert sonuc['Rapor Durumu'] == 'Raporsuz'
    assert sonuc['Ücretsiz İzin Kesintisi'] == 5
    assert sonuc['Destek Gün'] == 25


def test_ucretsiz_izin_resmi_tatili_kapsamaz():
    """13-24 Temmuz: 15 Temmuz tatil olduğu için 9 iş günü düşer."""
    sonuc = hesapla([satir(1, 'Ücretsiz İzin', '2026-07-13', '2026-07-24', 9,
                           'Kişisel Nedenler')])
    assert sonuc['Ücretsiz İzin Kesintisi'] == 9
    assert sonuc['Destek Gün'] == 21


def test_ucretsiz_izin_raporla_birlikte_mukerrer_sayilmaz():
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-10', 2),
        satir(1, 'Ücretsiz İzin', '2026-07-09', '2026-07-10', 2, 'Kişisel Nedenler'),
    ])
    assert sonuc['Rapor Gün'] == 2
    assert sonuc['Ücretsiz İzin Kesintisi'] == 0
    # 2 rapor + 2 hafta sonu + 1 resmi tatil
    assert sonuc['Toplam Kesinti'] == 5


def _kidem_satiri(ise_baslama, **kw):
    s = satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2, **kw)
    s[hesaplama.ISE_BASLAMA_KOLONU] = pd.Timestamp(ise_baslama)
    return s


def _kidem_rapor(ise_baslama):
    s = rapor(1, '2026-07-09', '2026-07-09', 1)
    s[hesaplama.ISE_BASLAMA_KOLONU] = pd.Timestamp(ise_baslama)
    return s


def test_bir_yildan_az_kidemde_yillik_izin_dusmez():
    """İş Kanunu Md. 53: hak edilmemiş yıllık izin, raporlu olsa bile düşmez."""
    sonuc = hesapla([_kidem_rapor('2026-03-02'), _kidem_satiri('2026-03-02')])
    assert sonuc['Yıllık İzin Kesintisi'] == 0
    assert 'kıdem' in sonuc['Uyarı']
    # 1 rapor + 2 hafta sonu + 1 resmi tatil
    assert sonuc['Toplam Kesinti'] == 4


def test_bir_yili_dolduran_kidemde_yillik_izin_duser():
    sonuc = hesapla([_kidem_rapor('2020-01-15'), _kidem_satiri('2020-01-15')])
    assert sonuc['Yıllık İzin Kesintisi'] == 2
    assert sonuc['Uyarı'] == ''
    assert sonuc['Toplam Kesinti'] == 6


@pytest.mark.parametrize('ise_baslama, beklenen', [
    ('2025-07-21', False),   # yıldönümüne 1 gün var
    ('2025-07-20', True),    # tam yıldönümü
    ('2025-07-19', True),    # yıldönümü geçmiş
    ('2026-01-01', False),
    ('2024-01-01', True),
    ('2024-02-29', True),    # artık gün: yıldönümü 28.02.2025 sayılır
])
def test_kidem_esigi(ise_baslama, beklenen):
    assert hesaplama.kidem_yeterli_mi(
        pd.Timestamp(ise_baslama), dt.date(2026, 7, 20)) is beklenen


def test_kidem_artik_yil_sinirinda_dogru():
    """29 Şubat'ta işe başlayanın yıldönümü, artık olmayan yılda 28 Şubat sayılır."""
    assert hesaplama.kidem_yeterli_mi(pd.Timestamp('2024-02-29'), dt.date(2025, 2, 28))
    assert not hesaplama.kidem_yeterli_mi(pd.Timestamp('2024-02-29'), dt.date(2025, 2, 27))


def test_ise_baslama_yoksa_kidem_sarti_uygulanmaz():
    """Bilgi yoksa kural uygulanmaz; yıllık izin normal şekilde düşer."""
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-09', 1),
        satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2),
    ])
    assert sonuc['Yıllık İzin Kesintisi'] == 2
    assert sonuc['Uyarı'] == ''


# ------------------------------------- Kural 3: yıllık izinde gün sayımı

@pytest.mark.parametrize('toplam, beklenen', [
    (0, 0),
    (0.5, 1),     # tek yarım gün -> 1 tam gün
    (1.0, 1),     # 0,5 + 0,5 -> 1 tam gün (iki ayrı gün değil)
    (1.5, 2),
    (2.0, 2),
    (3.5, 4),
])
def test_yillik_izin_yarim_gun_yuvarlamasi(toplam, beklenen):
    assert hesaplama.yillik_izin_kismi_kesintisi(toplam) == beklenen


def test_tek_yarim_gunluk_yillik_izin_tam_gun_sayilir():
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-09', 1),
        satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-20', 0.5),
    ])
    assert sonuc['Yıllık İzin Kesintisi'] == 1


def test_iki_ayri_yarim_gun_tek_tam_gun_sayilir():
    """0,5 + 0,5 farklı günlerde kullanılsa da toplam 1 tam gündür."""
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-09', 1),
        satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-20', 0.5),
        satir(1, 'Yıllık İzin', '2026-07-22', '2026-07-22', 0.5),
    ])
    assert sonuc['Yıllık İzin Kesintisi'] == 1


def test_yedi_yarim_gun_dort_tam_gun_sayilir():
    """Gerçek veride 1170 numaralı personelde görülen desen."""
    kayitlar = [rapor(1, '2026-07-09', '2026-07-09', 1)]
    for gun in (6, 7, 8, 10, 13, 14, 16):
        kayitlar.append(satir(1, 'Yıllık İzin', f'2026-07-{gun:02d}',
                              f'2026-07-{gun:02d}', 0.5))
    assert hesapla(kayitlar)['Yıllık İzin Kesintisi'] == 4


def test_dort_bucuk_saat_ustu_yillik_izin_tam_gun():
    """Eşiğin üzerindeki kısmi izin yarım değil tam gün sayılır."""
    kayit = satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-20', 0.625)  # 5 saat
    sonuc = hesapla([rapor(1, '2026-07-09', '2026-07-09', 1), kayit])
    assert sonuc['Yıllık İzin Kesintisi'] == 1

    kayit2 = satir(1, 'Yıllık İzin', '2026-07-22', '2026-07-22', 0.5)   # 4 saat
    sonuc2 = hesapla([rapor(1, '2026-07-09', '2026-07-09', 1), kayit, kayit2])
    # 1,0 + 0,5 = 1,5 -> 2 tam gün
    assert sonuc2['Yıllık İzin Kesintisi'] == 2


def test_tam_ve_yarim_gunluk_yillik_izin_birlikte():
    sonuc = hesapla([
        rapor(1, '2026-07-09', '2026-07-09', 1),
        satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2),      # 2 tam gün
        satir(1, 'Yıllık İzin', '2026-07-22', '2026-07-22', 0.5),    # + 1 gün
    ])
    assert sonuc['Yıllık İzin Kesintisi'] == 3


# ------------------------------------- kıdem kademeleri ve riskli işareti

@pytest.mark.parametrize('kidem, beklenen', [
    (0, 0), (1, 14), (4, 14), (5, 20), (14, 20), (15, 26), (30, 26),
])
def test_yillik_izin_hakki_kademeleri(kidem, beklenen):
    assert hesaplama.yillik_izin_hakki(kidem) == beklenen


def test_kidem_yili_hesabi():
    assert hesaplama.kidem_yili(pd.Timestamp('2020-07-15'), dt.date(2026, 7, 1)) == 5
    assert hesaplama.kidem_yili(pd.Timestamp('2020-06-15'), dt.date(2026, 7, 1)) == 6
    assert hesaplama.kidem_yili(None, dt.date(2026, 7, 1)) is None


def test_kidemsiz_yillik_izin_riskli_isaretlenir():
    """Raporsuz olsa bile İK'nın görmesi için işaretlenir."""
    sonuc = hesapla([_kidem_satiri('2026-03-02')])
    assert sonuc['Riskli'] == 'Evet'
    assert sonuc['Kıdem (Yıl)'] == 0
    assert sonuc['Yıllık İzin Hakkı'] == 0
    assert sonuc['Destek Gün'] == 30      # raporsuz, kesinti yok


def test_kidemli_personel_riskli_isaretlenmez():
    sonuc = hesapla([_kidem_satiri('2015-07-01')])
    assert sonuc['Riskli'] == ''
    assert sonuc['Kıdem (Yıl)'] == 11
    assert sonuc['Yıllık İzin Hakkı'] == 20


def test_ise_baslama_yoksa_kidem_kolonlari_bos():
    sonuc = hesapla([satir(1, 'Yıllık İzin', '2026-07-20', '2026-07-21', 2)])
    assert sonuc['Kıdem (Yıl)'] == ''
    assert sonuc['Yıllık İzin Hakkı'] == ''
    assert sonuc['Riskli'] == ''


# ---------------------------------------------- çok yıllı resmi tatil takvimi

def test_takvim_gelecek_yillari_kapsar():
    """Uygulama yıllarca kullanılacak; hiçbir yıl tatilsiz kalmamalı."""
    yillar = {g.year for g in hesaplama.RESMI_TATILLER}
    assert {2026, 2027, 2030, 2035} <= yillar
    for yil in range(2026, 2036):
        tatiller, _ = hesaplama.resmi_tatiller_yil(yil)
        assert len(tatiller) >= 15, f"{yil} yılında yalnızca {len(tatiller)} tatil"


@pytest.mark.parametrize('yil', [2026, 2027, 2030, 2035])
def test_sabit_tatiller_her_yil_uretilir(yil):
    """15 Temmuz, 1 Ocak gibi sabit tarihler her yıl takvimde olmalı."""
    tatiller, _ = hesaplama.resmi_tatiller_yil(yil)
    for ay, gun in [(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 28), (10, 29)]:
        assert dt.date(yil, ay, gun) in tatiller


def test_2026_takvimi_dogrulanmis_tarihlerle_uretilir():
    """Elle girilen 2026 tarihleri, önceki sabit listeyle birebir aynı olmalı."""
    tatiller, dogrulandi = hesaplama.resmi_tatiller_yil(2026)
    assert dogrulandi is True
    beklenen = {
        (1, 1), (3, 19), (3, 20), (3, 21), (3, 22), (4, 23), (5, 1), (5, 19),
        (5, 26), (5, 27), (5, 28), (5, 29), (5, 30), (7, 15), (8, 30), (10, 28), (10, 29),
    }
    assert {(g.month, g.day) for g in tatiller} == beklenen


def test_dogrulanmamis_yil_uyari_verir():
    """Hesaplanan dini bayram tarihleri sessizce doğru sayılmamalı."""
    assert hesaplama.takvim_dogrulandi_mi(2026) is True
    assert hesaplama.takvim_uyarisi((2026, 7)) is None

    assert hesaplama.takvim_dogrulandi_mi(2027) is False
    uyari = hesaplama.takvim_uyarisi((2027, 7))
    assert uyari and 'doğrulanmadı' in uyari and '2027' in uyari


def test_bayram_arifesi_ve_tum_gunleri_eklenir():
    """Ramazan arife + 3 gün, Kurban arife + 4 gün sürer."""
    tatiller, _ = hesaplama.resmi_tatiller_yil(2026)
    for gun in range(19, 23):                      # 19-22 Mart
        assert dt.date(2026, 3, gun) in tatiller
    assert dt.date(2026, 3, 23) not in tatiller
    for gun in range(26, 31):                      # 26-30 Mayıs
        assert dt.date(2026, 5, gun) in tatiller
    assert dt.date(2026, 5, 31) not in tatiller


def test_yilda_iki_kez_gecen_bayram_kaybolmaz():
    """2033'te Ramazan Bayramı hem Ocak hem Aralık ayında geçiyor."""
    bayramlar, _ = hesaplama._dini_bayram_baslangiclari(2033)
    ramazanlar = [t for ad, t in bayramlar if ad.startswith('ramazan')]
    assert len(ramazanlar) == 2
    assert {t.month for t in ramazanlar} == {1, 12}

    tatiller, _ = hesaplama.resmi_tatiller_yil(2033)
    assert dt.date(2033, 1, 3) in tatiller
    assert dt.date(2033, 12, 23) in tatiller


def test_ayar_dosyasindan_dini_bayram_dogrulanabilir(tmp_path):
    """Diyanet tarihi teyit edilince o yıl doğrulanmış sayılmalı."""
    yol = tmp_path / 'ayarlar.json'
    hesaplama.ayarlari_disa_aktar(yol)
    icerik = json.loads(yol.read_text(encoding='utf-8'))
    icerik['dogrulanmis_dini_bayramlar']['2027'] = {
        'ramazan': '11.03.2027', 'kurban': '18.05.2027',
    }
    yol.write_text(json.dumps(icerik, ensure_ascii=False), encoding='utf-8')

    onceki = dict(hesaplama.DOGRULANMIS_DINI_BAYRAMLAR)
    onceki_tatiller = set(hesaplama.RESMI_TATILLER)
    try:
        assert hesaplama.ayarlari_yukle(yol) is True
        assert hesaplama.takvim_dogrulandi_mi(2027) is True
        assert hesaplama.takvim_uyarisi((2027, 3)) is None
        tatiller, _ = hesaplama.resmi_tatiller_yil(2027)
        assert dt.date(2027, 3, 10) in tatiller       # arife
        assert dt.date(2027, 3, 13) in tatiller       # 3. gün
    finally:
        hesaplama.DOGRULANMIS_DINI_BAYRAMLAR = onceki
        hesaplama.RESMI_TATILLER = onceki_tatiller


# ------------------------------------------------------ ayar dosyası

def test_ayarlar_disa_aktarilip_geri_yuklenebilir(tmp_path):
    yol = tmp_path / 'ayarlar.json'
    hesaplama.ayarlari_disa_aktar(yol)
    assert yol.exists()

    icerik = json.loads(yol.read_text(encoding='utf-8'))
    assert 'kolon_esanlamlilari' in icerik
    assert icerik['tesvik_taban_gun'] == 30

    onceki = hesaplama.TESVIK_TABAN_GUN
    try:
        icerik['tesvik_taban_gun'] = 31
        yol.write_text(json.dumps(icerik, ensure_ascii=False), encoding='utf-8')
        assert hesaplama.ayarlari_yukle(yol) is True
        assert hesaplama.TESVIK_TABAN_GUN == 31
        assert hesaplama.ayar_uyarisi is None
    finally:
        hesaplama.TESVIK_TABAN_GUN = onceki


def test_bom_ile_kaydedilmis_ayar_dosyasi_okunur(tmp_path):
    """Not Defteri UTF-8 dosyayı BOM ile kaydedebilir; ayarlar yine geçerli olmalı."""
    yol = tmp_path / 'ayarlar.json'
    hesaplama.ayarlari_disa_aktar(yol)
    icerik = json.loads(yol.read_text(encoding='utf-8'))
    icerik['tesvik_taban_gun'] = 31
    yol.write_text(json.dumps(icerik, ensure_ascii=False), encoding='utf-8-sig')

    onceki = hesaplama.TESVIK_TABAN_GUN
    try:
        assert hesaplama.ayarlari_yukle(yol) is True
        assert hesaplama.ayar_uyarisi is None
        assert hesaplama.TESVIK_TABAN_GUN == 31
    finally:
        hesaplama.TESVIK_TABAN_GUN = onceki


def test_bozuk_ayar_dosyasi_varsayilana_doner(tmp_path):
    """Sessizce yanlış kuralla hesaplamak yerine uyarı bırakılmalı."""
    yol = tmp_path / 'ayarlar.json'
    yol.write_text('{ bozuk json', encoding='utf-8')
    assert hesaplama.ayarlari_yukle(yol) is False
    assert hesaplama.ayar_uyarisi and 'okunamadı' in hesaplama.ayar_uyarisi
    assert hesaplama.TESVIK_TABAN_GUN == 30
    hesaplama.ayar_uyarisi = None


def test_ayar_dosyasi_yoksa_varsayilanlar_kullanilir(tmp_path):
    assert hesaplama.ayarlari_yukle(tmp_path / 'olmayan.json') is False
    assert hesaplama.ayar_uyarisi is None
    assert hesaplama.TESVIK_TABAN_GUN == 30


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
    pd.DataFrame({'Konu': ['Test'], 'Tarih': ['2026-07-01']}).to_excel(yol, index=False)
    with pytest.raises(hesaplama.GirdiHatasi) as hata:
        hesaplama.oku(yol)
    mesaj = str(hata.value)
    assert 'İzin Türü' in mesaj              # eksik alanlar sayılır
    assert 'Konu' in mesaj                   # dosyadakiler de gösterilir


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
    kayit.update({'Sicil No': 'S-4471', 'Departman': 'Ar-Ge'})
    yol = _yaz(tmp_path, [kayit], kolon_adlari={KIMLIK: 'Çalışan Numarası'})
    sonuc = hesaplama.hesapla(hesaplama.oku(yol), TEMMUZ, TATILLER)

    assert sonuc['Sicil No'].iloc[0] == 'S-4471'
    assert sonuc['Departman'].iloc[0] == 'Ar-Ge'
    # Bilgi kolonları kimliğin hemen yanında olmalı.
    assert list(sonuc.columns)[:3] == ['Çalışan Numarası', 'Sicil No', 'Departman']
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
        KIMLIK: 'Sicil No',
        'İzin Başlangıç Tarihi': 'Başlangıç Tarihi',
        'İzin Bitiş Tarihi': 'Bitiş Tarihi',
        'İzin Türü': 'İzin Tipi',
        'quantityInDays': 'Gün Sayısı',
        'quantityInHours': 'Saat Sayısı',
    })
    sonuc = hesaplama.hesapla(hesaplama.oku(yol), TEMMUZ, TATILLER)
    # Kimlik kolonu çıktıda dosyadaki adıyla yer alır.
    assert sonuc.columns[0] == 'Sicil No'
    assert sonuc['Sicil No'].iloc[0] == 1
    assert sonuc['Rapor Durumu'].iloc[0] == 'Raporlu'
    assert sonuc['Destek Gün'].iloc[0] == 26


def test_ad_soyad_kimlik_olarak_kabul_edilir(tmp_path):
    """Dosyada çalışan numarası yoksa Ad Soyad kimlik olarak kullanılmalı."""
    yol = _yaz(tmp_path, [rapor('Ayşe Yılmaz', '2026-07-09', '2026-07-09', 1)],
               kolon_adlari={KIMLIK: 'Ad Soyad'})
    veri = hesaplama.oku(yol)
    assert veri.attrs['kimlik_ad'] == 'Ad Soyad'
    sonuc = hesaplama.hesapla(veri, TEMMUZ, TATILLER)
    assert sonuc.columns[0] == 'Ad Soyad'
    assert sonuc['Ad Soyad'].iloc[0] == 'Ayşe Yılmaz'
    assert sonuc['Destek Gün'].iloc[0] == 26


def test_calisan_numarasi_ad_soyada_tercih_edilir(tmp_path):
    """İkisi de varsa numara kimlik olur, ad soyad bilgi kolonu olarak taşınır."""
    kayit = rapor(7, '2026-07-09', '2026-07-09', 1)
    kayit['Ad Soyad'] = 'Ayşe Yılmaz'
    yol = _yaz(tmp_path, [kayit], kolon_adlari={KIMLIK: 'Çalışan Numarası'})
    sonuc = hesaplama.hesapla(hesaplama.oku(yol), TEMMUZ, TATILLER)
    assert list(sonuc.columns)[:2] == ['Çalışan Numarası', 'Ad Soyad']
    assert sonuc['Çalışan Numarası'].iloc[0] == 7


def test_elle_eslestirme_taninmayan_kolonlari_cozer(tmp_path):
    """Hiçbir kolon adı tanınmasa bile elle eşleştirmeyle hesap yapılabilmeli."""
    yol = _yaz(tmp_path, [rapor('P-1', '2026-07-09', '2026-07-09', 1)], kolon_adlari={
        KIMLIK: 'KOD', 'İzin Türü': 'Kategori', 'İzin Nedeni': 'Alt',
        'İzin Başlangıç Tarihi': 'Bas', 'İzin Bitiş Tarihi': 'Bit',
        'quantityInDays': 'Adet', 'quantityInHours': 'Sure', 'Şirket': 'Birim',
    })
    _, _, eksik = hesaplama.kolonlari_incele(yol)
    assert set(eksik) == set(hesaplama.KOLONLAR)     # hiçbiri tanınmadı

    elle = {'KOD': KIMLIK, 'Kategori': 'İzin Türü', 'Alt': 'İzin Nedeni',
            'Bas': 'İzin Başlangıç Tarihi', 'Bit': 'İzin Bitiş Tarihi',
            'Adet': 'quantityInDays', 'Sure': 'quantityInHours', 'Birim': 'Şirket'}
    sonuc = hesaplama.hesapla(hesaplama.oku(yol, elle), TEMMUZ, TATILLER)
    assert sonuc.columns[0] == 'KOD'
    assert sonuc['Destek Gün'].iloc[0] == 26


def test_buyuk_kucuk_harf_ve_bosluk_farki_onemsiz(tmp_path):
    yol = _yaz(tmp_path, [rapor(1, '2026-07-09', '2026-07-09', 1)], kolon_adlari={
        KIMLIK: '  ÇALIŞAN NUMARASI ',
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


def test_veri_sayfasi_cok_sayfali_dosyada_bulunur(tmp_path):
    """'Kurallar' gibi yardımcı sayfalar atlanıp veri sayfası seçilmeli."""
    yol = tmp_path / 'coksayfa.xlsx'
    veri_df = pd.DataFrame([rapor(1, '2026-07-09', '2026-07-09', 1)])
    kurallar = pd.DataFrame({'Kural': ['Kural 1', 'Kural 2'],
                             'Açıklama': ['Metin', 'Metin']})
    with pd.ExcelWriter(yol, engine='openpyxl') as writer:
        kurallar.to_excel(writer, index=False, sheet_name='Kurallar')
        veri_df.to_excel(writer, index=False, sheet_name='İzin Raporu', startrow=2)

    veri = hesaplama.oku(yol)
    assert len(veri) == 1
    assert hesaplama.hesapla(veri, TEMMUZ, TATILLER)['Destek Gün'].iloc[0] == 26


def test_ise_baslama_tarihi_okunabilir_bicimde_tasinir(tmp_path):
    kayit = rapor(1, '2026-07-09', '2026-07-09', 1)
    kayit[hesaplama.ISE_BASLAMA_KOLONU] = pd.Timestamp('2020-01-15')
    sonuc = hesaplama.hesapla(hesaplama.oku(_yaz(tmp_path, [kayit])), TEMMUZ, TATILLER)
    assert sonuc[hesaplama.ISE_BASLAMA_KOLONU].iloc[0] == '15.01.2020'


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
