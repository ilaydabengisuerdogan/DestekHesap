"""
Teknopark Destek Hesaplama — masaüstü arayüzü.

Python kurulumu gerektirmeyen tek dosya .exe olarak paketlenmek üzere yazılmıştır
(bkz. paketle.py). İnternet bağlantısı gerektirmez.

Hesaplama mantığı hesaplama.py içindedir; bu dosya yalnızca arayüzdür.
"""

import datetime as dt
import os
import queue
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

import hesaplama

AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
         'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

LACIVERT = '#1e3c72'
MAVI = '#2563eb'
YESIL = '#10b981'
ZEMIN = '#f8f9fa'
GRI = '#6c757d'

# Tabloda gösterilmeyen kolonlar (renkle/uyarı alanıyla zaten aktarılıyor).
GIZLI_KOLONLAR = {'Dönem', 'Rapor Durumu', 'Uyarı'}

# Bilinen kolonların genişlikleri; listede olmayan (Ad Soyad, Sicil No gibi
# sonradan eklenen) kolonlar VARSAYILAN_GENISLIK ile gösterilir.
KOLON_GENISLIKLERI = {
    'Çalışan Numarası': 110,
    'Şirket': 175,
    'Rapor Türü': 190,
    'Rapor Gün': 80,
    'Hafta Sonu Kesintisi': 130,
    'Yıllık İzin Kesintisi': 130,
    'Resmi Tatil Kesintisi': 130,
    'Kısmi Rapor Kesintisi': 130,
    'Toplam Kesinti': 100,
    'Destek Gün': 90,
    'Destek Saat': 90,
}
VARSAYILAN_GENISLIK = 150
SOLA_YASLI = {'Şirket', 'Rapor Türü'}


YOK = "— (kolon yok) —"

# Eşleştirme ekranında kolonların ne işe yaradığını anlatan açıklamalar.
KOLON_ACIKLAMALARI = {
    hesaplama.KIMLIK_KOLONU: "Personeli tanımlayan kolon — çalışan numarası veya ad soyad",
    'Şirket': "Personelin bağlı olduğu şirket",
    'İzin Türü': "Yıllık İzin / Mazeret İzni / Ücretsiz İzin / Şirket Dışında Olma Nedeni",
    'İzin Nedeni': "Alt kırılım — rapor tespiti buradan yapılır",
    'İzin Başlangıç Tarihi': "İznin ilk günü",
    'İzin Bitiş Tarihi': "İznin son günü",
    'quantityInDays': "İzin gün sayısı",
    'quantityInHours': "İzin saat sayısı",
    hesaplama.ISE_BASLAMA_KOLONU: "Kıdem hesabı için — yoksa kıdem şartı uygulanmaz",
}


