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
| I2 | Arife günleri **tam gün** tatil sayılır | VERİ | Teyitli |
| I3 | Hafta sonuna denk gelen resmi tatil ayrıca sayılmaz | VARSAYIM | Teyit gerekiyor |

> **I2 dayanağı:** Temmuz dosyasındaki bir kayıt 31 Aralık'a uzanıyordu ve İK
> sisteminin gün sayısı ancak **28 Ekim arifesi tam gün** sayılırsa tutuyordu.
> Bu, tahmin değil veriden çıkarılmış bir bulgu. Aynı kabul Ramazan ve Kurban
> arifeleri için de uygulandı.
>
> **Sorulacak soru:** Arife günleri gerçekten tam gün mü sayılıyor, yoksa yarım gün mü?
> Yarım günse sistemde tatil yapısının değişmesi gerekir.

### 2026 takvimi (sistemde tanımlı)

| Tarih | Tatil | Hafta içi mi? |
|---|---|---|
| 01.01.2026 | Yılbaşı | Perşembe |
| 19.03.2026 | Ramazan Bayramı Arifesi | Perşembe |
| 20–22.03.2026 | Ramazan Bayramı | 20'si Cuma, 21–22 hafta sonu |
| 23.04.2026 | Ulusal Egemenlik ve Çocuk Bayramı | Perşembe |
| 01.05.2026 | Emek ve Dayanışma Günü | Cuma |
| 19.05.2026 | Gençlik ve Spor Bayramı | Salı |
| 26.05.2026 | Kurban Bayramı Arifesi | Salı |
| 27–30.05.2026 | Kurban Bayramı | 30'u Cumartesi |
| 15.07.2026 | Demokrasi ve Millî Birlik Günü | Çarşamba |
| 30.08.2026 | Zafer Bayramı | **Pazar** |
| 28.10.2026 | Cumhuriyet Bayramı Arifesi | Çarşamba |
| 29.10.2026 | Cumhuriyet Bayramı | Perşembe |

> **Sorulacak soru:** Ramazan (19–22 Mart) ve Kurban (26–30 Mayıs) tarihleri doğru mu?
> Bunlar gerçek veriyle doğrulanamadı — Temmuz dosyası o aylara denk gelmiyor.
> 15.07 ve 28–29.10 veriyle doğrulandı.

---

## Özet — sorumlunuza sorulacak 8 madde

| # | Soru | Etkisi |
|---|---|---|
| 1 | Raporlu personelde yıllık izin düşüyor mu? (D3) | 5 personel, toplam 15 gün |
| 2 | Ücretsiz izinde hafta sonları da düşmeli mi? (H2) | Ücretsiz izinli her personel |
| 3 | Arife günleri tam gün mü, yarım gün mü? (I2) | Mart, Mayıs, Ekim dönemleri |
| 4 | Ramazan/Kurban 2026 tarihleri doğru mu? (I3) | Mart ve Mayıs dönemleri |
| 5 | `Destek Saat = Gün × 8` doğru mu? (A2) | Tüm çıktı |
| 6 | Ay sonu haftasının hafta sonu kaybolması kabul edilebilir mi? (E3) | Ay sonunda raporu biten personel |
| 7 | Yuvarlama eşiği yıllık izinde 4:30, raporda 4:00 — doğru mu? (G) | Şu an fark yaratmıyor |
| 8 | Hak edilenden fazla yıllık izin kullanımı işaretlensin mi? (F3) | Yeni özellik olurdu |

Cevaplar geldikçe `hesaplama.py` içindeki ilgili sabit güncellenir; çoğu için
`ayarlar.json` dosyasını düzenlemek bile yeterlidir.
