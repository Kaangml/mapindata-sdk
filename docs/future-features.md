# Future Features — Geliştirme Yol Haritası

Bu dosya, SDK'nın gelecek sürümlerinde eklenecek özellikleri tanımlar.  
Buradaki hiçbir özellik mevcut sürümde implement edilmemiştir.

Katkı veya öncelik güncellemesi için PR açınız.

---

## FF-001 — Tek Device Takibi

**Modül:** `mobility`  
**Planlanan sınıf/metod:** `FootfallEngine.getDeviceHistory(deviceId, records)`  
**Açıklama:**  
Belirli bir `device_aid` değerine ait tüm konum kayıtlarını kronolojik olarak döndürür.  
Yolculuk analizi ve dwell time hesabına temel oluşturur.

---

## FF-002 — S3 Veri Okuma (`S3Client` / `loadData`)

**Modül:** `data`  
**Planlanan sınıf/metod:** `S3Client`, `S3Client.loadData(path, format)`  
**Açıklama:**  
S3'teki ham mobil veriyi (parquet, csv) okuyarak Spark DataFrame döndürür.  
İki bağlantı modu desteklenecek:

| Mod | Açıklama |
|---|---|
| `iam_role` | EC2 üzerinde çalışırken IAM role ile kimlik doğrulama |
| `access_key` | `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` ile kimlik doğrulama |

Çoklu S3 yolu ve partition filter (örn. `province=Istanbul`) desteği de kapsama dahildir.

---

## FF-003 — Çoklu Mobil Veri Kaynağı Desteği

**Modül:** `data`  
**Açıklama:**  
MapinData bünyesinde birden fazla mobil veri sağlayıcısı (echo, partner_x vb.) farklı S3  
prefix'lerinde tutulmaktadır. `loadData` fonksiyonu bu kaynakları birleştirerek standart bir  
schema'ya normalize edilmiş DataFrame döndürecektir.

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
**Planlanan metod:** `FootfallEngine.getHourlyDistribution(records, ...) -> dict`  
**Açıklama:**  
Filtrelenmiş kayıtları saat bazında gruplandırarak 24 saatlik dağılım tablosu döndürür.  
Yoğunluk haritaları ve dwell time analizine girdi sağlar.

---

## Kapsam Dışı (Bu Sürüm)

Aşağıdaki konular kasıtlı olarak kapsam dışında bırakılmıştır:

- Spark DataFrame entegrasyonu (FootfallEngine şu an saf Python list kabul eder)
- Gerçek zamanlı (streaming) veri işleme
- Görselleştirme (`viz` modülü ayrı geliştirme aşamasında)
