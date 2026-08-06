# Teknopark Destek Hesaplama

İK'nın aylık izin raporu Excel'ini okuyup her personel için teknopark teşvikine esas
**destek gün ve saat** miktarını hesaplayan, kurulum gerektirmeden çalışan masaüstü uygulaması.

Girdi bir Excel dosyası, çıktı iki Excel dosyası. Arada, kesintinin hangi kalemden
geldiğini satır satır gösteren bir kural motoru var.

---

## Hesaplama kuralları

Teşvik **30 gün** üzerinden hesaplanır. Belirleyici kriter, personelin o ay içinde
**sağlık raporu** (hastalık raporu veya kadın doğum istirahati) olup olmadığıdır.

### Her personelde düşen

| Kesinti | Tanım |
|---|---|
| Ücretsiz izin | Ücret ödenmediği ve SGK primi yatmadığı için o günlerde teşvikten yararlanılamaz |

### Raporu olmayan personel

Ücretsiz izin dışında hiçbir izin düşmez; yıllık izin, resmi tatil ve mazeret izni
teşviki azaltmaz.

### Raporu olan personel

Haftalık çalışma saatini tamamlayamadığı için şu kalemler de düşülür:

| Kesinti | Tanım |
|---|---|
| Rapor günleri | Rapor aralığına düşen iş günleri (hafta sonu ve resmi tatil hariç) |
| Hafta sonu | Raporun değdiği **her** haftanın Cumartesi ve Pazar günleri |
| Yıllık izin | O ay içinde kullanılan yıllık izin günleri — kıdem şartına bağlı, aşağıya bakınız |
| Resmi tatil | O ay içindeki hafta içine denk gelen resmi tatiller |
| Kısmi rapor | Saatlik raporlar birikimli toplanır; artan kısım ≤ 4 saat ise yarım gün, > 4 saat ise tam gün |

**Düşmeyen izinler:** Mazeret İzni (doktor randevusu, doğum günü izni, taşınma vb.) ve
Evlilik İzni — personel raporlu olsa bile düşmez.

### Kıdem şartı (İş Kanunu Md. 53)

İşe başlama tarihinden itibaren **1 yılını doldurmamış** personelin yıllık izni
yasal olarak hak edilmemiş sayılır; bu kayıt, aynı dönemde raporu olsa dahi
teşvikten **düşülmez**, çıktının `Uyarı` kolonunda belirtilir ve `Riskli`
kolonunda işaretlenir.

Kıdem, gün sayısıyla değil takvim yıldönümüyle hesaplanır. `İşe Başlama Tarihi`
kolonu dosyada yoksa kural uygulanmaz ve ilgili kolonlar boş bırakılır.

| Kıdem | Yıllık izin hakkı |
|---|---:|
| 0–1 yıl | hak yok — **riskli** olarak işaretlenir |
| 1–5 yıl | 14 gün |
| 5–15 yıl | 20 gün |
| 15 yıl ve üzeri | 26 gün |

### Yıllık izinde gün sayımı

Yarım günlük yıllık izinler ay boyunca toplanıp **yukarı yuvarlanır**:

- 0,5 gün → **1 tam gün**
- 0,5 + 0,5 (iki ayrı günde) → **1 tam gün**, iki ayrı tam gün değil
- Bir günde **4 saat 30 dakikanın üzerinde** izin → o gün tam gün sayılır

Bu yuvarlama yalnızca yıllık izne uygulanır. Kısmi rapor (eksik çalışma) için
farklı bir kural işler: ≤ 4 saat yarım gün, > 4 saat tam gün.

**Ay sonu haftası:** Hafta sonu yalnızca dönem ayının içine düşerse sayılır. 27–31 Temmuz
haftasının hafta sonu 1–2 Ağustos olduğu için Temmuz hesabına girmez.

```
Destek Gün  = max(0, 30 − toplam kesinti)
Destek Saat = Destek Gün × 8
```

### Örnek

16 Temmuz'da doğum istirahatine ayrılan, aynı ay 1 gün doğum günü izni ve 4 saat
doktor randevusu izni kullanmış, yıllık izni olmayan bir personel:

| Kalem | Gün |
|---|---:|
| Rapor günleri (16–31 Temmuz iş günleri) | 12,0 |
| Hafta sonu (18–19 ve 25–26 Temmuz) | 4,0 |
| Yıllık izin — yok | 0,0 |
| Resmi tatil (15 Temmuz) | 1,0 |
| Mazeret izinleri — düşmez | 0,0 |
| **Toplam kesinti** | **17,0** |
| **Destek günü** (30 − 17) | **13,0** |

---

## Kurulum ve çalıştırma

### Son kullanıcı (Python gerekmez)

`TeknoparkDestekHesaplama_Kurulum.exe` çalıştırılır. Yönetici şifresi gerektirmez;
program kullanıcının kendi klasörüne kurulur, Başlat menüsüne kısayol ekler ve
kaldırma kaydı oluşturur. Kullanım adımları `KULLANIM.txt` içinde.

Kurulumsuz kullanmak isteyenler `TeknoparkDestekHesaplama.exe` dosyasını doğrudan
çalıştırabilir. Her iki durumda da internet gerekmez.

> Üretilen dosyalar depoya dahil değildir (32–34 MB). Aşağıdaki komutlarla üretilir.

### Geliştirme

```bash
python -m pip install -r requirements.txt

python masaustu.py                    # masaüstü arayüzü
python -m streamlit run app.py        # tarayıcı arayüzü
python hesaplama.py girdi.xlsx cikti.xlsx   # komut satırı

python paketle.py                     # tek dosya .exe üret
python kurulum_yap.py                 # kurulum dosyası (setup) üret
```