class KolonEslestirme(tk.Toplevel):
    """
    Dosyadaki kolonları programın beklediği alanlara eşleştirme penceresi.

    Dosya yapısı değiştiğinde kod değiştirmeden uyarlama yapılabilsin diye var.
    Kapatılırsa `sonuc` None kalır; onaylanırsa {dosya_basligi: beklenen} döner.
    """

    def __init__(self, ana, basliklar, mevcut_eslesme, hedefler, tumu=False):
        super().__init__(ana)
        self.sonuc = None
        self.title("Kolon Eşleştirme")
        self.configure(bg=ZEMIN)
        self.resizable(False, False)
        self.transient(ana)

        # Hangi alanlar gösterilecek: yalnızca eksikler ya da tamamı.
        gosterilecek = list(hesaplama.KOLONLAR) if tumu else list(hedefler)
        if tumu and hesaplama.ISE_BASLAMA_KOLONU not in gosterilecek:
            gosterilecek.append(hesaplama.ISE_BASLAMA_KOLONU)

        # beklenen -> dosyadaki başlık (ters çevrilmiş eşleşme)
        ters = {v: k for k, v in mevcut_eslesme.items()}

        dis = ttk.Frame(self, padding=18)
        dis.pack(fill='both', expand=True)

        ttk.Label(dis, text="Kolon Eşleştirme", style='Baslik2.TLabel').pack(anchor='w')
        aciklama = ("Dosyadaki kolonlar otomatik tanınamadı. Aşağıdan hangi kolonun "
                    "ne olduğunu seçin." if not tumu else
                    "Program kolonları otomatik tanıdı. Yanlış eşleşen varsa düzeltebilirsiniz.")
        ttk.Label(dis, text=aciklama, style='AltBaslik.TLabel',
                  wraplength=560).pack(anchor='w', pady=(2, 14))

        izgara = ttk.Frame(dis)
        izgara.pack(fill='x')
        ttk.Label(izgara, text="PROGRAMIN BEKLEDİĞİ", style='Kucuk.TLabel').grid(
            row=0, column=0, sticky='w', pady=(0, 6))
        ttk.Label(izgara, text="DOSYADAKİ KOLON", style='Kucuk.TLabel').grid(
            row=0, column=1, sticky='w', padx=(14, 0), pady=(0, 6))

        secenekler = [YOK] + [str(b) for b in basliklar]
        self.secimler = {}
        for i, hedef in enumerate(gosterilecek, start=1):
            zorunlu = hedef in hesaplama.KOLONLAR
            etiket = hedef + (" *" if zorunlu else "  (isteğe bağlı)")
            ttk.Label(izgara, text=etiket).grid(row=i, column=0, sticky='w', pady=3)

            degisken = tk.StringVar(value=str(ters.get(hedef, YOK)))
            ttk.Combobox(izgara, values=secenekler, textvariable=degisken,
                         state='readonly', width=34).grid(
                row=i, column=1, sticky='we', padx=(14, 0), pady=3)
            self.secimler[hedef] = degisken

            ipucu = KOLON_ACIKLAMALARI.get(hedef, "")
            if ipucu:
                ttk.Label(izgara, text=ipucu, style='Kucuk.TLabel').grid(
                    row=i, column=2, sticky='w', padx=(12, 0), pady=3)

        ttk.Label(dis, text="* işaretli alanlar zorunludur.",
                  style='AltBaslik.TLabel').pack(anchor='w', pady=(14, 0))

        dugmeler = ttk.Frame(dis)
        dugmeler.pack(fill='x', pady=(14, 0))
        ttk.Button(dugmeler, text="Tamam", style='Mavi.TButton',
                   command=self._onayla).pack(side='right')
        ttk.Button(dugmeler, text="Vazgeç", command=self.destroy).pack(
            side='right', padx=(0, 8))

        self.bind('<Escape>', lambda e: self.destroy())
        self.update_idletasks()
        x = ana.winfo_rootx() + (ana.winfo_width() - self.winfo_width()) // 2
        y = ana.winfo_rooty() + 80
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        ana.wait_window(self)

    def _onayla(self):
        eslesme, kullanilan = {}, {}
        for hedef, degisken in self.secimler.items():
            secim = degisken.get()
            if secim == YOK:
                continue
            if secim in kullanilan:
                messagebox.showwarning(
                    "Aynı kolon iki kez seçildi",
                    f"'{secim}' hem {kullanilan[secim]} hem {hedef} olarak seçilmiş.\n\n"
                    "Her kolon yalnızca bir alana atanabilir.", parent=self)
                return
            kullanilan[secim] = hedef
            eslesme[secim] = hedef

        eksik = [k for k in hesaplama.KOLONLAR if k not in eslesme.values()]
        if eksik:
            messagebox.showwarning(
                "Zorunlu alan seçilmedi",
                "Şu zorunlu alanlar için kolon seçilmedi:\n\n  "
                + "\n  ".join(eksik), parent=self)
            return

        self.sonuc = eslesme
        self.destroy()


