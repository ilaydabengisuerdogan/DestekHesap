import streamlit as st
import pandas as pd
import io

# Sayfa Ayarları
st.set_page_config(page_title="Teknopark Destek Hesaplama", page_icon="🏢", layout="wide")

def process_data(df):
    """
    Excel'den gelen puantaj verisini işleyerek destek gün ve saatini hesaplar.
    """
    # 1. Kolon Doğrulama
    beklenen_kolonlar = ['Sicil No / TC', 'Ad Soyad', 'Tarih', 'Çalışılan Saat', 'Devamsızlık Tipi']
    eksik_kolonlar = [col for col in beklenen_kolonlar if col not in df.columns]
    
    if eksik_kolonlar:
        return False, f"Hata: Yüklenen dosyada şu kolonlar eksik: {', '.join(eksik_kolonlar)}"
    
    # 2. Veri Temizleme ve Hazırlık
    # Tarih kolonunu datetime'a çevir
    try:
        df['Tarih'] = pd.to_datetime(df['Tarih'])
    except Exception as e:
        return False, f"Hata: 'Tarih' kolonu geçerli bir tarih formatında değil. Detay: {e}"
        
    # Boş verileri temizle (Örn: Sicil No boş olan satırları yoksay)
    df = df.dropna(subset=['Sicil No / TC', 'Tarih'])
    
    # Aynı gün için mükerrer kayıtları temizle (TC-11)
    df = df.drop_duplicates(subset=['Sicil No / TC', 'Tarih'], keep='first')
    
    # Hafta içi mi kontrolü (0=Pzt, 6=Paz)
    df['Gun_Indeks'] = df['Tarih'].dt.dayofweek
    df['Hafta_Ici'] = df['Gun_Indeks'] < 5
    
    # Hafta ve Yıl bilgisi (ISO Takvimi) - TC-09 için Pazartesi başlangıçlı gruplama
    df['Yıl'] = df['Tarih'].dt.isocalendar().year
    df['Hafta'] = df['Tarih'].dt.isocalendar().week
    
    # Sadece hafta içi günlerini filtrele (Kesintiler hafta içi günlerinden düşülür)
    df_hafta_ici = df[df['Hafta_Ici'] == True].copy()
    
    # Kesinti Sayılacak Devamsızlık Tipleri
    kesinti_tipleri = ['Yıllık İzin', 'Rapor', 'Resmi Tatil', 'Ücretsiz İzin']
    df_hafta_ici['Kesinti_Mi'] = df_hafta_ici['Devamsızlık Tipi'].isin(kesinti_tipleri)
    
    # 3. Hesaplama (Çalışan ve Hafta bazında gruplama)
    sonuclar = []
    
    gruplar = df_hafta_ici.groupby(['Sicil No / TC', 'Ad Soyad', 'Yıl', 'Hafta'])
    
    for (sicil, ad, yil, hafta), grup in gruplar:
        # Toplam kesinti gün sayısı (Aynı güne ait mükerrerleri zaten sildik)
        kesinti_gun_sayisi = grup['Kesinti_Mi'].sum()
        
        # Destek Formülü: 5 iş günü - Kesinti Gün Sayısı
        # (Kesinti 5'ten büyük olamaz, güvenlik amaçlı max(0, ...) kullanıyoruz)
        destek_gun = max(0, 5 - kesinti_gun_sayisi)
        destek_saat = destek_gun * 8
        
        # O haftanın başlangıç tarihi (Pazartesi) gösterim amaçlı
        hafta_baslangic = grup['Tarih'].min() - pd.Timedelta(days=grup['Tarih'].min().dayofweek)
        hafta_bitis = hafta_baslangic + pd.Timedelta(days=6)
        hafta_etiket = f"{hafta_baslangic.strftime('%d.%m.%Y')} - {hafta_bitis.strftime('%d.%m.%Y')}"
        
        sonuclar.append({
            'Sicil No / TC': sicil,
            'Ad Soyad': ad,
            'Yıl': yil,
            'Hafta': hafta,
            'Hafta Aralığı': hafta_etiket,
            'Kesinti Gün Sayısı': kesinti_gun_sayisi,
            'Destek Gün': destek_gun,
            'Destek Saat': destek_saat
        })
        
    sonuc_df = pd.DataFrame(sonuclar)
    return True, sonuc_df

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
st.markdown('<p class="sub-title">Puantaj Excel dosyalarınızı saniyeler içinde işleyin ve desteğe esas gün/saat miktarlarını hatasız hesaplayın.</p>', unsafe_allow_html=True)

with st.expander("ℹ️ Hesaplama Kuralları ve Detaylar", expanded=False):
    st.markdown("""
    - Haftalık norm **5 iş günü** ve **40 saattir**.
    - Destek hesaplaması yalnızca hafta içi günleri (Pzt-Cuma) baz alır.
    - **Rapor, Resmi Tatil, Yıllık İzin, Ücretsiz İzin** gibi devamsızlıklar destek gününden düşülür (1 tam gün = 8 saat).
    - Hafta sonuna denk gelen devamsızlıklar destek süresini etkilemez (zaten dahil edilmemiştir).
    """)

# Dosya Yükleme Alanı
col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader("Puantaj Excel Dosyasını Sürükleyin veya Seçin", type=['xlsx', 'xls'])

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True) # Hizalama için
    hesapla_btn = st.button("🚀 Verileri Hesapla", use_container_width=True)

if uploaded_file is not None and hesapla_btn:
    with st.spinner("✨ Veriler işleniyor, lütfen bekleyin..."):
        try:
            # Veriyi oku
            df = pd.read_excel(uploaded_file)
            
            # İşle
            basarili, sonuc = process_data(df)
            
            if not basarili:
                st.error(sonuc) # Hata mesajını göster
            else:
                st.toast('Hesaplama Başarılı!', icon='✅')
                
                # --- Özet Metrikler ---
                st.markdown("### 📊 Genel Özet")
                m1, m2, m3 = st.columns(3)
                toplam_calisan = sonuc['Sicil No / TC'].nunique()
                toplam_hafta = sonuc.shape[0]
                toplam_destek_saat = sonuc['Destek Saat'].sum()
                
                with m1:
                    st.metric("Toplam Çalışan", f"{toplam_calisan} Kişi")
                with m2:
                    st.metric("İncelenen Hafta Kaydı", f"{toplam_hafta} Kayıt")
                with m3:
                    st.metric("Toplam Destek Saati", f"{toplam_destek_saat} Saat")
                
                st.divider()
                
                # Sonuçları göster
                st.markdown("### 📑 Hesaplama Sonuçları")
                st.dataframe(sonuc, use_container_width=True, height=400)
                
                # İndirme işlemi için veriyi Excel'e çevir
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    sonuc.to_excel(writer, index=False, sheet_name='Destek_Sonuclari')
                
                # Stream pointer'ı başa al
                buffer.seek(0)
                
                col3, col4, col5 = st.columns([1, 2, 1])
                with col4:
                    st.download_button(
                        label="📥 Excel Olarak Bilgisayarına İndir",
                        data=buffer,
                        file_name="teknopark_destek_sonuclari.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
        except Exception as e:
            st.error(f"Beklenmeyen bir hata oluştu: {e}")