`kurulum_yap.py`, gerekiyorsa önce `paketle.py`'yi çağırır. Kurulum dosyası üretmek
için [Inno Setup 6](https://jrsoftware.org/isdl.php) kurulu olmalıdır.

### Dağıtım

**E-posta ve WhatsApp ile göndermeyin.** Bu servisler `.exe` dosyalarını güvenlik
gerekçesiyle engeller veya uzantısını değiştirir; dosya karşı tarafa bozuk ulaşır ve
Windows "hangi uygulamayla açmak istersiniz?" diye sorar. Zip içine koymak da işe
yaramaz — Gmail zip içindeki `.exe` dosyalarını da engeller.

Çalışan yöntemler:

- **OneDrive / SharePoint / Teams bağlantısı** — dosyayı yükleyip bağlantısını paylaşın
- **Şirket ağ sürücüsü**
- **USB bellek**
- **GitHub Releases** — depo sayfasından *Releases → Create a new release* ile yüklenir

---

## Dosya yapısı

| Dosya | Rolü |
|---|---|
| `hesaplama.py` | **Kural motoru** — okuma, doğrulama, hesap, Excel yazma. Arayüzden bağımsız. |
| `masaustu.py` | Masaüstü penceresi (tkinter). Dağıtılan uygulamanın arayüzü. |
| `app.py` | Tarayıcı arayüzü (Streamlit). Aynı motoru kullanır. |
| `test_hesaplama.py` | 105 test senaryosu. |
| `paketle.py` | PyInstaller ile tek dosya `.exe` üretir. |
| `kurulum.iss` / `kurulum_yap.py` | Inno Setup ile kurulum dosyası (setup) üretir. |
| `KULLANIM.txt` | İK için kullanım kılavuzu; kurulumla birlikte dağıtılır. |

Kural motoru arayüzden ayrı tutuldu: kural değişince tek dosya güncelleniyor,
hesaplama arayüz açmadan test edilebiliyor ve aynı motor üç kullanım biçimini besliyor.

---

## Girdi dosyası

Gereken sekiz bilgi ve tanınan adlandırmalar:

| Gereken | Tanınan adlar |
|---|---|
| Personel kimliği | Çalışan Numarası, Sicil No, Personel No, TC, **Ad Soyad**, İsim, Employee Id |
| `Şirket` | Firma, Şirket Adı, Company |
| `İzin Türü` | İzin Tipi, Devamsızlık Tipi, Leave Type |
| `İzin Nedeni` | İzin Sebebi, Neden, Açıklama |
| `İzin Başlangıç Tarihi` | Başlangıç Tarihi, Başlangıç, İlk Gün |
| `İzin Bitiş Tarihi` | Bitiş Tarihi, Bitiş, Son Gün |
| `quantityInDays` | Gün, Gün Sayısı, İzin Gün Sayısı |
| `quantityInHours` | Saat, Saat Sayısı, İzin Saat Sayısı |

İsteğe bağlı: `İşe Başlama Tarihi` (İşe Giriş Tarihi, Hire Date) — kıdem şartı için.

Personel kimliği olarak **çalışan numarası da ad soyad da** kabul edilir. İkisi birden
varsa numara kimlik olur, ad soyad bilgi kolonu olarak taşınır. Kimlik kolonu çıktıda
dosyadaki adıyla görünür.

Ayrıca:

- Büyük/küçük harf, Türkçe karakter ve fazladan boşluk farkları tolere edilir.
- Başlık satırı ilk satırda olmak zorunda değildir; üstte firma adı/dönem bloğu varsa
  gerçek başlık satırı ilk 15 satır içinde bulunur.
- **Çok sayfalı dosyalarda veri sayfası otomatik seçilir.** "Kurallar", "Açıklama" gibi
  yardımcı sayfalar atlanır.
- **Tanınmayan kolonlar korunur.** Departman, İşe Başlama Tarihi gibi kolonlar eklenirse
  çıktıda kimliğin hemen yanında yer alır.

### Kolon eşleştirme

Bir kolon otomatik tanınamazsa program hata verip durmaz: **kolon eşleştirme ekranı**
açılır ve hangi kolonun ne olduğu açılır listelerden seçilir. Böylece dosya yapısı
tamamen değişse bile kod değiştirmeden uyarlama yapılabilir.

Eşleştirme, `Kolonları Eşleştir...` düğmesiyle sonradan da gözden geçirilebilir —
otomatik tanıma yanlış eşleştirmişse düzeltilebilir.

### Kural dosyası (`ayarlar.json`)

Kolon eşanlamlıları, izin türleri, resmi tatil takvimi, teşvik taban günü ve kıdem
kademeleri kod içine gömülü **değildir**: uygulamanın yanındaki `ayarlar.json`
dosyasından okunur. Böylece yeni bir kolon adı veya tatil eklemek için yeniden
derlemeye gerek kalmaz.

```jsonc
{
  "kolon_esanlamlilari": { "Personel": ["Sicil No", "Ad Soyad", ...], ... },
  "kesinti_izin_turleri": ["Yıllık İzin"],
  "her_kosulda_kesinti_turleri": ["Ücretsiz İzin"],
  "tesvik_taban_gun": 30,
  "yillik_izin_tam_gun_esigi_saat": 4.5,
  "yillik_izin_hak_kademeleri": [[15, 26], [5, 20], [1, 14], [0, 0]],
  "resmi_tatiller": ["01.01.2026", "15.07.2026", ...]
}
```

Dosya yoksa gömülü varsayılanlar kullanılır — bu normal çalışma biçimidir.
Dosya bozuksa program sessizce varsayılana dönmez; ekranda uyarı gösterir.
Kurulum sırasında oluşturulur ve program güncellenirken **üzerine yazılmaz**.

## Çıktı

Kaydetme iki dosya üretir:

| Dosya | İçerik |
|---|---|
| `teknopark_destek_YYYY_AA.xlsx` | Tüm personel |
| `teknopark_destek_YYYY_AA_kesintili.xlsx` | Yalnızca kesintisi olan personel |

Kesinti kalemleri ayrı kolonlarda durur (rapor günü, hafta sonu, yıllık izin, resmi tatil,
kısmi rapor, ücretsiz izin, toplam kesinti, destek gün, destek saat). Son kolon `Uyarı`,
resmi tatil takvimiyle dosyadaki gün sayıları arasındaki tutarsızlıkları ve kıdem şartı
nedeniyle hesaba katılmayan yıllık izinleri bildirir.

---

## Testler

```bash
python -m pytest test_hesaplama.py -q
```

105 senaryo, on bir başlıkta:

| Grup | Adet | Kapsam |
|---|---:|---|
| Gerçek veri regresyonu | 13 | Raporlu personellerin beklenen değerleri birebir sabitlenir |
| Kural doğrulama | 14 | Hafta sonu, ay sonu, mükerrer sayım, izin türleri |
| Ücretsiz izin ve kıdem şartı | 13 | Rapor aranmadan düşme, yıldönümü hesabı, artık yıl |
| Yıllık izinde gün sayımı | 11 | 0,5 + 0,5 = 1 gün, 4:30 eşiği |
| Kıdem kademeleri ve riskli işareti | 11 | 14/20/26 gün hakkı, riskli kayıt tespiti |
| Kısmi rapor yuvarlama | 10 | Yuvarlama eşikleri ve aylık birikim |
| Girdi dayanıklılığı | 15 | Kimlik esnekliği, elle eşleştirme, çok sayfa, başlık bloğu |
| Çok yıllı tatil takvimi | 10 | Sabit tatil üretimi, dini bayram kayması, doğrulama |
| Ayar dosyası | 3 | Dışa aktarma, geri yükleme, bozuk dosyada varsayılana dönüş |
| Çıktı dosyaları | 2 | İkili Excel üretimi |
| Tatil takvimi uyarısı | 2 | Takvim sapması tespiti |

**Senaryoların tamamı beklenen sonuçlarıyla birlikte → [TEST_SENARYOLARI.md](TEST_SENARYOLARI.md)**

> Gerçek veri regresyon testleri, izin raporu dosyası çalışma dizininde yoksa
> otomatik olarak atlanır. Veri dosyaları depoda bulunmaz (aşağıya bakınız).

---

## Personel verisi hakkında

İzin raporu ve hesap çıktıları, çalışan numarasıyla eşleşmiş **sağlık verisi** içerir
(hastalık raporu, doğum istirahati, doktor randevusu). KVKK kapsamında özel nitelikli
kişisel veridir ve bu depoda **bulunmaz**. `.gitignore` tüm `.xlsx`, `.xls` ve `.csv`
dosyalarını hariç tutar.

Veri dosyalarını depoya eklemeyin.

---

## Bakım notları

- **Resmi tatil takvimi** üç katmanlıdır ve yıllarca güncelleme gerektirmeden çalışır:
  - *Sabit tarihli tatiller* (1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz,
    30 Ağustos, 28–29 Ekim) her yıl için koddan üretilir.
  - *Dini bayramlar* kayar. Diyanet takviminden teyit edilmiş yıllar
    `DOGRULANMIS_DINI_BAYRAMLAR` içinde tutulur; tanımlı olmayan yıllar aritmetik
    Hicri takvimden hesaplanır ve **doğrulanmamış** sayılır — o dönem için hesap
    yapıldığında arayüzde uyarı çıkar.
  - `ayarlar.json` hepsini ezebilir. Teyit edilen yıl eklendiğinde uyarı kalkar,
    yeniden derleme gerekmez.

  Şu an yalnızca **2026** doğrulanmıştır. Algoritma 2026'yı birebir tutturmuştur,
  ancak Diyanet astronomik hesap kullandığı için diğer yıllarda bir gün sapabilir.
- **Kural değişirse** `hesaplama.py` güncellenir, testler çalıştırılır, `python paketle.py`
  ile yeni `.exe` üretilir. Hangi izin türlerinin düşeceği tek bir sabitte tutulur
  (`KESINTI_IZIN_TURLERI`).
- **Ay sonu haftası:** Raporu ay içinde biten bir personelin son hafta hafta sonu ne bu
  aydan ne de sonraki aydan düşer. Bu davranış bilinçlidir; kabul edilebilir bulunmazsa
  ayrı bir kural gerekir.