class Uygulama(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Teknopark Destek Hesaplama")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.configure(bg=ZEMIN)

        self.dosya_yolu = None
        self.veri = None
        self.sonuc = None
        self.elle_eslesme = None
        self._kuyruk = queue.Queue()

        self._stil_kur()
        self._arayuzu_kur()

    # ------------------------------------------------------------- görünüm

    def _stil_kur(self):
        stil = ttk.Style(self)
        try:
            stil.theme_use('clam')
        except tk.TclError:
            pass
        stil.configure('.', background=ZEMIN, font=('Segoe UI', 10))
        stil.configure('TFrame', background=ZEMIN)
        stil.configure('TLabel', background=ZEMIN)
        stil.configure('TLabelframe', background=ZEMIN)
        stil.configure('TLabelframe.Label', background=ZEMIN, foreground=LACIVERT,
                       font=('Segoe UI', 10, 'bold'))
        stil.configure('TCheckbutton', background=ZEMIN)
        stil.configure('Baslik.TLabel', font=('Segoe UI', 20, 'bold'), foreground=LACIVERT)
        stil.configure('Baslik2.TLabel', font=('Segoe UI', 13, 'bold'), foreground=LACIVERT)
        stil.configure('AltBaslik.TLabel', font=('Segoe UI', 10), foreground=GRI)
        stil.configure('Kucuk.TLabel', font=('Segoe UI', 8), foreground=GRI)
        stil.configure('Dosya.TLabel', font=('Segoe UI', 10, 'bold'), foreground=LACIVERT)
        stil.configure('Metrik.TLabel', font=('Segoe UI', 17, 'bold'), foreground=LACIVERT)
        stil.configure('MetrikBaslik.TLabel', font=('Segoe UI', 9), foreground=GRI)
        stil.configure('Uyari.TLabel', foreground='#b45309', font=('Segoe UI', 9))
        stil.configure('Treeview', rowheight=24, fieldbackground='white', background='white')
        stil.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

        for ad, renk, koyu in (('Mavi', MAVI, '#1d4ed8'), ('Yesil', YESIL, '#059669')):
            stil.configure(f'{ad}.TButton', background=renk, foreground='white',
                           font=('Segoe UI', 10, 'bold'), borderwidth=0, padding=(16, 9))
            stil.map(f'{ad}.TButton',
                     background=[('active', koyu), ('disabled', '#cbd5e1')],
                     foreground=[('disabled', '#94a3b8')])

    def _arayuzu_kur(self):
        dis = ttk.Frame(self, padding=18)
        dis.pack(fill='both', expand=True)

        ttk.Label(dis, text="🏢 Teknopark Destek Hesaplama", style='Baslik.TLabel').pack(anchor='w')
        ttk.Label(dis, text="İzin raporu Excel dosyasını seçin, desteğe esas gün/saat miktarı hesaplansın.",
                  style='AltBaslik.TLabel').pack(anchor='w', pady=(2, 14))

        # --- 1. Dosya seçimi
        kutu1 = ttk.LabelFrame(dis, text=" 1. İzin Raporu Dosyası ", padding=12)
        kutu1.pack(fill='x')
        ttk.Button(kutu1, text="📂  Dosya Seç...", style='Mavi.TButton',
                   command=self.dosya_sec).pack(side='left')
        self.eslestir_dugmesi = ttk.Button(
            kutu1, text="Kolonları Eşleştir...", command=self.eslestirmeyi_duzenle,
            state='disabled')
        self.eslestir_dugmesi.pack(side='left', padx=(10, 0))
        self.dosya_etiketi = ttk.Label(kutu1, text="Henüz dosya seçilmedi.", style='AltBaslik.TLabel')
        self.dosya_etiketi.pack(side='left', padx=14)

        # --- 2. Dönem ve tatil ayarları
        kutu2 = ttk.LabelFrame(dis, text=" 2. Dönem ve Resmi Tatiller ", padding=12)
        kutu2.pack(fill='x', pady=12)

        ttk.Label(kutu2, text="Yıl:").grid(row=0, column=0, sticky='w')
        self.yil_degeri = tk.StringVar(value=str(dt.date.today().year))
        self.yil_kutusu = ttk.Spinbox(kutu2, from_=2020, to=2100, width=8,
                                      textvariable=self.yil_degeri, command=self.donem_degisti)
        self.yil_kutusu.grid(row=0, column=1, sticky='w', padx=(6, 20))
        self.yil_kutusu.bind('<FocusOut>', lambda e: self.donem_degisti())

        ttk.Label(kutu2, text="Ay:").grid(row=0, column=2, sticky='w')
        self.ay_degeri = tk.StringVar(value=AYLAR[dt.date.today().month - 1])
        self.ay_kutusu = ttk.Combobox(kutu2, values=AYLAR, textvariable=self.ay_degeri,
                                      state='readonly', width=12)
        self.ay_kutusu.grid(row=0, column=3, sticky='w', padx=(6, 20))
        self.ay_kutusu.bind('<<ComboboxSelected>>', lambda e: self.donem_degisti())

        ttk.Label(kutu2, text="Resmi tatiller:").grid(row=0, column=4, sticky='w')
        self.tatil_degeri = tk.StringVar()
        ttk.Entry(kutu2, textvariable=self.tatil_degeri, width=46).grid(
            row=0, column=5, sticky='we', padx=(6, 0))
        kutu2.columnconfigure(5, weight=1)
        ttk.Label(kutu2, text="Dönem ve tatiller dosyadan otomatik doldurulur. "
                              "Tatil listesi hatalıysa gg.aa.yyyy biçiminde, virgülle ayırarak düzeltin.",
                  style='AltBaslik.TLabel').grid(row=1, column=0, columnspan=6, sticky='w', pady=(8, 0))

        # --- 3. Hesapla
        kutu3 = ttk.Frame(dis)
        kutu3.pack(fill='x')
        self.hesapla_dugmesi = ttk.Button(kutu3, text="🚀  HESAPLA", style='Mavi.TButton',
                                          command=self.hesapla, state='disabled')
        self.hesapla_dugmesi.pack(side='left')
        self.kaydet_dugmesi = ttk.Button(kutu3, text="📥  Excel Olarak Kaydet",
                                         style='Yesil.TButton',
                                         command=self.kaydet, state='disabled')
        self.kaydet_dugmesi.pack(side='left', padx=10)
        self.durum_etiketi = ttk.Label(kutu3, text="", style='AltBaslik.TLabel')
        self.durum_etiketi.pack(side='left', padx=12)

        # --- Özet metrikler
        self.ozet_cercevesi = ttk.Frame(dis)
        self.ozet_cercevesi.pack(fill='x', pady=(14, 0))
        self.metrikler = {}
        for sutun, baslik in enumerate(["Toplam Personel", "Raporlu Personel",
                                        "Toplam Destek Günü", "Toplam Kesinti"]):
            hucre = tk.Frame(self.ozet_cercevesi, bg='white', highlightbackground='#e2e8f0',
                             highlightthickness=1)
            hucre.grid(row=0, column=sutun, sticky='we', padx=(0 if sutun == 0 else 8, 0))
            self.ozet_cercevesi.columnconfigure(sutun, weight=1)
            tk.Label(hucre, text=baslik, bg='white', fg=GRI, font=('Segoe UI', 9)).pack(
                anchor='w', padx=12, pady=(9, 0))
            deger = tk.Label(hucre, text="—", bg='white', fg=LACIVERT, font=('Segoe UI', 17, 'bold'))
            deger.pack(anchor='w', padx=12, pady=(0, 9))
            self.metrikler[baslik] = deger

        self.uyari_etiketi = ttk.Label(dis, text="", style='Uyari.TLabel', wraplength=1100)
        self.uyari_etiketi.pack(anchor='w', pady=(8, 0))

        # Kural dosyası bozuksa sessizce varsayılana dönmek yerine haber ver.
        if hesaplama.ayar_uyarisi:
            ttk.Label(dis, text="⚠ " + hesaplama.ayar_uyarisi, style='Uyari.TLabel',
                      wraplength=1100).pack(anchor='w', pady=(4, 0))

        # --- Sonuç tablosu
        kutu4 = ttk.LabelFrame(dis, text=" Hesaplama Sonuçları ", padding=10)
        kutu4.pack(fill='both', expand=True, pady=(12, 0))

        self.filtre_degeri = tk.BooleanVar(value=True)
        ttk.Checkbutton(kutu4, text="Yalnızca kesintisi olan personeli göster",
                        variable=self.filtre_degeri, command=self.tabloyu_doldur).pack(anchor='w')

        tablo_cerceve = ttk.Frame(kutu4)
        tablo_cerceve.pack(fill='both', expand=True, pady=(8, 0))

        # Kolonlar sonuç tablosuna göre çalışma anında kurulur; girdi dosyasına
        # Ad Soyad, Sicil No gibi kolonlar eklenirse tabloda kendiliğinden görünür.
        self.tablo = ttk.Treeview(tablo_cerceve, show='headings', selectmode='browse')
        self.tablo.tag_configure('raporlu', background='#fef2f2')

        dikey = ttk.Scrollbar(tablo_cerceve, orient='vertical', command=self.tablo.yview)
        yatay = ttk.Scrollbar(tablo_cerceve, orient='horizontal', command=self.tablo.xview)
        self.tablo.configure(yscrollcommand=dikey.set, xscrollcommand=yatay.set)
        self.tablo.grid(row=0, column=0, sticky='nsew')
        dikey.grid(row=0, column=1, sticky='ns')
        yatay.grid(row=1, column=0, sticky='we')
        tablo_cerceve.rowconfigure(0, weight=1)
        tablo_cerceve.columnconfigure(0, weight=1)

    # -------------------------------------------------------------- olaylar

    @property
    def donem(self):
        return int(self.yil_degeri.get()), AYLAR.index(self.ay_degeri.get()) + 1

    def dosya_sec(self):
        yol = filedialog.askopenfilename(
            title="İzin raporu Excel dosyasını seçin",
            filetypes=[("Excel dosyaları", "*.xlsx *.xls"), ("Tüm dosyalar", "*.*")],
        )
        if not yol:
            return
        self._dosyayi_yukle(yol)

    def _dosyayi_yukle(self, yol, elle_eslesme=None):
        """
        Dosyayı okur. Tanınmayan kolon varsa eşleştirme ekranını açar,
        böylece dosya yapısı değiştiğinde program hata verip durmaz.
        """
        try:
            basliklar, otomatik, eksik = hesaplama.kolonlari_incele(yol)
        except hesaplama.GirdiHatasi as hata:
            self._okuma_basarisiz(str(hata))
            return
        except Exception:
            self._beklenmeyen_hata()
            return

        if eksik and elle_eslesme is None:
            elle_eslesme = KolonEslestirme(self, basliklar, otomatik, eksik).sonuc
            if elle_eslesme is None:
                self._okuma_basarisiz(
                    "Kolon eşleştirmesi tamamlanmadı, dosya okunmadı.", sessiz=True)
                return

        try:
            self.veri = hesaplama.oku(yol, elle_eslesme)
        except hesaplama.GirdiHatasi as hata:
            self._okuma_basarisiz(str(hata))
            return
        except Exception:
            self._beklenmeyen_hata()
            return

        self.dosya_yolu = yol
        self.elle_eslesme = elle_eslesme
        self.dosya_etiketi.config(text=os.path.basename(yol), style='Dosya.TLabel')
        self.hesapla_dugmesi.config(state='normal')
        self.eslestir_dugmesi.config(state='normal')
        self._sonucu_temizle()

        yil, ay = hesaplama.donem_tespit(self.veri)
        self.yil_degeri.set(str(yil))
        self.ay_degeri.set(AYLAR[ay - 1])
        self.donem_degisti()

        kimlik = self.veri.attrs.get('kimlik_ad', hesaplama.KIMLIK_KOLONU)
        self.durum_etiketi.config(
            text=f"{len(self.veri)} izin kaydı okundu · kimlik: {kimlik}")

    def eslestirmeyi_duzenle(self):
        """Kolon eşleştirmesini kullanıcı istediği zaman gözden geçirebilsin."""
        if not self.dosya_yolu:
            return
        try:
            basliklar, otomatik, eksik = hesaplama.kolonlari_incele(self.dosya_yolu)
        except Exception:
            self._beklenmeyen_hata()
            return
        mevcut = dict(otomatik)
        mevcut.update(self.elle_eslesme or {})
        yeni = KolonEslestirme(self, basliklar, mevcut, hesaplama.KOLONLAR,
                               tumu=True).sonuc
        if yeni is not None:
            self._dosyayi_yukle(self.dosya_yolu, yeni)

    def _okuma_basarisiz(self, mesaj, sessiz=False):
        self.veri = None
        self.dosya_yolu = None
        self.elle_eslesme = None
        self.dosya_etiketi.config(text="Dosya okunmadı.", style='AltBaslik.TLabel')
        self.hesapla_dugmesi.config(state='disabled')
        self.eslestir_dugmesi.config(state='disabled')
        self._sonucu_temizle()
        if sessiz:
            self.durum_etiketi.config(text=mesaj)
        else:
            messagebox.showerror("Dosya okunamadı", mesaj)

    def donem_degisti(self):
        """Dönem değişince tatil kutusunu o ayın varsayılan tatilleriyle doldur."""
        try:
            tatiller = hesaplama.donem_tatilleri(self.donem)
        except (ValueError, TypeError):
            return
        self.tatil_degeri.set(", ".join(f"{g:%d.%m.%Y}" for g in tatiller))
        self._sonucu_temizle()

    def _tatilleri_coz(self):
        """Kutudaki metni tarih kümesine çevirir; dönem dışı tatiller korunur."""
        varsayilan = hesaplama.donem_tatilleri(self.donem)
        tatiller = {g for g in hesaplama.RESMI_TATILLER if g not in varsayilan}
        gecersiz = []
        for parca in self.tatil_degeri.get().split(','):
            parca = parca.strip()
            if not parca:
                continue
            try:
                tatiller.add(dt.datetime.strptime(parca, '%d.%m.%Y').date())
            except ValueError:
                gecersiz.append(parca)
        return tatiller, gecersiz

    def hesapla(self):
        if self.veri is None:
            return
        tatiller, gecersiz = self._tatilleri_coz()
        if gecersiz:
            messagebox.showwarning(
                "Tarih okunamadı",
                "Şu girdiler tarih olarak okunamadı ve yok sayılacak:\n\n  "
                + "\n  ".join(gecersiz)
                + "\n\nDoğru biçim: 15.07.2026",
            )

        self.hesapla_dugmesi.config(state='disabled')
        self.kaydet_dugmesi.config(state='disabled')
        self.durum_etiketi.config(text="Hesaplanıyor, lütfen bekleyin...")
        self.update_idletasks()

        # Tkinter değişkenleri yalnızca ana iş parçacığından okunabilir; dönemi
        # thread başlamadan burada sabitliyoruz.
        donem = self.donem
        veri = self.veri

        # Büyük dosyalarda pencere donmasın diye hesaplama ayrı iş parçacığında.
        # Sonuç kuyruğa bırakılır; tkinter'a yalnızca ana iş parçacığı dokunur.
        def calis():
            try:
                self._kuyruk.put(('tamam', hesaplama.hesapla(veri, donem, tatiller)))
            except Exception:
                self._kuyruk.put(('hata', traceback.format_exc()))

        threading.Thread(target=calis, daemon=True).start()
        self.after(80, self._kuyrugu_yokla)

    def _kuyrugu_yokla(self):
        """Hesaplama iş parçacığının sonucunu ana iş parçacığında karşılar."""
        try:
            durum, yuk = self._kuyruk.get_nowait()
        except queue.Empty:
            self.after(80, self._kuyrugu_yokla)
            return
        if durum == 'tamam':
            self._hesap_bitti(yuk)
        else:
            self._hesap_hatasi(yuk)

    def _hesap_bitti(self, sonuc):
        self.sonuc = sonuc
        self.hesapla_dugmesi.config(state='normal')
        self.kaydet_dugmesi.config(state='normal')
        self.durum_etiketi.config(text="Hesaplama tamamlandı.")

        raporlu = sonuc[sonuc['Rapor Durumu'] == 'Raporlu']
        self.metrikler["Toplam Personel"].config(text=f"{len(sonuc)}")
        self.metrikler["Raporlu Personel"].config(text=f"{len(raporlu)}")
        self.metrikler["Toplam Destek Günü"].config(text=self._sayi(sonuc['Destek Gün'].sum()))
        self.metrikler["Toplam Kesinti"].config(text=self._sayi(sonuc['Toplam Kesinti'].sum()))

        uyarililar = sonuc[sonuc['Uyarı'] != '']
        if uyarililar.empty:
            self.uyari_etiketi.config(text="")
        else:
            takvim = uyarililar['Uyarı'].str.contains('resmi tatil listesi').sum()
            metin = f"⚠ {len(uyarililar)} personelde not var."
            if takvim:
                metin += (f" {takvim} tanesinde izin gün sayısı resmi tatil takvimiyle "
                          f"uyuşmuyor — tatil listesini kontrol edin.")
            metin += " Ayrıntı, kaydedilen Excel dosyasının 'Uyarı' kolonunda."
            self.uyari_etiketi.config(text=metin)
        self.tabloyu_doldur()

    def _hesap_hatasi(self, iz):
        self.hesapla_dugmesi.config(state='normal')
        self.durum_etiketi.config(text="Hesaplama başarısız.")
        self._beklenmeyen_hata(iz)

    def tabloyu_doldur(self):
        self.tablo.delete(*self.tablo.get_children())
        if self.sonuc is None:
            return
        gosterilen = self.sonuc
        if self.filtre_degeri.get():
            gosterilen = gosterilen[gosterilen['Toplam Kesinti'] > 0]

        kolonlar = [k for k in self.sonuc.columns if k not in GIZLI_KOLONLAR]
        if list(self.tablo['columns']) != kolonlar:
            self.tablo['columns'] = kolonlar
            for kolon in kolonlar:
                self.tablo.heading(kolon, text=kolon)
                self.tablo.column(
                    kolon,
                    width=KOLON_GENISLIKLERI.get(kolon, VARSAYILAN_GENISLIK),
                    anchor='w' if kolon in SOLA_YASLI or kolon not in KOLON_GENISLIKLERI
                    else 'center',
                    stretch=False,
                )

        for _, satir in gosterilen.iterrows():
            degerler = [
                self._sayi(satir[k]) if isinstance(satir[k], float) else satir[k]
                for k in kolonlar
            ]
            etiket = 'raporlu' if satir['Rapor Durumu'] == 'Raporlu' else ''
            self.tablo.insert('', 'end', values=degerler, tags=(etiket,))

        if gosterilen.empty:
            self.durum_etiketi.config(text="Bu dönemde kesintisi olan personel bulunmuyor.")

    def kaydet(self):
        if self.sonuc is None:
            return
        yil, ay = self.donem
        yol = filedialog.asksaveasfilename(
            title="Sonuç dosyasını kaydet",
            defaultextension=".xlsx",
            initialfile=f"teknopark_destek_{yil}_{ay:02d}.xlsx",
            filetypes=[("Excel dosyası", "*.xlsx")],
        )
        if not yol:
            return
        try:
            ana_yol, kesintili_yol = hesaplama.excel_yaz_ikili(self.sonuc, yol)
        except PermissionError:
            messagebox.showerror(
                "Dosya kaydedilemedi",
                "Dosya başka bir programda açık olabilir.\n\n"
                "Excel'de açıksa kapatıp tekrar deneyin.",
            )
        except Exception:
            self._beklenmeyen_hata()
        else:
            kesintili_sayi = len(hesaplama.kesintili_personel(self.sonuc))
            self.durum_etiketi.config(text="Kaydedildi.")
            mesaj = f"Tüm personel ({len(self.sonuc)} kişi):\n{ana_yol}"
            if kesintili_yol:
                mesaj += f"\n\nKesintisi olan personel ({kesintili_sayi} kişi):\n{kesintili_yol}"
            else:
                mesaj += "\n\nKesintisi olan personel bulunmadığı için ikinci dosya oluşturulmadı."
            messagebox.showinfo("Kaydedildi", mesaj)

    # ----------------------------------------------------------- yardımcılar

    @staticmethod
    def _sayi(deger):
        """Tam sayıysa ondalıksız, değilse Türkçe ondalık ayracıyla gösterir."""
        if float(deger) == int(deger):
            return f"{int(deger):,}".replace(',', '.')
        return f"{deger:,.1f}".replace(',', '\x00').replace('.', ',').replace('\x00', '.')

    def _sonucu_temizle(self):
        self.sonuc = None
        self.kaydet_dugmesi.config(state='disabled')
        self.tablo.delete(*self.tablo.get_children())
        self.uyari_etiketi.config(text="")
        for etiket in self.metrikler.values():
            etiket.config(text="—")

    def _beklenmeyen_hata(self, iz=None):
        messagebox.showerror(
            "Beklenmeyen hata",
            "İşlem sırasında beklenmeyen bir hata oluştu:\n\n"
            + (iz or traceback.format_exc())[-1200:],
        )


def kendini_dogrula(girdi, cikti):
    """
    Arayüz açmadan uçtan uca hesap yapar (paketlenmiş .exe'yi doğrulamak için).

    Kullanım:  TeknoparkDestekHesaplama.exe --kendini-dogrula girdi.xlsx cikti.xlsx
    Başarılıysa 0, aksi halde 1 döner ve nedeni cikti dosyasının yanına .log yazar.
    """
    kayit = os.path.splitext(cikti)[0] + '.log'
    try:
        veri = hesaplama.oku(girdi)
        donem = hesaplama.donem_tespit(veri)
        sonuc = hesaplama.hesapla(veri, donem)
        # Arayüzdeki kaydetme akışının aynısı: iki dosya üretilir.
        ana_yol, kesintili_yol = hesaplama.excel_yaz_ikili(sonuc, cikti)
        raporlu = (sonuc['Rapor Durumu'] == 'Raporlu').sum()
        ayar_yolu = hesaplama.ayar_dosyasi_yolu()
        ozet = (f"TAMAM\ndonem={donem[0]}-{donem[1]:02d}\npersonel={len(sonuc)}\n"
                f"raporlu={raporlu}\ntoplam_destek_gun={sonuc['Destek Gün'].sum():g}\n"
                f"kesintili_personel={len(hesaplama.kesintili_personel(sonuc))}\n"
                f"ayar_dosyasi={'okundu' if ayar_yolu.exists() else 'yok'}\n"
                f"ayar_uyarisi={hesaplama.ayar_uyarisi or '-'}\n"
                f"tesvik_taban_gun={hesaplama.TESVIK_TABAN_GUN}\n"
                f"ana_dosya={ana_yol}\nkesintili_dosya={kesintili_yol}\n")
    except Exception:
        with open(kayit, 'w', encoding='utf-8') as dosya:
            dosya.write("HATA\n" + traceback.format_exc())
        return 1
    with open(kayit, 'w', encoding='utf-8') as dosya:
        dosya.write(ozet)
    return 0


def main():
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == '--kendini-dogrula':
        return kendini_dogrula(sys.argv[2], sys.argv[3])
    Uygulama().mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
