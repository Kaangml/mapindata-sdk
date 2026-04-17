# Future Features — Geliştirme Yol Haritası

Bu dosya, SDK'nın gelecek sürümlerinde eklenecek özellikleri tanımlar.  
Buradaki hiçbir özellik mevcut sürümde implement edilmemiştir.

Bir özellik tamamlandığında buradan **silinir** ve [development-history.md](development-history.md) tablosuna eklenir.  
Katkı veya öncelik güncellemesi için PR açınız.

---

## FF-001 — Çoklu Device Takibi (DataFrame Bazlı)

**Modül:** `mobility`  
**Planlanan sınıf/metod:** `FootfallEngine.getDeviceHistory(devicesDF, mobilityDF)`  
**Açıklama:**  
Bir Spark DataFrame içindeki tüm device_aid değerlerini alarak bu cihazlara ait tüm
mobil veri sinyallerini tam mobility verisinden filtreler ve döndürür.  
Tek cihaz değil; bir footfall analizinden çıkan device seti için toplu yolculuk/konum
geçmişi çıkartmayı hedefler (örn. `getDeviceListByPolygonSpark` çıktısını girdi olarak alır).  
Dwell time, güzergah analizi ve motivation analizi için temel oluşturur.

---

## FF-003 — Çoklu Mobil Veri Kaynağı Desteği

**Modül:** `data`  
**Açıklama:**  
MapinData bünyesinde birden fazla mobil veri sağlayıcısı (echo, partner_x vb.) farklı S3  
prefix'lerinde tutulmaktadır. `S3Client.loadMobilityData` bu kaynakları birleştirerek standart  
bir schema'ya normalize edilmiş DataFrame döndürecektir.

---

## FF-004 — Polygon Yükleme (`loadPolygon`)

**Modül:** `core` veya `data`  
**Planlanan fonksiyon:** `loadPolygon(path)` → `dict`  
**Açıklama:**  
GeoJSON veya Shapefile formatındaki polygon dosyalarını yükler.  
S3 yolu veya yerel dosya yolunu kabul eder.  
`FootfallEngine` ile doğrudan entegrasyon hedeflenmektedir.

---

## FF-005 — Saatlik Dağılım (`getHourlyDistribution`)

**Modül:** `mobility`  
**Planlanan metod:** `FootfallEngine.getHourlyDistribution(df, ...) -> dict`  
**Açıklama:**  
Filtrelenmiş kayıtları saat bazında gruplandırarak 24 saatlik dağılım tablosu döndürür.  
Yoğunluk haritaları ve dwell time analizine girdi sağlar. Spark DataFrame kabul eder.

---

## Kapsam Dışı (Bu Sürüm)

Aşağıdaki konular kasıtlı olarak kapsam dışında bırakılmıştır:

- Gerçek zamanlı (streaming) veri işleme
- Görselleştirme (`viz` modülü ayrı geliştirme aşamasında)

---

## Katkıda Bulunanlar

| Ad | Rol |
|---|---|
| Kaan Gümele | SDK Geliştirici |

