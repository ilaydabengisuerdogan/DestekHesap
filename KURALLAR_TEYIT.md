# Uygulanan Kurallar — Teyit Listesi

Bu belge, uygulamanın **şu anda uyguladığı** kuralları kaynaklarıyla birlikte listeler.
Her kuralın yanında nereden geldiği ve teyit durumu belirtilmiştir.

Kaynak kısaltmaları:

| Kısaltma | Anlamı |
|---|---|
| **İK-1** | İlk sözlü/yazılı talimat (hesaplama örneğinin verildiği mesaj) |
| **İK-2** | İzin raporu dosyasındaki "Kurallar ve Açıklama" sayfası |
| **İK-3** | "Izin_Sistemi_Revizyon_Prompt" revizyon talimatı |
| **VERİ** | Gerçek Temmuz 2026 dosyasından doğrulandı |
| **VARSAYIM** | Kaynaklarda açıkça belirtilmedi, tarafımızca yorumlandı |

---

## A. Temel hesap

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| A1 | Teşvik **30 gün** üzerinden hesaplanır | İK-1 | Teyitli |
| A2 | `Destek Saat = Destek Gün × 8` | VARSAYIM | **Teyit gerekiyor** |
| A3 | Destek günü negatife düşmez, en az 0 olur | VARSAYIM | Teyit gerekiyor |

> **A2 sorusu:** Teknoparkın saat karşılığı 8 saat/gün mü? Farklıysa tek satırda değişir.

---

## B. Rapor (sağlık raporu) tespiti

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| B1 | Rapor = `İzin Türü` **Şirket Dışında Olma Nedeni** ve `İzin Nedeni` **Hastalık Raporu** veya **Kadın Doğum İstirahat Raporu** | İK-1, VERİ | Teyitli |
| B2 | Rapor günleri teşvikten düşer | İK-1, İK-2 | Teyitli |

---

## C. Raporu OLMAYAN personel

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| C1 | Yıllık izin **düşmez** | İK-1, İK-2 | Teyitli |
| C2 | Resmi tatil **düşmez** | İK-1 | Teyitli |
| C3 | Mazeret izni **düşmez** | İK-2, İK-3 | Teyitli |
| C4 | Ücretsiz izin **düşer** | İK-2, İK-3 | Teyitli |

---

## D. Raporu OLAN personel

Aşağıdakiler teşvikten düşer:

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| D1 | Rapor günleri (hafta sonu ve resmi tatil hariç iş günleri) | İK-1 | Teyitli |
| D2 | Raporun değdiği **her** haftanın Cumartesi + Pazar günleri | İK-1 | Teyitli |
| D3 | O ay içindeki **yıllık izin** günleri | İK-1 | Teyitli |
| D4 | O ay içindeki hafta içine denk gelen **resmi tatiller** | İK-1 | Teyitli |
| D5 | Ücretsiz izin | İK-2, İK-3 | Teyitli |
| D6 | Mazeret ve evlilik izni **düşmez** | İK-2, İK-3 | Teyitli |

> ### ⚠ D3 için dikkat — belgeler arasında görünürde çelişki var
>
> **İK-2** ve **İK-3**'teki tablo "Yıllık İzin (ücretli) → Destek Devam Eder" diyor.
> Bu, yıllık iznin hiç düşmemesi gerektiği gibi okunabilir.
>
> Ancak **İK-3'ün Kural 1 istisnası** şöyle diyor: *"1 yılını doldurmamış personelin
> yıllık izin kaydı, aynı dönemde hastalık raporu alınmış olsa **dahi** düşülmemeli."*
> Buradaki "dahi" ifadesi, **normalde raporlu personelde düştüğünü** varsayar.
>
> Bu nedenle şu yorum uygulandı: tablo genel durumu (raporsuz personel) anlatıyor,
> raporlu personelde o ayın yıllık izni düşüyor.
>
> **Sorulacak soru:** Raporlu bir personelin o ay kullandığı yıllık izin teşvikten
> düşüyor mu, düşmüyor mu? Düşmüyorsa Temmuz sonuçları değişir:
> 1079 → 26, 1179 → 18, 1192 → 26, 1303 → 26, 1345 → 28 (toplam 6.383 → 6.398).

---

## E. Hafta sonu kuralı

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| E1 | Rapor haftasının hafta sonu düşer | İK-1 | Teyitli |
| E2 | Rapor birden çok haftaya yayılırsa **her** haftanın hafta sonu düşer | İK-1 | Teyitli |
| E3 | Hafta sonu yalnızca **dönem ayının içine düşerse** sayılır | İK-1 | Teyitli |

