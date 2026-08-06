# Test Senaryoları

105 senaryo, on bir başlıkta. Tamamı `test_hesaplama.py` içinde kodlanmıştır ve her
değişiklikte saniyeler içinde çalışır.

```bash
python -m pytest test_hesaplama.py -q
```

Referans dönem **Temmuz 2026**, tek resmi tatil **15 Temmuz (Çarşamba)**.

> Gerçek veri regresyon testleri (1–13), izin raporu Excel dosyası çalışma dizininde
> yoksa otomatik olarak atlanır. Veri dosyaları depoda bulunmaz.

---

## 1. Gerçek veri regresyonu — 13 senaryo

Gerçek Temmuz 2026 dosyası üzerinde çalışır. Amaç, kural motorunda bir şey bozulduğunda
hangi personelin hangi değerinin kaydığını anında görebilmek.

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 1 | Dönem tespiti | Dosyadan Temmuz 2026 tespit edilir |
| 2 | Toplamlar | 215 personel, 8 raporlu, 6.383 destek günü |
| 3–10 | 8 raporlu personelin kesinti kırılımı | Her birinin 6 değeri birebir sabitlenir (aşağıdaki tablo) |
| 11 | Raporsuz personel | 207 personelin tamamı tam 30 gün alır |
| 12 | Tatil takvimi tutarlılığı | 367 kaydın hiçbirinde takvim sapması uyarısı çıkmaz |
| 13 | Kırılım toplamı | Her satırda `Toplam Kesinti + Destek Gün = 30` |

### Sabitlenen değerler

| Çalışan | Rapor türü | Rapor | Hafta sonu | Yıllık izin | Resmi tatil | Kısmi | Toplam kesinti | Destek günü |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1043 | Kadın Doğum İstirahat Raporu | 12 | 4 | 0 | 1 | 0 | 17 | **13** |
| 1079 | Hastalık Raporu | 1 | 2 | 5 | 1 | 0 | 9 | **21** |
| 1179 | Hastalık Raporu | 9 | 2 | 4 | 1 | 0 | 16 | **14** |
| 1192 | Hastalık Raporu | 1 | 2 | 2 | 1 | 0 | 6 | **24** |
| 1297 | Hastalık Raporu | 2 | 2 | 0 | 1 | 0 | 5 | **25** |
| 1303 | Hastalık Raporu | 1 | 2 | 2 | 1 | 0 | 6 | **24** |
| 1333 | Hastalık Raporu | 3 | 0 | 0 | 1 | 0 | 4 | **26** |
| 1345 | Hastalık Raporu | 1 | 0 | 2 | 1 | 0 | 4 | **26** |

1333 ve 1345'in hafta sonu kesintisi sıfır: ikisinin de raporu 27–31 Temmuz haftasında
ve o haftanın hafta sonu Ağustos'a taşıyor.

---

## 2. Kural doğrulama — 14 senaryo

Her kuralı tek başına izole eden sentetik senaryolar.

