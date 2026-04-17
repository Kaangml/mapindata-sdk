# FootfallEngine + DuckDBClient — API Referansı

`mapindata.mobility.footfall_engine` ve `mapindata.data.duckdb_client` modülleri,
büyük ölçekli S3 Parquet verisi üzerinde ayak izi (footfall) analizlerini kapsayan
birleşik API sunar.

---

## Genel Bakış

### Desteklenen Analizler

| Analiz | Metod | Çıktı |
|---|---|---|
| Polygon footfall sayısı | `getCountByPolygon` | `int` |
| Radius footfall sayısı | `getCountByRadius` | `int` |
| Polygon device listesi | `getDeviceList` | `list[str]` / DataFrame |
| Radius device listesi | `getDeviceListByRadius` | `list[str]` / DataFrame |
| Device yolculuğu | `fetchDeviceRecords` | `pandas.DataFrame` / Spark DataFrame |

### Motor Seçimi

Her metod `engine` parametresi alır:

| `engine=` | Motor | Hız (polygon) | Hız (radius) |
|---|---|---|---|
| `"duckdb"` (varsayılan) | DuckDB 1.5.2 + httpfs | **~70× Spark'tan hızlı** | ~3× Spark'tan hızlı |
| `"spark"` | PySpark 3.5.0 | Referans | Referans |

> **Benchmark (İstanbul rowsorted verisi — 71.7 GB / 130 dosya):**
>
> | Sorgu | Spark | DuckDB | Kazanım |
> |---|---:|---:|---:|
> | Taksim 0.056 km² polygon | 17.6 sn | 0.24 sn | 73× |
> | Beşiktaş 1.1 km² polygon | 133.9 sn | 2.07 sn | 65× |
> | Bağcılar 17 km² polygon | 387.8 sn | 5.18 sn | 75× |
> | Radius 300–1000 m (ort.) | 4.9 sn | 1.7 sn | 2.9× |
> | 100 cihaz journey | 52.3 sn | 11.6 sn | 4.5× |

---

## DuckDBClient

```python
from mapindata.data.duckdb_client import DuckDBClient
from mapindata.core.config import ConfigManager
```

### `DuckDBClient(config)`

| Parametre | Tip | Açıklama |
|---|---|---|
| `config` | `ConfigManager` | Ortam değişkenlerini yönetir |

### `.connect() → duckdb.DuckDBPyConnection`

DuckDB bağlantısını başlatır.

- `httpfs` + `spatial` extension kurulur/yüklenir
- AWS kimlik bilgileri `boto3.DefaultCredentialChain` üzerinden aktarılır
- Thread sayısı `ConfigManager.sparkMaster` üzerinden türetilir (`local[8]` → 8 thread)
- Zaten açık bağlantı varsa mevcut bağlantı döner

### `.s3Path(province) → str`

| Parametre | Örnek |
|---|---|
| `"istanbul"` | `s3://mapindata-athena/results/bench_spatial/istanbul/v2_h3_alt_consolidated/*.parquet` |
| `"ankara"` | `s3://mapindata-athena/results/bench_spatial/ankara/v2_h3_dev_sorted/*.parquet` |

`ConfigManager.mobilityDataPath()` üzerinden veri yolunu türetir; `s3a://` → `s3://` dönüşümü ve `*.parquet` glob eklemesi otomatik yapılır.

### `.close()`

Bağlantıyı kapatır.

---

## FootfallEngine

```python
from mapindata.mobility.footfall_engine import FootfallEngine, ENGINE_DUCKDB, ENGINE_SPARK
```

### `FootfallEngine(df, con, s3Path, latCol, lonCol, deviceCol)`

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `df` | `None` | Spark DataFrame — `engine="spark"` için |
| `con` | `None` | DuckDB bağlantısı — `engine="duckdb"` için |
| `s3Path` | `None` | DuckDB S3 glob yolu — `engine="duckdb"` için |
| `latCol` | `"latitude"` | Enlem sütunu adı |
| `lonCol` | `"longitude"` | Boylam sütunu adı |
| `deviceCol` | `"device_aid"` | Cihaz ID sütunu adı |

**Hızlı başlangıç — DuckDB (önerilen):**

```python
from mapindata.core.config import ConfigManager
from mapindata.data.duckdb_client import DuckDBClient
from mapindata.mobility.footfall_engine import FootfallEngine

cfg = ConfigManager()
duck = DuckDBClient(cfg)
con = duck.connect()

engine = FootfallEngine(con=con, s3Path=duck.s3Path("istanbul"))
```

**Hızlı başlangıç — Spark:**

```python
from mapindata.data.s3_client import S3Client

s3 = S3Client(cfg)
s3.createSession("FootfallJob")
df = s3.loadCleanMobilityData("istanbul")

engine = FootfallEngine(df=df)
```

---

### `getCountByPolygon(polygonCoords, engine="duckdb") → int`

Polygon / MultiPolygon içindeki unique device sayısını döndürür.