> ### ⚠ E3'ün sonucu — teyit edilmesi iyi olur
>
> 27–31 Temmuz haftasının hafta sonu 1–2 Ağustos olduğu için Temmuz'dan düşmüyor.
> Raporu ay içinde biten bir personel (1333, 1345) Ağustos'ta raporlu görünmeyeceği
> için o hafta sonu **hiçbir aydan düşmüyor**.
>
> **Sorulacak soru:** Bu kabul edilebilir mi, yoksa ay sonu haftası için ayrı bir
> kural mı gerekir?

---

## F. Kıdem şartı (İş Kanunu Md. 53)

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| F1 | 1 yılını doldurmamış personelin yıllık izni, raporu olsa dahi **düşmez** | İK-2, İK-3 | Teyitli |
| F2 | Bu kayıt çıktıda `Riskli = Evet` olarak işaretlenir | İK-3 | Teyitli |
| F3 | Kıdem kademeleri: 1–5 yıl → 14 gün, 5–15 yıl → 20 gün, 15+ yıl → 26 gün | İK-2, İK-3 | Teyitli |
| F4 | Kıdem, gün sayısıyla değil **takvim yıldönümüyle** hesaplanır | VARSAYIM | Teyit gerekiyor |
| F5 | `İşe Başlama Tarihi` kolonu yoksa kural uygulanmaz, kolonlar boş kalır | İK-3 | Teyitli |

> **F4 notu:** 365 gün saymak yerine yıldönümü karşılaştırılıyor; artık yıllarda gün
> hesabı bir gün kaydığı için. Sınır tarihlerde fark yaratır.
>
> **F3 notu:** Kademeler çıktıda bilgi olarak gösteriliyor ama **hesaba girmiyor** —
> yani "14 gün hakkı varken 20 gün kullanmış" gibi bir kontrol yapılmıyor.
> **Sorulacak soru:** Hak edilenden fazla yıllık izin kullanımı da işaretlensin mi?

---

## G. Gün sayımı ve yuvarlama

### G1. Yıllık izinde (İK-3, Kural 3)

| Durum | Sonuç | Durum |
|---|---|---|
| Tek yarım gün (0,5) | **1 tam gün** | Teyitli |
| İki ayrı günde 0,5 + 0,5 | **1 tam gün** (iki ayrı gün değil) | Teyitli |
| Bir günde **4 saat 30 dk üzeri** izin | O gün tam gün | Teyitli |
| Toplam yarım günler | Toplanıp yukarı yuvarlanır (3,5 → 4) | Teyitli |

### G2. Kısmi raporda / eksik çalışmada (İK-1)

| Durum | Sonuç | Durum |
|---|---|---|
| Eksik saat ≤ **4 saat** | Yarım gün | Teyitli |
| Eksik saat > **4 saat** | Tam gün | Teyitli |
| Aylık birikim | Saatler toplanır, artan kısım yuvarlanır | VARSAYIM |

> ### ⚠ G1 ve G2 farklı eşikler kullanıyor
>
> Yıllık izinde eşik **4:30**, kısmi raporda **4:00**. Bunun sebebi iki farklı
> belgenin iki farklı sayı vermesi: İK-1 "yarım günün altı/üstü" (4 saat) diyor,
> İK-3 açıkça "4 saat 30 dakika" diyor.
>
> Mevcut veride 4 ile 4,5 saat arasında hiç kayıt yok, yani bugün fark yaratmıyor.
>
> **Sorulacak soru:** İki eşik de doğru mu, yoksa ikisi de 4:30 mu olmalı?

---

## H. Ücretsiz izin

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| H1 | Ücretsiz izin, rapor durumundan bağımsız olarak **her personelde** düşer | İK-2, İK-3 | Teyitli |
| H2 | Yalnızca **iş günleri** düşer; hafta sonu ve resmi tatil sayılmaz | VARSAYIM | **Teyit gerekiyor** |

> ### ⚠ H2 — en önemli açık soru
>
> Ücretsiz izinde SGK primi yatmıyorsa, o dönemin hafta sonlarında da yatmıyor
> olabilir. Belgeler bu noktayı belirtmiyor, literal okuma yapıldı.
>
> **Örnek:** Onur Kurt 13–24 Temmuz ücretsiz izinde.
> - Şu anki hesap: 9 iş günü düşer → destek 21 gün
> - Hafta sonları da düşerse: 9 + 4 hafta sonu (18-19, 11-12 hariç) = 12 gün → destek 18
>
> **Sorulacak soru:** Ücretsiz izin döneminde hafta sonları da teşvikten düşmeli mi?

---

## I. Resmi tatil takvimi

| # | Kural | Kaynak | Durum |
|---|---|---|---|
| I1 | Dini bayramlar da resmi tatil sayılır | İK (sözlü bilgilendirme) | Teyitli |
| I2 | Arife günleri **yarım gün** sayılır | İK talimatı | **Teyitli** |
| I3 | Hafta sonuna denk gelen resmi tatil ayrıca sayılmaz | VARSAYIM | Teyit gerekiyor |