| # | Senaryo | Girdi | Beklenen sonuç |
|---|---|---|---|
| 14 | Raporsuz personelde izin | 5 gün yıllık izin + saatlik mazeret izni | Kesinti 0, destek 30 gün |
| 15 | Doğum istirahati rapor sayılır | Kadın Doğum İstirahat Raporu | Hastalık raporuyla aynı işleme tabi |
| 16 | Tek günlük rapor | Perşembe 9 Temmuz | 1 rapor + 2 hafta sonu + 1 resmi tatil = 4 |
| 17 | Çok haftaya yayılan rapor | 9–20 Temmuz | Değdiği 3 haftanın hafta sonu düşer = 6 gün |
| 18 | Ay dışına taşan hafta sonu | 29–31 Temmuz raporu | Hafta sonu kesintisi **0** (1–2 Ağustos'a taşıyor) |
| 19 | Önceki aydan başlayan hafta | 1–2 Temmuz raporu | Hafta sonu (4–5 Tem) ay içinde olduğu için sayılır |
| 20 | Ay dışına taşan rapor | 21 Temmuz – 19 Ağustos | Yalnızca Temmuz günleri: 9 rapor + 2 hafta sonu |
| 21 | Rapor ve yıllık izin aynı günde | Aynı tarihte iki kayıt | Mükerrer sayılmaz, rapor günü kazanır |
| 22 | Raporluda yıllık izin | Rapor + 2 gün yıllık izin | Yıllık izin düşer |
| 23 | Tam gün mazeret izni | Doğum Günü İzni, 1 gün | **Düşmez** |
| 24 | Saatlik mazeret izni | Doktor Randevusu, 0,5 gün | **Düşmez** |
| 25 | Evlilik izni | 3 gün | **Düşmez** |
| 26 | Tüm ay rapor | 1–31 Temmuz | Destek 0'a iner, negatife düşmez |
| 27 | Hafta sonuna denk gelen resmi tatil | Cumartesi tatil | Ayrıca sayılmaz |

---

## 3. Ücretsiz izin ve kıdem şartı — 13 senaryo

İK kural dokümanından gelen iki kural.

### Ücretsiz izin

Ücret ödenmediği ve SGK primi yatmadığı için rapor durumundan bağımsız olarak düşer.

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 28 | Raporsuz personelde ücretsiz izin | 27–31 Temmuz, 5 gün düşer → destek 25 |
| 29 | Resmi tatili kapsamaz | 13–24 Temmuz, 15 Temmuz tatil → 9 iş günü düşer |
| 30 | Raporla aynı günde | Mükerrer sayılmaz, rapor günü kazanır |

### Kıdem şartı (İş Kanunu Md. 53)

1 yılını doldurmamış personelin yıllık izni hak edilmemiş sayılır; raporlu olsa bile düşmez.

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 31 | 1 yıldan az kıdem | Yıllık izin kesintisi 0, `Uyarı` kolonunda kıdem notu |
| 32 | 1 yılını dolduran kıdem | Yıllık izin normal şekilde düşer |
| 33–38 | Kıdem eşiği — 6 tarih | Yıldönümüne 1 gün varsa hak yok, yıldönümünde ve sonrasında hak var |
| 39 | Artık yıl sınırı | 29 Şubat'ta işe başlayanın yıldönümü, artık olmayan yılda 28 Şubat sayılır |
| 40 | İşe Başlama Tarihi yoksa | Kural uygulanmaz, yıllık izin normal düşer |

Kıdem gün sayısıyla değil **takvim yıldönümüyle** hesaplanır; gün hesabı artık yıllarda
bir gün kaydığı için sınır tarihlerde yanlış sonuç veriyordu.

---

## 3b. Yıllık izinde gün sayımı (Kural 3) — 11 senaryo

Yarım günlük yıllık izinler ay boyunca toplanıp yukarı yuvarlanır.

| Senaryo | Beklenen sonuç |
|---|---|
| Yuvarlama tablosu — 6 değer | 0 → 0 · 0,5 → 1 · 1,0 → 1 · 1,5 → 2 · 2,0 → 2 · 3,5 → 4 |
| Tek yarım günlük yıllık izin | 1 tam gün sayılır |
| İki ayrı günde 0,5 + 0,5 | **1 tam gün** — iki ayrı tam gün değil |
| Yedi ayrı yarım gün | 3,5 → **4 tam gün** (gerçek veride 1170 numaralı personelin deseni) |
| 4:30 üzeri kısmi izin | O gün tam gün sayılır; 1,0 + 0,5 = 1,5 → 2 gün |
| Tam ve yarım gün birlikte | 2 tam gün + 0,5 → 3 gün |

Bu yuvarlama **yalnızca yıllık izne** uygulanır. Kısmi rapor (eksik çalışma) için
bölüm 4'teki farklı kural işler.

---

## 3c. Kıdem kademeleri ve riskli işareti — 11 senaryo

| Senaryo | Beklenen sonuç |
|---|---|
| İzin hakkı kademeleri — 7 değer | 0 yıl → 0 · 1 yıl → 14 · 4 → 14 · 5 → 20 · 14 → 20 · 15 → 26 · 30 → 26 |
| Kıdem yılı hesabı | Yıldönümü geçmemişse bir eksik sayılır; bilgi yoksa `None` |
| Kıdemsiz yıllık izin | `Riskli = Evet`, raporsuz olsa bile işaretlenir |
| Kıdemli personel | `Riskli` boş, hak 20 gün |
| İşe Başlama Tarihi yoksa | Kıdem kolonları boş bırakılır, kural uygulanmaz |

---

## 4. Kısmi rapor yuvarlama — 10 senaryo

Saatlik raporlar ay boyunca toplanır; artan kısım yarım günü (4 saat) aşmıyorsa yarım gün,
aşıyorsa tam gün olarak düşülür.

| # | Toplam saat | Beklenen gün kaybı |
|---|---:|---:|
| 41 | 0 | 0,0 |
| 42 | 1 | 0,5 |
| 43 | 4 | 0,5 |
| 44 | 5 | 1,0 |
| 45 | 8 | 1,0 |
| 46 | 12 | 1,5 |
| 47 | 13 | 2,0 |
| 48 | 16 | 2,0 |

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 49 | Aylık birikim | 3 ayrı 2 saatlik rapor = 6 saat → 1 tam gün |
| 50 | **İK'nın verdiği örnek** | Aşağıda |

### 50 — İK örneği

> Personel ayın 2. haftasında 2 saatlik eksik çalışma yaptı, o ay içerisinde farklı bir
> haftada 2 günlük yıllık izin kullandı, ayrıca yine farklı bir haftada 1 günlük resmi
> tatil var.

| Kalem | Gün |
|---|---:|
| 2 saatlik eksik çalışma | 0,5 |
| O haftanın hafta sonu | 2,0 |
| Yıllık izin | 2,0 |
| Resmi tatil | 1,0 |
| **Toplam kesinti** | **5,5** |
| Destek günü | 24,5 |

---

## 5. Girdi dosyası dayanıklılığı — 15 senaryo

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 51 | Eksik kolon | Hangi alanın eksik olduğu ve dosyada hangi kolonların bulunduğu söylenir |
| 52 | Boş dosya | Anlamlı hata mesajı verir |
| 53 | Mükerrer satırlar | Bir kez sayılır |
| 54 | Ters tarih aralığı | Bitiş < başlangıç ise tek güne çevrilir |
| 55 | Ek kolonlar | Sicil No, Departman kimliğin yanında çıktıya taşınır |
| 56 | Ek kolon satırdan satıra değişirse | Tüm farklı değerler `Ar-Ge / Üretim` biçiminde gösterilir |
| 57 | Eşanlamlı kolon adları | `Sicil No`, `Başlangıç Tarihi`, `Gün Sayısı` vb. tanınır; kimlik çıktıda dosyadaki adıyla görünür |
| 58 | **Ad Soyad kimlik olarak** | Çalışan numarası yoksa Ad Soyad kimlik kabul edilir |
| 59 | Numara ve ad birlikte | Numara kimlik olur, ad soyad bilgi kolonu olarak taşınır |
| 60 | **Elle eşleştirme** | Hiçbir kolon adı tanınmasa bile eşleştirmeyle hesap yapılır, sonuç birebir aynı |
| 61 | Büyük/küçük harf ve boşluk | `  ÇALIŞAN NUMARASI `, `izin türü` gibi yazımlar kabul edilir |
| 62 | Başlık üstünde blok | Firma adı/dönem satırları varsa gerçek başlık satırı bulunur |
| 63 | **Çok sayfalı dosya** | "Kurallar" gibi yardımcı sayfalar atlanır, veri sayfası seçilir |
| 64 | İşe Başlama Tarihi biçimi | Çıktıda `15.01.2020` olarak görünür, saat kısmı olmadan |
| 65 | Ek kolonsuz mevcut dosya | Çıktı kolonları değişmez |

---

## 6. Çıktı dosyaları — 2 senaryo

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 66 | İkili Excel çıktısı | 215 satırlık tüm personel ve 8 satırlık kesintili personel dosyası, aynı kolonlarla |
| 67 | Kesintili personel yoksa | İkinci dosya oluşturulmaz |

---

## 6b. Ayar dosyası (`ayarlar.json`) — 3 senaryo

Kolon eşanlamlıları, izin türleri, tatil takvimi ve teşvik taban günü kod dışında
tutulur; yeni bir kural için yeniden derleme gerekmez.

| Senaryo | Beklenen sonuç |
|---|---|
| Dışa aktar ve geri yükle | Dosyaya yazılır, düzenlenip yüklenince kurallar değişir |
| Bozuk dosya | Gömülü varsayılanlara dönülür **ve uyarı bırakılır** — sessizce yanlış hesaplanmaz |
| Dosya yoksa | Gömülü varsayılanlar kullanılır, uyarı üretilmez (normal durum) |

---

## 6c. Çok yıllı resmi tatil takvimi — 10 senaryo

Uygulama yıllarca kullanılacağı için takvimin hiçbir yıl boş kalmaması gerekir.

| Senaryo | Beklenen sonuç |
|---|---|
| Gelecek yılları kapsama | 2026–2035 arası her yılda en az 15 tatil bulunur |
| Sabit tatiller — 4 yıl | 1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz, 30 Ağustos, 28–29 Ekim her yıl üretilir |
| 2026 takvimi | Elle girilen tarihlerle üretilen takvim, önceki sabit listeyle birebir aynı |
| Doğrulanmamış yıl uyarısı | 2026 uyarı vermez; 2027 "doğrulanmadı" uyarısı verir |
| Arife ve bayram günleri | Ramazan arife + 3 gün, Kurban arife + 4 gün |
| Yılda iki bayram | 2033'te Ramazan hem Ocak hem Aralık'ta — ikisi de takvime girer |
| Ayar dosyasından doğrulama | Diyanet tarihi girilince o yıl doğrulanmış sayılır, uyarı kalkar |

Aritmetik Hicri takvim 2026'yı **birebir** tutturdu (0 gün sapma), ancak Diyanet
astronomik hesap kullandığı için diğer yıllarda bir gün kayabilir. Bu yüzden
hesaplanan tarihler doğrulanmış sayılmaz.

---

## 7. Tatil takvimi uyarısı — 2 senaryo

Program, dosyadaki izin gün sayılarını kendi resmi tatil takvimiyle karşılaştırır.

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 68 | Takvimden 15 Temmuz çıkarılırsa | 13–17 Temmuz aralıklı kayıtlarda sapma uyarısı üretilir |
| 69 | Takvim doğruysa | Uyarı üretilmez |

Bu kontrol geliştirme sırasında gerçek bir eksiği yakaladı: resmi tatil listesinde
**28 Ekim** (Cumhuriyet Bayramı Arifesi) yoktu ve İK sistemi onu tam gün tatil sayıyordu.

---

## Uçtan uca doğrulama

Testlerin dışında, paketlenmiş `.exe` içinde tek bir `.py` dosyası bulunmayan temiz bir
klasörde farklı girdi biçimleriyle çalıştırıldı:

| Girdi | Personel | Raporlu | Destek günü | Sonuç |
|---|---:|---:|---:|---|
| Çalışan numaralı dosya | 215 | 8 | 6.383 | Geçti |
| + Ad Soyad, Sicil No, Departman | 215 | 8 | 6.383 | Geçti |
| Farklı kolon adları + üst başlık bloğu | 215 | 8 | 6.383 | Geçti |
| Ad Soyad kimlikli, 2 sayfalı, ücretsiz izinli dosya | 15 | 2 | 408 | Geçti |
| Hiçbiri tanınmayan kolon adları + elle eşleştirme | 15 | 2 | 408 | Geçti |

Son iki satır aynı veriyi farklı kolon adlarıyla içerir; elle eşleştirme sonrası sonucun
birebir aynı çıkması, eşleştirme mekanizmasının doğru çalıştığını gösterir.

Ayrıca aynı pencerede arka arkaya farklı dosyalar yüklenerek dönemin, resmi tatil
listesinin ve sonuçların doğru yenilendiği doğrulandı: Temmuz dosyasından sonra bir
Ağustos dosyası seçildiğinde ay kendiliğinden Ağustos'a, tatil kutusu `30.08.2026`'ya
geçti; Temmuz'a dönüldüğünde ilk sonucun aynısı üretildi.

Kurulum dosyası da sınandı: yönetici yetkisi istemeden kuruluyor, Başlat menüsü kısayolu
6 saniyede açılıyor, kaldırma işlemi klasörü tamamen temizliyor.
