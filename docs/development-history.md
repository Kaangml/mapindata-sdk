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
| 2026-04-15 | `data.s3_client` | `S3Client.loadCleanMobilityData` | Metod | V2 H3 zenginleştirilmiş temiz veri yükler. `mobilityDataPath` üzerinden il bazlı S3 yolunu çözer; `MOBILITY_CLEAN_COLUMNS` varsayılan şemasını kullanır. FootfallEngine Spark metodlarının önerilen girdi kaynağı. |
| 2026-04-15 | `data.s3_client` | `MOBILITY_CLEAN_COLUMNS` | Sabit | V2 H3 veri setinin standart sütun listesi: `[timestamp, device_aid, latitude, longitude, horizontal_accuracy, neighborhood, h3_res9_id]` |
| 2026-04-15 | `data.s3_client` | `S3Client.createSession` (güncellendi) | Metod | `PYSPARK_PYTHON` ve `PYSPARK_DRIVER_PYTHON` ortam değişkenleri `sys.executable` olarak ayarlandı. Python 3.11 uyumsuzluk hatası önlendi. |
| 2026-04-15 | `core.config` | `ConfigManager.mobilityDataPath` | Metod | İl bazlı V2 H3 Parquet yolunu döndürür. İstanbul → `v2_h3_alt_dev_sorted` (200 m altitude filtreli), diğerleri → `v2_h3_dev_sorted`. `MAPIN_MOBILITY_DATA_SUFFIX` env override desteği. |
| 2026-04-15 | `core.config` | `ConfigManager.mobilitySparkConfig` (güncellendi) | Metod | Multipart boyutları 256 MB / 512 MB olarak güncellendi. `python.worker.reuse=true` ve `maxPartitionBytes=256MB` eklendi. |
| 2026-04-15 | `core.config` | `ConfigManager.testProvince` | Özellik | Test ve geliştirme ortamı için varsayılan il. `MAPIN_TEST_PROVINCE` env ile override edilebilir; varsayılan `istanbul`. |
| 2026-04-15 | `core.geo_utils` | `polygonAreaM2` | Fonksiyon | GeoJSON polygon alanını metre kare cinsinden hesaplar. Shoelace (Gauss) formülü + derece→metre dönüşümü. Küçük polygon eşik kararında kullanılır (< 100 000 m² → kring bazlı). |
| 2026-04-15 | `core.geo_utils` | `h3CentroidCell` | Fonksiyon | Koordinatın H3 hücresini INT64 olarak döndürür. Parquet `h3_res9_id` sütunuyla doğrudan karşılaştırılabilir. |
| 2026-04-15 | `core.geo_utils` | `h3PolygonCells` | Fonksiyon | GeoJSON polygon için H3 INT64 hücre listesi döndürür. `h3shape_to_cells` polyfill + `grid_disk(bufferK)` tampon. Büyük polygon H3 ön-filtresi için kullanılır. |
| 2026-04-15 | `core.geo_utils` | `autoKringK` | Fonksiyon | Polygon kenar uzunluğuna göre kring k değerini (`0` veya `1`) otomatik seçer. Küçük polygon → k=1, büyük polygon → k=0. H3 res9 çap eşiği ≈ 174 m. |
| 2026-04-15 | `mobility.footfall_engine` | `FootfallEngine._filterByPolygonSpark` (güncellendi) | Metod | 3-katmanlı pipeline: BBox ön-filtre → H3 hücre ön-filtre (`h3PolygonCells` veya `autoKringK`) → PiP UDF (Shapely). H3 ön-filtresi Parquet row-group skip'i etkinleştirir; benchmark: 6–14× hızlanma. |
| 2026-04-15 | `mobility.footfall_engine` | `FootfallEngine._filterByRadiusSpark` (güncellendi) | Metod | BBox ön-filtre → H3 kring ön-filtre (`k = ceil(radius / 174m)`) → Spark-native Haversine. Python UDF kullanmaz; Catalyst tarafından tam optimize edilir. k formülü düzeltildi: 87 m → 174 m (hücre çapı). |
| 2026-04-15 | `mobility.footfall_engine` | `FootfallEngine.fetchDeviceRecords` | Metod | Device ID listesine göre tüm mobil kayıtları döndürür. ≤ 1000 cihaz → `isin` filtresi; > 1000 cihaz → broadcast join. |

---

## Gelecek Eklemeler

Planlanan özellikler için bkz. [future-features.md](future-features.md)