> **I2 — kapandı.** Ramazan, Kurban ve 28 Ekim arifeleri yarım gün sayılır.
> O güne denk gelen rapor veya izin 0,5 gün kaybettirir; çalışılmışsa resmi
> tatil kesintisi 0,5 gündür.
>
> **Bilinen fark:** İK'nın izin raporunu üreten sistem arifeyi **tam gün**
> sayıyor. Bu, 1043 numaralı personelin 16.07–31.12 kaydında görülüyor:
> dosyada 119 gün yazıyor, bizim hesabımız 119,5. Fark tam olarak 28 Ekim'den
> geliyor ve **beklenen bir farktır** — çıktının `Uyarı` kolonunda böyle
> belirtilir, işlem gerektirmez.

### Takvim nasıl üretiliyor

Dini bayramlar her yıl kaydığı için takvim üç katmanlı çalışır:

1. **Sabit tarihli tatiller** — 1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz,
   30 Ağustos, 28–29 Ekim. Her yıl aynı gündedir, koddan otomatik üretilir.
   Bu kalemde hata riski yoktur.
2. **Dini bayramlar** — Diyanet takviminden teyit edilmiş yıllar listede tutulur.
   Listede olmayan yıllar **aritmetik Hicri takvimden hesaplanır** ve
   "doğrulanmadı" sayılır; program o dönemde uyarı gösterir.
3. **`ayarlar.json`** — yukarıdakilerin hepsini ezebilir.

Şu an **yalnızca 2026 doğrulanmış** durumda. 2020–2040 arası tüm yıllar takvimde
var, ama 2026 dışındakilerin dini bayram tarihleri hesaplanmıştır.

### Hesaplanan dini bayram tarihleri (teyit edilmeli)

| Yıl | Ramazan Bayramı (arife dahil) | Kurban Bayramı (arife dahil) |
|---|---|---|
| **2026** | 19–22 Mart ✔ doğrulanmış | 26–30 Mayıs ✔ doğrulanmış |
| 2027 | 09–12 Mart | 16–20 Mayıs |
| 2028 | 26–29 Şubat | 04–08 Mayıs |
| 2029 | 14–17 Şubat | 23–27 Nisan |
| 2030 | 04–07 Şubat | 13–17 Nisan |
| 2031 | 24–27 Ocak | 02–06 Nisan |
| 2032 | 13–16 Ocak | 21–25 Mart |
| 2033 | 02–05 Ocak **ve** 22–25 Aralık | 11–15 Mart |

> Algoritma 2026'yı **birebir** tutturdu (0 gün sapma), ama Diyanet astronomik
> hesap kullandığı için bazı yıllarda 1 gün kayabilir.
>
> **Sorulacak soru:** Yukarıdaki tarihler Diyanet takvimiyle uyuşuyor mu?
> Teyit edilen yıl `ayarlar.json` içindeki `dogrulanmis_dini_bayramlar`
> bölümüne eklenince uyarı kalkar — kod değişikliği gerekmez:
>
> ```json
> "dogrulanmis_dini_bayramlar": {
>   "2026": { "ramazan": "20.03.2026", "kurban": "27.05.2026" },
>   "2027": { "ramazan": "10.03.2027", "kurban": "17.05.2027" }
> }
> ```
> (Girilen tarih bayramın **1. günüdür**; arife ve kalan günler otomatik eklenir.)

---

## Özet — sorumlunuza sorulacak 8 madde

| # | Soru | Etkisi |
|---|---|---|
| 1 | Raporlu personelde yıllık izin düşüyor mu? (D3) | 5 personel, toplam 15 gün |
| 2 | Ücretsiz izinde hafta sonları da düşmeli mi? (H2) | Ücretsiz izinli her personel |
| ~~3~~ | ~~Arife günleri tam gün mü, yarım gün mü?~~ **Kapandı: yarım gün** | — |
| 4 | Hesaplanan dini bayram tarihleri Diyanet'le uyuşuyor mu? (I) | 2027 ve sonrası |
| 5 | `Destek Saat = Gün × 8` doğru mu? (A2) | Tüm çıktı |
| 6 | Ay sonu haftasının hafta sonu kaybolması kabul edilebilir mi? (E3) | Ay sonunda raporu biten personel |
| 7 | Yuvarlama eşiği yıllık izinde 4:30, raporda 4:00 — doğru mu? (G) | Şu an fark yaratmıyor |
| 8 | Hak edilenden fazla yıllık izin kullanımı işaretlensin mi? (F3) | Yeni özellik olurdu |

Cevaplar geldikçe `hesaplama.py` içindeki ilgili sabit güncellenir; çoğu için
`ayarlar.json` dosyasını düzenlemek bile yeterlidir.
