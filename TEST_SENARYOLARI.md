# Test Senaryoları

51 senaryo, altı başlıkta. Tamamı `test_hesaplama.py` içinde kodlanmıştır ve her
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
| 12 | Tatil takvimi tutarlılığı | 367 kaydın hiçbirinde sapma uyarısı çıkmaz |
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

## 3. Kısmi gün yuvarlama — 10 senaryo

Saatlik raporlar ay boyunca toplanır; artan kısım yarım günü (4 saat) aşmıyorsa yarım gün,
aşıyorsa tam gün olarak düşülür.

| # | Toplam saat | Beklenen gün kaybı |
|---|---:|---:|
| 28 | 0 | 0,0 |
| 29 | 1 | 0,5 |
| 30 | 4 | 0,5 |
| 31 | 5 | 1,0 |
| 32 | 8 | 1,0 |
| 33 | 12 | 1,5 |
| 34 | 13 | 2,0 |
| 35 | 16 | 2,0 |

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 36 | Aylık birikim | 3 ayrı 2 saatlik rapor = 6 saat → 1 tam gün |
| 37 | **İK'nın verdiği örnek** | Aşağıda |

### 37 — İK örneği

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

## 4. Girdi dosyası dayanıklılığı — 10 senaryo

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 38 | Eksik kolon | Hangi kolonun eksik olduğu ve dosyada hangilerinin bulunduğu söylenerek durulur |
| 39 | Boş dosya | Anlamlı hata mesajı verir |
| 40 | Mükerrer satırlar | Bir kez sayılır |
| 41 | Ters tarih aralığı | Bitiş < başlangıç ise tek güne çevrilir |
| 42 | Ek kolonlar | Ad Soyad, Sicil No, Departman çalışan numarasının yanında çıktıya taşınır |
| 43 | Ek kolon satırdan satıra değişirse | Tüm farklı değerler `Ar-Ge / Üretim` biçiminde gösterilir |
| 44 | Eşanlamlı kolon adları | `Sicil No`, `Başlangıç Tarihi`, `Gün Sayısı` vb. tanınır |
| 45 | Büyük/küçük harf ve boşluk | `  ÇALIŞAN NUMARASI `, `izin türü` gibi yazımlar kabul edilir |
| 46 | Başlık üstünde blok | Firma adı/dönem satırları varsa gerçek başlık satırı bulunur |
| 47 | Ek kolonsuz mevcut dosya | Çıktı kolonları değişmez |

---

## 5. Çıktı dosyaları — 2 senaryo

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 48 | İkili Excel çıktısı | 215 satırlık tüm personel ve 8 satırlık kesintili personel dosyası, aynı kolonlarla |
| 49 | Kesintili personel yoksa | İkinci dosya oluşturulmaz |

---

## 6. Tatil takvimi uyarısı — 2 senaryo

Program, dosyadaki izin gün sayılarını kendi resmi tatil takvimiyle karşılaştırır.

| # | Senaryo | Beklenen sonuç |
|---|---|---|
| 50 | Takvimden 15 Temmuz çıkarılırsa | 13–17 Temmuz aralıklı kayıtlarda sapma uyarısı üretilir |
| 51 | Takvim doğruysa | Uyarı üretilmez |

Bu kontrol geliştirme sırasında gerçek bir eksiği yakaladı: resmi tatil listesinde
**28 Ekim** (Cumhuriyet Bayramı Arifesi) yoktu ve İK sistemi onu tam gün tatil sayıyordu.

---

## Uçtan uca doğrulama

Testlerin dışında, paketlenmiş `.exe` içinde tek bir `.py` dosyası bulunmayan temiz bir
klasörde üç farklı girdi biçimiyle çalıştırıldı:

| Girdi | Personel | Raporlu | Destek günü | Sonuç |
|---|---:|---:|---:|---|
| Orijinal dosya | 215 | 8 | 6.383 | Geçti |
| + Ad Soyad, Sicil No, Departman | 215 | 8 | 6.383 | Geçti |
| Farklı kolon adları + üst başlık bloğu | 215 | 8 | 6.383 | Geçti |

Ayrıca aynı pencerede arka arkaya farklı dosyalar yüklenerek dönemin, resmi tatil
listesinin ve sonuçların doğru yenilendiği doğrulandı: Temmuz dosyasından sonra bir
Ağustos dosyası seçildiğinde ay kendiliğinden Ağustos'a, tatil kutusu `30.08.2026`'ya
geçti; Temmuz'a dönüldüğünde ilk sonucun aynısı üretildi.

Kurulum dosyası da sınandı: yönetici yetkisi istemeden kuruluyor, Başlat menüsü kısayolu
6 saniyede açılıyor, kaldırma işlemi klasörü tamamen temizliyor.
