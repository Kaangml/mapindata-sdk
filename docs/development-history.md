# Development History

SDK genelinde eklenen her sınıf, fonksiyon ve önemli yapısal değişiklik bu tabloda kayıt altına alınır.

| Tarih | Modül | Sembol | Tür | Amaç / Kapsam |
|---|---|---|---|---|
| 2026-04-09 | `core.config` | `ConfigManager` | Sınıf | Ortam değişkenlerinden merkezi konfigürasyon. AWS, S3, Spark, DB ve genel ayarları yönetir. Spark bellek/paralellik değerleri sistem RAM ve CPU'ya göre otomatik hesaplanır. |
| 2026-04-09 | `core.config` | `ConfigManager.mobilitySparkConfig` | Metod | Büyük ölçekli mobil veri işleme için optimize edilmiş Spark konfigürasyon sözlüğü döndürür. S3A, Kryo, Adaptive Query Execution ve bellek ayarlarını içerir. |
| 2026-04-09 | `core.geo_utils` | `haversineDistance` | Fonksiyon | İki (lat, lon) koordinatı arasındaki yüzey mesafesini Haversine formülüyle metre cinsinden hesaplar. |
| 2026-04-09 | `core.geo_utils` | `pointInPolygon` | Fonksiyon | Verilen koordinatın GeoJSON formatındaki polygon içinde olup olmadığını Shapely ile kontrol eder. GeoJSON'ın [lon, lat] sırasını dahili olarak yönetir. |
| 2026-04-09 | `core.geo_utils` | `boundingBox` | Fonksiyon | Koordinat listesinden minimum sınırlayıcı dikdörtgen (min/max lat-lon) hesaplar. Büyük veri kümelerini S3'ten okurken ön filtre olarak kullanılır. |
| 2026-04-09 | `core.geo_utils` | `centroid` | Fonksiyon | Koordinat listesinin aritmetik merkezini (ortalama lat, lon) hesaplar. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine` | Sınıf | Mobil konum verisi üzerinden ayak izi metrikleri hesaplar. Pure Python (list[dict]) ve Spark DataFrame olmak üzere iki çalışma modu sunar. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getCountByPolygon` | Metod | Pure Python modu: polygon içindeki unique device sayısını döndürür. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getCountByRadius` | Metod | Pure Python modu: Haversine yarıçapı içindeki unique device sayısını döndürür. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getDeviceListByPolygon` | Metod | Pure Python modu: polygon içindeki unique device ID listesini döndürür. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getDeviceListByRadius` | Metod | Pure Python modu: Haversine yarıçapı içindeki unique device ID listesini döndürür. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getCountByPolygonSpark` | Metod | Spark modu: Spark DataFrame üzerinde polygon UDF filtresi ile unique device sayısı. Büyük/S3 verisi için. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getCountByRadiusSpark` | Metod | Spark modu: Spark DataFrame üzerinde Haversine UDF filtresi ile unique device sayısı. |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getDeviceListByPolygonSpark` | Metod | Spark modu: Polygon içindeki device ID'leri Spark DataFrame olarak döndürür (collect() kullanıcıya bırakılır). |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getDeviceListByRadiusSpark` | Metod | Spark modu: Haversine yarıçapı içindeki device ID'leri Spark DataFrame olarak döndürür. |
| 2026-04-09 | `data.s3_client` | `S3Client` | Sınıf | S3 üzerindeki büyük ölçekli mobil veri dosyalarını PySpark ile okur. IAM Role ve Access Key olmak üzere iki kimlik doğrulama modunu destekler. |
| 2026-04-09 | `data.s3_client` | `S3Client.createSession` | Metod | mobilitySparkConfig ile optimize edilmiş Spark oturumu oluşturur; S3A multipart ayarlarını Hadoop config'e de uygular. |
| 2026-04-09 | `data.s3_client` | `S3Client.loadData` | Metod | S3'teki herhangi bir parquet/csv dosyasını Spark DataFrame olarak okur. basePath ile partition tabanlı tablo desteği sağlar. |
| 2026-04-09 | `data.s3_client` | `S3Client.loadMobilityData` | Metod | MapinData standart echo_data_partitioned şemasından mobil veri yükler. Province bazlı partition filter ve varsayılan sütun seçimi içerir. |

---

## Gelecek Eklemeler

Planlanan özellikler için bkz. [future-features.md](future-features.md)