**Coğrafi girdi formatları:**

| Format | Örnek |
|---|---|
| Polygon koordinat listesi | `[[[28.97, 41.01], [28.98, 41.01], ...]]` |
| MultiPolygon koordinat listesi | `[[[[28.97, 41.01], ...]], [[[29.1, 41.2], ...]]]` |
| GeoJSON dosya yolu | `"data/taksim.json"` |
| GeoJSON dict (Feature/Geometry) | `{"type": "Polygon", "coordinates": [...]}` |

```python
# Polygon koordinat
count = engine.getCountByPolygon([[[28.97, 41.01], [28.98, 41.01], [28.98, 41.02], [28.97, 41.01]]])

# GeoJSON dosyası
count = engine.getCountByPolygon("data/besiktas.json")

# Spark motoru
count = engine.getCountByPolygon(coords, engine="spark")
```

---

### `getCountByRadius(centerLat, centerLon, radiusMeters, engine="duckdb") → int`

Haversine yarıçapı içindeki unique device sayısını döndürür.

```python
count = engine.getCountByRadius(41.037, 28.985, 300)          # Taksim 300m, DuckDB
count = engine.getCountByRadius(41.037, 28.985, 300, engine="spark")  # Spark
```

---

### `getDeviceList(polygonCoords, engine="duckdb")`

Polygon içindeki unique device ID listesi.

- DuckDB: `list[str]` (sıralı)
- Spark: `pyspark.sql.DataFrame` (`device_aid` sütunu)

```python
devices = engine.getDeviceList("data/kadikoy.json")
```

### `getDeviceListByRadius(centerLat, centerLon, radiusMeters, engine="duckdb")`

Radius içindeki unique device ID listesi. Aynı dönüş formatı.

---

### `fetchDeviceRecords(deviceIds, engine="duckdb")`

Belirtilen cihazların tüm konum kayıtlarını döndürür.

- DuckDB: `pandas.DataFrame`
- Spark: `pyspark.sql.DataFrame`

| Device sayısı | DuckDB | Spark |
|---|---|---|
| ≤ 1 000 | `IN (...)` clause | `.isin()` filtresi |
| > 1 000 | Geçici tablo + JOIN | Broadcast join |

```python
records = engine.fetchDeviceRecords(["devid-001", "devid-002"])
```

---

## MultiPolygon Desteği

Birden fazla ayrık alan için `MultiPolygon` kullanılır.

```python
# İki ayrı mahalle/bölge birlikte sorgulanır
multi_coords = [
    # Taksim
    [[[28.97, 41.037], [28.98, 41.037], [28.98, 41.043], [28.97, 41.037]]],
    # Kadıköy
    [[[29.02, 40.98], [29.03, 40.98], [29.03, 40.99], [29.02, 40.98]]],
]
count = engine.getCountByPolygon(multi_coords)

# GeoJSON dosyasından MultiPolygon
count = engine.getCountByPolygon("data/istanbul_ilceler.json")
```

**Motor davranışı:**

| Motor | MultiPolygon |
|---|---|
| DuckDB | Her polygon için ayrı `WHERE ST_Contains(...)` → `UNION` → `COUNT DISTINCT` |
| Spark | `shapely.geometry.shape()` MultiPolygon'u natively destekler |

---

## Tam Örnek

```python
from mapindata.core.config import ConfigManager
from mapindata.data.duckdb_client import DuckDBClient
from mapindata.mobility.footfall_engine import FootfallEngine

cfg = ConfigManager()
duck = DuckDBClient(cfg)
engine = FootfallEngine(con=duck.connect(), s3Path=duck.s3Path("istanbul"))

# 1. Footfall sayısı
count = engine.getCountByPolygon("data/besiktas.json")
print(f"Beşiktaş device sayısı: {count}")

# 2. Radius
count_r = engine.getCountByRadius(41.037, 28.985, 500)
print(f"Taksim 500m device sayısı: {count_r}")

# 3. Device listesi → journey
devices = engine.getDeviceList("data/besiktas.json")
records = engine.fetchDeviceRecords(devices[:100])
print(records.head())

duck.close()
```

---

## Deprecated Alias'lar

Önceki Spark-specific metodlar geriye dönük uyumluluk için korunmuştur ancak kullanımdan kaldırılmıştır.

| Eski Metod | Yeni Karşılık |
|---|---|
| `getCountByPolygonSpark(df, coords)` | `getCountByPolygon(coords, engine="spark")` |
| `getCountByRadiusSpark(df, lat, lon, r)` | `getCountByRadius(lat, lon, r, engine="spark")` |
| `getDeviceListByPolygonSpark(df, coords)` | `getDeviceList(coords, engine="spark")` |
| `getDeviceListByRadiusSpark(df, lat, lon, r)` | `getDeviceListByRadius(lat, lon, r, engine="spark")` |

---

## Katkıda Bulunanlar

| Ad | Rol |
|---|---|
| Kaan Gümele | SDK Geliştirici |
