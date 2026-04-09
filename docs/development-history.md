# Development History

SDK genelinde eklenen her sınıf, fonksiyon ve önemli yapısal değişiklik bu tabloda kayıt altına alınır.

| Tarih | Modül | Sembol | Tür | Amaç / Kapsam | Kaynak Referans |
|---|---|---|---|---|---|
| 2026-04-09 | `core.config` | `ConfigManager` | Sınıf | Ortam değişkenlerinden merkezi konfigürasyon yönetimi. Spark ayarlarını CPU/RAM'e göre dinamik hesaplar. | `FilterData.py` — CONFIGURATION bölümü |
| 2026-04-09 | `core.geo_utils` | `haversineDistance` | Fonksiyon | İki koordinat arasındaki yüzey mesafesini metre cinsinden hesaplar (Haversine formülü). | `FilterData.py` — `haversine_distance()` |
| 2026-04-09 | `core.geo_utils` | `pointInPolygon` | Fonksiyon | Koordinatın GeoJSON polygon içinde olup olmadığını Shapely ile kontrol eder. | `FilterData.py` — `point_in_polygon()` |
| 2026-04-09 | `core.geo_utils` | `boundingBox` | Fonksiyon | Koordinat listesinden minimum sınırlayıcı dikdörtgeni hesaplar. Büyük veri ön filtresi için. | `FilterData.py` — bounding box hesabı |
| 2026-04-09 | `core.geo_utils` | `centroid` | Fonksiyon | Koordinat listesinin aritmetik merkezini hesaplar. | Geometrik yardımcı |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine` | Sınıf | Polygon veya Haversine bazlı unique device sayısı ve ham device listesi üretir. | `FilterData.py` — POLYGON/RADIUS processing |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getCountByPolygon` | Metod | Polygon içindeki unique device sayısı (Footfall Count — polygon mod). | `FilterData.py` — polygon UDF + stats |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getCountByRadius` | Metod | Haversine yarıçapı içindeki unique device sayısı (Footfall Count — haversine mod). | `FilterData.py` — radius UDF + stats |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getDeviceListByPolygon` | Metod | Polygon içindeki ham device ID listesi (Footfall Device List — polygon mod). | `FilterData.py` — polygon filtered_df |
| 2026-04-09 | `mobility.footfall_engine` | `FootfallEngine.getDeviceListByRadius` | Metod | Haversine yarıçapı içindeki ham device ID listesi (Footfall Device List — haversine mod). | `FilterData.py` — radius filtered_df |

---

## Gelecek Eklemeler

Planlanan özellikler için bkz. [future-features.md](future-features.md)
