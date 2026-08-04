# Teknopark Destek Hesaplama

İK'nın aylık izin raporu Excel'ini okuyup her personel için teknopark teşvikine esas
**destek gün ve saat** miktarını hesaplayan, kurulum gerektirmeden çalışan masaüstü uygulaması.

Girdi bir Excel dosyası, çıktı iki Excel dosyası. Arada, kesintinin hangi kalemden
geldiğini satır satır gösteren bir kural motoru var.

---

## Hesaplama kuralları

Teşvik **30 gün** üzerinden hesaplanır. Belirleyici kriter, personelin o ay içinde
**sağlık raporu** (hastalık raporu veya kadın doğum istirahati) olup olmadığıdır.

### Raporu olmayan personel

Yıllık izin, resmi tatil ve mazeret izni teşvikten **düşmez**. Tam 30 gün destek alır.

### Raporu olan personel

Haftalık çalışma saatini tamamlayamadığı için şu kalemler düşülür:

| Kesinti | Tanım |
|---|---|
| Rapor günleri | Rapor aralığına düşen iş günleri (hafta sonu ve resmi tatil hariç) |
| Hafta sonu | Raporun değdiği **her** haftanın Cumartesi ve Pazar günleri |
| Yıllık izin | O ay içinde kullanılan yıllık izin günleri |
| Resmi tatil | O ay içindeki hafta içine denk gelen resmi tatiller |
| Kısmi rapor | Saatlik raporlar birikimli toplanır; artan kısım ≤ 4 saat ise yarım gün, > 4 saat ise tam gün |

**Düşmeyen izinler:** Mazeret İzni (doktor randevusu, doğum günü izni, taşınma vb.) ve
Evlilik İzni — personel raporlu olsa bile düşmez.

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
| `test_hesaplama.py` | 51 test senaryosu. |
| `paketle.py` | PyInstaller ile tek dosya `.exe` üretir. |
| `kurulum.iss` / `kurulum_yap.py` | Inno Setup ile kurulum dosyası (setup) üretir. |
| `KULLANIM.txt` | İK için kullanım kılavuzu; kurulumla birlikte dağıtılır. |

Kural motoru arayüzden ayrı tutuldu: kural değişince tek dosya güncelleniyor,
hesaplama arayüz açmadan test edilebiliyor ve aynı motor üç kullanım biçimini besliyor.

---

## Girdi dosyası

Beklenen sekiz kolon ve tanınan diğer adlandırmalar:

| Beklenen | Tanınan diğer adlar |
|---|---|
| `Çalışan Numarası` | Sicil No, Personel No, TC, Employee Id |
| `Şirket` | Firma, Şirket Adı, Company |
| `İzin Türü` | İzin Tipi, Devamsızlık Tipi, Leave Type |
| `İzin Nedeni` | İzin Sebebi, Neden, Açıklama |
| `İzin Başlangıç Tarihi` | Başlangıç Tarihi, Başlangıç, İlk Gün |
| `İzin Bitiş Tarihi` | Bitiş Tarihi, Bitiş, Son Gün |
| `quantityInDays` | Gün, Gün Sayısı, İzin Gün Sayısı |
| `quantityInHours` | Saat, Saat Sayısı, İzin Saat Sayısı |

Ayrıca:

- Büyük/küçük harf, Türkçe karakter ve fazladan boşluk farkları tolere edilir.
- Başlık satırı ilk satırda olmak zorunda değildir; üstte firma adı/dönem bloğu varsa
  gerçek başlık satırı ilk 15 satır içinde bulunur.
- **Tanınmayan kolonlar korunur.** Ad Soyad, Sicil No, Departman gibi kolonlar eklenirse
  çıktıda çalışan numarasının hemen yanında yer alır.
- Kolonlardan biri bulunamazsa program sessizce yanlış hesaplamaz; hangi kolonun eksik
  olduğunu ve dosyada hangi kolonların bulunduğunu söyleyerek durur.

## Çıktı

Kaydetme iki dosya üretir:

| Dosya | İçerik |
|---|---|
| `teknopark_destek_YYYY_AA.xlsx` | Tüm personel |
| `teknopark_destek_YYYY_AA_kesintili.xlsx` | Yalnızca kesintisi olan personel |

Kesinti kalemleri ayrı kolonlarda durur (rapor günü, hafta sonu, yıllık izin, resmi tatil,
kısmi rapor, toplam kesinti, destek gün, destek saat). Son kolon `Uyarı`, resmi tatil
takvimiyle dosyadaki gün sayıları arasında tutarsızlık varsa bunu bildirir.

---

## Testler

```bash
python -m pytest test_hesaplama.py -q
```

51 senaryo, altı başlıkta:

| Grup | Adet | Kapsam |
|---|---:|---|
| Gerçek veri regresyonu | 13 | Raporlu personellerin beklenen değerleri birebir sabitlenir |
| Kural doğrulama | 14 | Hafta sonu, ay sonu, mükerrer sayım, izin türleri |
| Kısmi gün yuvarlama | 10 | Yuvarlama eşikleri ve aylık birikim |
| Girdi dayanıklılığı | 10 | Eksik kolon, eşanlamlılar, başlık bloğu, ek kolonlar |
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

- **Resmi tatil takvimi** `hesaplama.py` içinde 2026 yılı için gömülüdür. Yeni yıla
  geçildiğinde güncellenmelidir. Güncellenmezse program sessizce yanlış hesaplamaz;
  dosyadaki gün sayılarıyla karşılaştırıp çıktının `Uyarı` kolonunda sapmayı bildirir.
  Dini bayram tarihleri gerçek veriyle doğrulanmamıştır, kullanım öncesi kontrol edilmelidir.
- **Kural değişirse** `hesaplama.py` güncellenir, testler çalıştırılır, `python paketle.py`
  ile yeni `.exe` üretilir. Hangi izin türlerinin düşeceği tek bir sabitte tutulur
  (`KESINTI_IZIN_TURLERI`).
- **Ay sonu haftası:** Raporu ay içinde biten bir personelin son hafta hafta sonu ne bu
  aydan ne de sonraki aydan düşer. Bu davranış bilinçlidir; kabul edilebilir bulunmazsa
  ayrı bir kural gerekir.
