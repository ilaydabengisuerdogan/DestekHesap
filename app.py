import datetime as dt
import io

import streamlit as st

import hesaplama

# Sayfa Ayarları
st.set_page_config(page_title="Teknopark Destek Hesaplama", page_icon="🏢", layout="wide")

AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
         'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

# --- ÖZEL CSS (ŞIK TASARIM) ---
st.markdown("""
<style>
    /* Genel Arka Plan ve Yazı Tipleri */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Inter', sans-serif;
    }

    /* Başlık Stili */
    .main-title {
        color: #1e3c72;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0px;
        padding-bottom: 10px;
    }

    .sub-title {
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }

    /* Buton Stilleri */
    div.stButton > button:first-child {
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.2);
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background-color: #1d4ed8;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
        color: white;
    }
    div.stButton > button:first-child:active {
        background-color: #1e40af;
    }

    /* İndirme Butonu Stili */
    div.stDownloadButton > button:first-child {
        background-color: #10b981;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.2s ease;
        box-shadow: 0 2px 5px rgba(16, 185, 129, 0.2);
    }
    div.stDownloadButton > button:first-child:hover {
        background-color: #059669;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
        color: white;
    }
    div.stDownloadButton > button:first-child:active {
        background-color: #047857;
    }

    /* Yükleme Alanı Çerçevesi */
    .stFileUploader {
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 10px;
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- UI Tasarımı ---
st.markdown('<h1 class="main-title">🏢 Teknopark Destek Hesaplama</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">İzin raporu Excel dosyanızı saniyeler içinde işleyin ve desteğe esas gün/saat miktarlarını hatasız hesaplayın.</p>', unsafe_allow_html=True)

with st.expander("ℹ️ Hesaplama Kuralları ve Detaylar", expanded=False):
    st.markdown(f"""
    Teşvik **{hesaplama.TESVIK_TABAN_GUN} gün** üzerinden hesaplanır. Belirleyici kriter,
    personelin o ay içinde **sağlık raporu** (hastalık raporu veya kadın doğum istirahati) olup olmadığıdır.

    **Raporu olmayan personel** — yıllık izin, resmi tatil ve mazeret izni teşvikten **düşmez**;
    tam {hesaplama.TESVIK_TABAN_GUN} gün destek alır.

    **Raporu olan personel** — haftalık çalışma saatini tamamlayamadığı için şu kalemler düşülür:
    1. **Rapor günleri** — rapor aralığına düşen iş günleri.
    2. **Hafta sonu** — raporun değdiği *her* haftanın Cumartesi ve Pazar günleri.
    3. **Yıllık izin** — o ay içinde kullanılan yıllık izin günleri.
    4. **Resmi tatiller** — o ay içindeki hafta içine denk gelen resmi tatiller.
    5. **Kısmi rapor** — saatlik raporlar birikimli toplanır; artan kısım yarım günü aşmıyorsa
       yarım gün, aşıyorsa tam gün olarak düşülür.

    **Mazeret İzni** (doktor randevusu, doğum günü izni vb.) ve **Evlilik İzni** teşvikten
    düşmez — raporlu personelde dahi.

    Hafta sonu yalnızca **dönem ayının içine düşerse** sayılır. Ay sonu haftasının hafta sonu
    bir sonraki aya taşıyorsa (örn. 27-31 Temmuz haftasının 1-2 Ağustos'u) bu dönemden düşmez.

    `Destek Saat = Destek Gün × {hesaplama.GUNLUK_SAAT}` olarak hesaplanır.
    """)

# Dosya Yükleme Alanı
col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader("İzin Raporu Excel Dosyasını Sürükleyin veya Seçin", type=['xlsx', 'xls'])

# Dosya okundukça dönem/tatil ayarlarını hazırla; hesaplama butonuna basılmadan
# kullanıcı bunları gözden geçirebilsin.
veri = None
hata_mesaji = None
if uploaded_file is not None:
    try:
        veri = hesaplama.oku(uploaded_file)
    except hesaplama.GirdiHatasi as hata:
        hata_mesaji = str(hata)

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)  # Hizalama için
    hesapla_btn = st.button("🚀 Verileri Hesapla", width='stretch', disabled=veri is None)

if hata_mesaji:
    st.error(hata_mesaji)

if veri is not None:
    tespit_yil, tespit_ay = hesaplama.donem_tespit(veri)

    st.markdown("#### ⚙️ Dönem ve Resmi Tatil Ayarları")
    a1, a2, a3 = st.columns([1, 1, 3])
    with a1:
        yil = st.number_input("Yıl", min_value=2020, max_value=2100, value=tespit_yil, step=1)
    with a2:
        ay = st.selectbox("Ay", options=list(range(1, 13)),
                          index=tespit_ay - 1, format_func=lambda a: AYLAR[a - 1])

    donem = (int(yil), int(ay))
    varsayilan_tatiller = hesaplama.donem_tatilleri(donem)
    with a3:
        tatil_metni = st.text_input(
            f"{AYLAR[ay - 1]} {yil} resmi tatilleri (gg.aa.yyyy, virgülle ayrılmış)",
            value=", ".join(f"{g:%d.%m.%Y}" for g in varsayilan_tatiller),
            help="Takvimde eksik/fazla tatil varsa buradan düzeltin. Sapmalar çıktıdaki 'Uyarı' kolonunda da bildirilir.",
        )

    # Dönem dışı tatiller korunur; tutarlılık uyarısı ay dışına taşan izinleri de kontrol ediyor.
    tatiller = {g for g in hesaplama.RESMI_TATILLER if g not in varsayilan_tatiller}
    gecersiz = []
    for parca in tatil_metni.split(','):
        parca = parca.strip()
        if not parca:
            continue
        try:
            tatiller.add(dt.datetime.strptime(parca, '%d.%m.%Y').date())
        except ValueError:
            gecersiz.append(parca)
    if gecersiz:
        st.warning("Tarih olarak okunamayan girdiler yok sayıldı: " + ", ".join(gecersiz))

    # Sonuçları session state'te tutuyoruz; aksi halde tablo filtresi gibi bir
    # widget'a dokunulduğunda st.button tekrar False dönüp sonuçlar kaybolur.
    ayarlar = (getattr(uploaded_file, 'name', ''), getattr(uploaded_file, 'size', 0),
               donem, tuple(sorted(tatiller)))
    if st.session_state.get('ayarlar') != ayarlar:
        st.session_state.pop('sonuc', None)  # ayar değişti, eski sonuç geçersiz

    if hesapla_btn:
        with st.spinner("✨ Veriler işleniyor, lütfen bekleyin..."):
            try:
                st.session_state['sonuc'] = hesaplama.hesapla(veri, donem, tatiller)
                st.session_state['ayarlar'] = ayarlar
            except Exception as hata:
                st.error(f"Beklenmeyen bir hata oluştu: {hata}")
            else:
                st.toast('Hesaplama Başarılı!', icon='✅')

    sonuc = st.session_state.get('sonuc')
    if sonuc is not None:
        # --- Özet Metrikler ---
        st.markdown("### 📊 Genel Özet")
        raporlu = sonuc[sonuc['Rapor Durumu'] == 'Raporlu']
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Toplam Personel", f"{len(sonuc)} Kişi")
        with m2:
            st.metric("Raporlu Personel", f"{len(raporlu)} Kişi")
        with m3:
            st.metric("Toplam Destek Günü", f"{sonuc['Destek Gün'].sum():,.1f} Gün")
        with m4:
            st.metric("Toplam Kesinti", f"{sonuc['Toplam Kesinti'].sum():,.1f} Gün")

        uyarililar = sonuc[sonuc['Uyarı'] != '']
        if not uyarililar.empty:
            st.warning(
                f"{len(uyarililar)} personelde izin gün sayısı ile resmi tatil takvimi "
                "uyuşmuyor. Ayrıntı için sonuç tablosundaki 'Uyarı' kolonuna bakın."
            )

        st.divider()

        # Sonuçları göster
        st.markdown("### 📑 Hesaplama Sonuçları")
        sadece_kesintili = st.checkbox(
            "Yalnızca kesintisi olan personeli göster", value=True,
            help=f"Kesintisi olmayan personel tam {hesaplama.TESVIK_TABAN_GUN} gün destek alır.",
        )
        gosterilen = sonuc[sonuc['Toplam Kesinti'] > 0] if sadece_kesintili else sonuc

        if gosterilen.empty:
            st.info("Bu dönemde kesintisi olan personel bulunmuyor.")
        else:
            st.dataframe(
                gosterilen.style.apply(
                    lambda satir: ['background-color: #fef2f2'] * len(satir)
                    if satir['Rapor Durumu'] == 'Raporlu' else [''] * len(satir),
                    axis=1,
                ),
                width='stretch',
                height=400,
            )

        # İki ayrı indirme: tüm personel ve yalnızca kesintisi olanlar.
        EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        donem_eki = f"{donem[0]}_{donem[1]:02d}"

        tumu_buffer = io.BytesIO()
        hesaplama.excel_yaz(sonuc, tumu_buffer)
        tumu_buffer.seek(0)

        kesintililer = hesaplama.kesintili_personel(sonuc)

        col3, col4 = st.columns(2)
        with col3:
            st.download_button(
                label=f"📥 Tüm Personel ({len(sonuc)} kişi)",
                data=tumu_buffer,
                file_name=f"teknopark_destek_{donem_eki}.xlsx",
                mime=EXCEL_MIME,
                width='stretch',
            )
        with col4:
            if kesintililer.empty:
                st.button("Kesintisi olan personel yok", disabled=True, width='stretch')
            else:
                kesintili_buffer = io.BytesIO()
                hesaplama.excel_yaz(kesintililer, kesintili_buffer,
                                    sayfa_adi='Kesintili_Personel')
                kesintili_buffer.seek(0)
                st.download_button(
                    label=f"📥 Kesintisi Olanlar ({len(kesintililer)} kişi)",
                    data=kesintili_buffer,
                    file_name=f"teknopark_destek_{donem_eki}_kesintili.xlsx",
                    mime=EXCEL_MIME,
                    width='stretch',
                )
