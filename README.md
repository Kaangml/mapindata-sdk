# MapinData SDK

Mobil sinyal verisi üzerinden ayak izi analizi ve konum bazlı analitik için kurumsal Python kütüphanesi.

---

## İçindekiler

- [Kurulum](#kurulum)
- [S3 ve EC2 Ortamı](#s3-ve-ec2-ortamı)
- [Konfigürasyon](#konfigürasyon)
- [Modüller](#modüller)
- [Kod Standartları](#kod-standartları)
- [Test](#test)
- [Dokümantasyon](#dokümantasyon)

---

## Kurulum

### GitHub'dan Kurulum (Önerilen)

```bash
# Temel kurulum (core + shapely)
pip install "git+https://github.com/Kaangml/mapindata-sdk.git"

# S3 okuma + Spark + Footfall Analizi
pip install "git+https://github.com/Kaangml/mapindata-sdk.git#egg=mapindata-sdk[mobility]"

# Tüm bağımlılıklar
pip install "git+https://github.com/Kaangml/mapindata-sdk.git#egg=mapindata-sdk[all]"
```

### Geliştirme Ortamı

```bash
git clone https://github.com/Kaangml/mapindata-sdk.git
cd mapindata-sdk
pip install -e ".[all,dev]"
```

### Extra Bağımlılık Grupları

| Extra | İçerik | Kurulum |
|---|---|---|
| `data` | boto3, pyspark, psycopg2, sqlalchemy, pyarrow | `mapindata-sdk[data]` |
| `mobility` | data dahil + geopandas, h3 | `mapindata-sdk[mobility]` |
| `scraping` | playwright, apify-client, aiohttp, httpx | `mapindata-sdk[scraping]` |
| `nlp` | transformers, torch, langdetect | `mapindata-sdk[nlp]` |
| `all` | tümü | `mapindata-sdk[all]` |
| `dev` | pytest, ruff, mypy | `mapindata-sdk[dev]` |

---

## S3 ve EC2 Ortamı

### AWS AMI Seçimi: Amazon Linux 2023 (Önerilen)

Tüm üretim işleri **Amazon Linux 2023** AMI üzerinde çalışır.

| | Amazon Linux 2023 | Ubuntu |
|---|---|---|
| AWS SSM / CloudWatch entegrasyonu | Yerleşik | Manuel |
| IAM Role otomatik kimlik doğrulama | `DefaultAWSCredentialsProviderChain` ile tam uyumlu | Ek yapılandırma gerekir |
| Java / PySpark paketi | `dnf install java-17-amazon-corretto` tek komut | Farklı kaynak gerekir |
| AWS CLI v2 önceden kurulu | Evet | Hayır |

### IAM Role ile S3 Erişimi (.env'de AWS key gerekmez)

EC2 instance'a IAM Role atandığında `DefaultAWSCredentialsProviderChain`
otomatik olarak role credentials'ını alır. `.env`'e `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` **yazılmaz**.

**Gerekli IAM Policy (instance role'e ekle):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::mapindata-raw-data",
        "arn:aws:s3:::mapindata-raw-data/*"
      ]
    }
  ]
}
```

### S3A JAR Dosyaları (EC2'de tek seferlik kurulum)

```bash
mkdir -p /home/ec2-user/jars && cd /home/ec2-user/jars

# Hadoop AWS connector
curl -O https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar

# AWS SDK bundle (hadoop-aws'ın bağımlılığı)
curl -O https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.528/aws-java-sdk-bundle-1.12.528.jar
```

`.env.example` içinde:
```ini
SPARK_JARS=/home/ec2-user/jars/hadoop-aws-3.3.4.jar,/home/ec2-user/jars/aws-java-sdk-bundle-1.12.528.jar
```

> **Not:** Amazon Linux 2023 AMI seçildiğinde bu JAR yolları sabittir.
> Farklı bir AMI veya dizin kullanıyorsan `SPARK_JARS` env değişkenini override et.

---

## Konfigürasyon

> **Güvenlik Kuralı:** Hiçbir şifre, API anahtarı veya erişim token'ı kaynak koda yazılmaz.

```bash
cp .env.example .env
# .env dosyasını doldurun — bu dosya .gitignore'da, asla commit edilmez
```

### Ortam Değişkenleri → ConfigManager

| Kategori | Ortam Değişkeni | ConfigManager Property | Varsayılan |
|---|---|---|---|
| S3 bucket | `MAPIN_S3_BUCKET` | `cfg.s3Bucket` | `mapindata-prod` |
| S3 raw prefix | `MAPIN_S3_RAW_PREFIX` | `cfg.s3RawPrefix` | `raw/` |
| DB host | `MAPIN_DB_HOST` | `cfg.dbHost` | `localhost` |
| DB port | `MAPIN_DB_PORT` | `cfg.dbPort` | `5432` |
| DB adı | `MAPIN_DB_NAME` | `cfg.dbName` | `mapindata` |
| DB şifre | `MAPIN_DB_PASSWORD` | `cfg.dbPassword` | **zorunlu** |
| Spark driver bellek | `SPARK_DRIVER_MEMORY` | `cfg.sparkDriverMemory` | sistem RAM × 0.75 |
| Spark core sayısı | `SPARK_EXECUTOR_CORES` | `cfg.sparkCores` | `cpu_count()` |
| S3A JAR dosyaları | `SPARK_JARS` | `cfg.sparkJars` | _(boş)_ |
| Haversine yarıçapı | `MAPIN_RADIUS_METERS` | `cfg.radiusMeters` | `15` |
| Ortam | `MAPIN_ENV` | `cfg.environment` | `development` |

---

## Modüller

### `core` — Temel Katman

> Tüm kurulumlarda mevcut. Ek bağımlılık gerektirmez.

#### `ConfigManager`

```python
from mapindata.core import ConfigManager

cfg = ConfigManager()

print(cfg.sparkMaster)        # "local[8]"  (8 çekirdekli sistemde)
print(cfg.sparkDriverMemory)  # "12g"       (16 GB RAM'li sistemde otomatik)
print(cfg.s3Bucket)           # "mapindata-prod"
print(cfg.radiusMeters)       # 15

# Mobil veri Spark konfigürasyonu (S3A + Kryo + AQE dahil)
for key, val in cfg.mobilitySparkConfig("FootfallJob").items():
    print(key, "=", val)
```

#### `geo_utils`

```python
from mapindata.core import haversineDistance, pointInPolygon, boundingBox, centroid

# İki nokta arası mesafe (metre)
dist = haversineDistance(41.01, 28.97, 39.92, 32.85)
print(f"İstanbul–Ankara: {dist/1000:.0f} km")  # ~350 km

# Polygon içinde mi? (GeoJSON: [lon, lat] sırası)
polygon = [[[28.97, 41.01], [28.98, 41.01], [28.98, 41.02], [28.97, 41.02], [28.97, 41.01]]]
print(pointInPolygon(41.015, 28.975, polygon))  # True

# Bounding box (ön filtre için)
coords = [[41.01, 28.97], [41.05, 28.99], [41.03, 29.01]]
bb = boundingBox(coords)
# {"minLat": 41.01, "maxLat": 41.05, "minLon": 28.97, "maxLon": 29.01}
```

Fonksiyon detayları: [docs/geo-utils.md](docs/geo-utils.md)

---

### `data` — Veri Katmanı

> Gereksinim: `pip install mapindata-sdk[mobility]`

#### `S3Client`

```python
from mapindata.core.config import ConfigManager
from mapindata.data import S3Client

cfg = ConfigManager()
client = S3Client(cfg)

# Spark oturumu oluştur (mobilitySparkConfig otomatik uygulanır)
spark = client.createSession("FootfallJob")

# İstanbul mobil verisini yükle (echo_data_partitioned şeması)
df = client.loadMobilityData(province="Istanbul")
#  → device_aid, latitude, longitude, timestamp, horizontal_accuracy sütunları

# Tüm iller (dikkat: çok büyük veri!)
df_all = client.loadMobilityData()

# Özel S3 yolu
df_custom = client.loadData("s3a://mapindata-raw-data/custom/path/", format="parquet")

# Oturumu kapat
client.stop()
```

---

### `mobility` — Mobil Veri Analitiği

> Gereksinim: `pip install mapindata-sdk[mobility]`

#### `FootfallEngine`

İki çalışma modu vardır:

| Mod | Girdi | Ne zaman kullanılır |
|---|---|---|
| **Pure Python** | `list[dict]` | Küçük/test verisi, Spark gereksiz |
| **Spark** | `pyspark.sql.DataFrame` | S3'ten okunan gerçek büyük veri |

```python
from mapindata.mobility import FootfallEngine

engine = FootfallEngine()  # latCol, lonCol, deviceCol özelleştirilebilir

# ── Pure Python Modu ──────────────────────────────────────────────────
records = [
    {"device_aid": "d001", "latitude": 41.033, "longitude": 28.978},
    {"device_aid": "d002", "latitude": 41.034, "longitude": 28.979},
]

polygon = [[[28.97, 41.03], [28.99, 41.03], [28.99, 41.04], [28.97, 41.04], [28.97, 41.03]]]

count   = engine.getCountByPolygon(records, polygon)        # int
devices = engine.getDeviceListByPolygon(records, polygon)   # list[str]

count   = engine.getCountByRadius(records, 41.033, 28.978, 50)       # int, 50m yarıçap
devices = engine.getDeviceListByRadius(records, 41.033, 28.978, 50)  # list[str]

# ── Spark Modu (S3 verisi için) ───────────────────────────────────────
from mapindata.data import S3Client

client = S3Client(cfg)
spark  = client.createSession("FootfallJob")
df     = client.loadMobilityData(province="Istanbul")

count      = engine.getCountByPolygonSpark(df, polygon)           # int
devices_df = engine.getDeviceListByPolygonSpark(df, polygon)      # DataFrame
devices_df.write.parquet("/output/devices/")

count      = engine.getCountByRadiusSpark(df, 41.033, 28.978, 50)
devices_df = engine.getDeviceListByRadiusSpark(df, 41.033, 28.978, 50)

client.stop()
```

> **GeoJSON Koordinat Sırası:** `polygonCoords` her zaman `[lon, lat]` sırasındadır.

---

## Kod Standartları

Tüm kurallar: [docs/kodlama-standartlari.md](docs/kodlama-standartlari.md)

| Öğe | Kural | Örnek |
|---|---|---|
| Sınıf | PascalCase | `FootfallEngine`, `ConfigManager`, `S3Client` |
| Fonksiyon / Metod | camelCase | `haversineDistance`, `getCountByPolygon` |
| Değişken | camelCase | `centerLat`, `radiusMeters` |
| Sabit | UPPER_SNAKE_CASE | `MOBILITY_DEFAULT_COLUMNS` |
| Private | `_` prefix | `_filterByPolygon`, `_makePolygonUdf` |

### Ruff

```bash
ruff check src/          # lint kontrol
ruff check --fix src/    # otomatik düzeltme
ruff format src/         # formatlama
```

---

## Test

```bash
# Tüm testler
pytest

# Kapsam raporu
pytest --cov=src/mapindata --cov-report=term-missing

# Modül bazlı
pytest tests/core/ -v
pytest tests/mobility/ -v
pytest tests/data/ -v
```

### Test Durumu

| Modül | Durum |
|---|---|
| `core.config` | ✅ Testler geçiyor |
| `core.geo_utils` | ✅ Testler geçiyor |
| `mobility.footfall_engine` | ✅ Pure Python testler geçiyor |
| `data.s3_client` | ✅ Config testleri geçiyor; S3 testleri entegrasyon ortamı gerektirir |
| `analytics`, `scraping`, `viz` | ⏳ Henüz implement edilmedi |

---

## Dokümantasyon

| Dosya | İçerik |
|---|---|
| [docs/geo-utils.md](docs/geo-utils.md) | `haversineDistance`, `pointInPolygon`, `boundingBox`, `centroid` fonksiyon referansı |
| [docs/development-history.md](docs/development-history.md) | Her eklenen sınıf/metod kronolojik tablo |
| [docs/future-features.md](docs/future-features.md) | Planlanmış özellikler (FF-001, FF-003...) |
| [docs/kodlama-standartlari.md](docs/kodlama-standartlari.md) | MapinData kodlama kuralları |

---

## Lisans

Proprietary — MapinData © 2026
