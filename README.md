# MapinData SDK

Mobil sinyal verisi üzerinden ayak izi analizi, persona tespiti, lokasyon skorlaması ve veri toplama için kurumsal Python kütüphanesi.

---

## İçindekiler

- [Kurulum](#kurulum)
- [Gizli Bilgiler ve Konfigürasyon](#gizli-bilgiler-ve-konfigürasyon)
- [Modüller](#modüller)
  - [core — Temel Katman](#core--temel-katman)
  - [data — Veri Katmanı](#data--veri-katmanı)
  - [mobility — Mobil Veri Analitiği](#mobility--mobil-veri-analitiği)
  - [analytics — İş Mantığı](#analytics--iş-mantığı)
  - [scraping — Veri Toplama](#scraping--veri-toplama)
  - [viz — Görselleştirme](#viz--görselleştirme)
- [Kod Standartları](#kod-standartları)
- [Test](#test)
- [Geliştirme](#geliştirme)

---

## Kurulum

### Temel Kurulum (zorunlu bağımlılıklar)

```bash
pip install mapindata-sdk
```

Temel kurulumda şunlar dahildir: `core`, `analytics`, `viz`

### Extra Bağımlılıklar

```bash
# S3, PostgreSQL, Spark
pip install mapindata-sdk[data]

# Ayak izi, Persona, Journey (data dahil)
pip install mapindata-sdk[mobility]

# Playwright scraping, Apify, Rocket API
pip install mapindata-sdk[scraping]
# Playwright için chromium kurulumu (ilk seferinde):
playwright install chromium

# Türkçe NLP / Duygu Analizi (BERT)
pip install mapindata-sdk[nlp]

# Hepsi
pip install mapindata-sdk[all]
```

### Geliştirme Ortamı

```bash
git clone <repo-url>
cd mapindata-sdk
pip install -e ".[all,dev]"
```

---

## Gizli Bilgiler ve Konfigürasyon

> **Güvenlik Kuralı**: Hiçbir şifre, API anahtarı veya erişim token'ı kaynak koda yazılmaz.

### Gizli Bilgilerin Akışı

```
Kaynak                     Ortam          Erişim Yolu
─────────────────────────  ─────────────  ────────────────────────────────
.env dosyası               Geliştirme     python-dotenv → ConfigManager
Sistem ortam değişkeni     Üretim / CI    os.getenv()   → ConfigManager
AWS Secrets Manager        Prod (opsiyonel) ConfigManager override
```

### Kurulum Adımları

**1. Şablon dosyasını kopyala:**

```bash
cp .env.example .env
```

**2. `.env` dosyasını doldur:**

```ini
# AWS / S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your-secret
MAPIN_S3_BUCKET=mapindata-prod

# PostgreSQL
MAPIN_DB_HOST=localhost
MAPIN_DB_NAME=mapindata
MAPIN_DB_USER=mapindata_user
MAPIN_DB_PASSWORD=your-password
```

**3. `.env` dosyası `.gitignore`'a alınmıştır** — asla commit edilmez.

### Hangi Bilgi Nerede Bulunur?

| Kategori | Ortam Değişkeni | ConfigManager Property |
|---|---|---|
| AWS erişim anahtarı | `AWS_ACCESS_KEY_ID` | `config.awsAccessKeyId` |
| AWS gizli anahtar | `AWS_SECRET_ACCESS_KEY` | `config.awsSecretAccessKey` |
| S3 bucket adı | `MAPIN_S3_BUCKET` | `config.s3Bucket` |
| DB host | `MAPIN_DB_HOST` | `config.dbHost` |
| DB port | `MAPIN_DB_PORT` | `config.dbPort` |
| DB adı | `MAPIN_DB_NAME` | `config.dbName` |
| DB kullanıcı | `MAPIN_DB_USER` | `config.dbUser` |
| DB şifre | `MAPIN_DB_PASSWORD` | `config.dbPassword` |
| Tüm DB bağlantısı | _(birleşim)_ | `config.dbConnectionString` |
| Scraper EC2 URL | `MAPIN_SCRAPER_EC2_URL` | `config.scraperEc2Url` |
| Apify token | `APIFY_API_TOKEN` | `config.apifyToken` |
| Rocket API key | `ROCKET_API_KEY` | `config.rocketApiKey` |

### Üretim Ortamı

Üretimde `.env` dosyası **kullanılmaz**. Ortam değişkenleri sistem seviyesinde set edilir:

```bash
# systemd service
export MAPIN_DB_HOST=prod-db.rds.amazonaws.com
export MAPIN_DB_PASSWORD=$(aws secretsmanager get-secret-value ...)
```

---

## Modüller

### `core` — Temel Katman

Her kurulumda mevcut. Extra bağımlılık gerektirmez.

#### `ConfigManager`

```python
from mapindata.core import ConfigManager

config = ConfigManager()

# Değerlere erişim
print(config.s3Bucket)           # "mapindata-prod"
print(config.dbConnectionString) # "postgresql+psycopg2://user:pass@host:5432/db"
print(config.isProduction)       # False (geliştirme ortamında)
```

#### `GeoUtils`

```python
from mapindata.core import haversineDistance, pointInPolygon

# İki nokta arası mesafe (metre)
dist = haversineDistance(41.0082, 28.9784, 39.9255, 32.8660)
print(f"İstanbul-Ankara: {dist/1000:.0f} km")  # ~350 km

# Nokta poligon içinde mi?
polygon = [(28.97, 41.01), (28.98, 41.01), (28.98, 41.02), (28.97, 41.02)]
inside = pointInPolygon((28.975, 41.015), polygon)
print(inside)  # True
```

#### `constants`

```python
from mapindata.core.constants import TURKEY_TZ, MAPIN_COLORS, LOCATION_CATEGORIES
```

---

### `data` — Veri Katmanı

Gereksinim: `pip install mapindata-sdk[data]`

#### `S3Client`

```python
from mapindata.data import S3Client

client = S3Client()

# Parquet okuma
df = client.readParquet("processed/mobility/2024-01/footfall.parquet")

# Filtrelenmiş okuma
df = client.readParquet(
    "processed/mobility/2024-01/footfall.parquet",
    columns=["device_id", "lat", "lon"],
    filters=[("city", "=", "Istanbul")],
)

# Parquet yazma
client.writeParquet(df, "processed/results/scores.parquet")

# Partition ile yazma
client.writeParquet(df, "processed/results/", partitionCols=["year", "month"])
```

#### `SparkManager`

```python
from mapindata.data import SparkManager

# Sistem kaynaklarına göre otomatik konfigürasyon
spark = SparkManager(appName="FootfallAnalysis").getSparkSession()
df = spark.read.parquet("s3a://mapindata-prod/raw/mobility/")

# Üretim ortamında .env ile override:
# SPARK_DRIVER_MEMORY=64g
# SPARK_EXECUTOR_CORES=8
```

#### `DBConnector`

```python
from mapindata.data import DBConnector

db = DBConnector()

# Sorgu çalıştırma (parametreli — SQL injection güvenli)
df = db.readQuery(
    "SELECT * FROM locations WHERE city = :city AND category = :cat",
    params={"city": "Istanbul", "cat": "bar"},
)

# Tablo okuma
df = db.readTable("public.poi_master", columns=["id", "name", "lat", "lon"])

# DataFrame yazma
db.writeDataFrame(results_df, "staging_footfall", ifExists="replace")
```

---

### `mobility` — Mobil Veri Analitiği

Gereksinim: `pip install mapindata-sdk[mobility]`

#### `FootfallEngine`

```python
from mapindata.mobility import FootfallEngine

engine = FootfallEngine()

# Poligon bazlı sayım
polygons = [
    {"id": "POI_001", "coords": [(28.97, 41.01), (28.98, 41.01), ...]},
    {"id": "POI_002", "coords": [(29.01, 41.05), ...]},
]
result = engine.calculateByPolygon(gps_df, polygons)
# polygon_id  total_pings  unique_visitors
# POI_001     1250         430
# POI_002     870          295

# Radius bazlı sayım
result = engine.calculateByRadius(
    points=gps_df,
    center=(41.015, 28.975),
    radius=500,  # metre
)
# {"total_pings": 340, "unique_visitors": 120}
```

#### `PersonaManager`

```python
from mapindata.mobility import PersonaManager

manager = PersonaManager(nightStart=23, dayStart=8)
personas = manager.identifyHomeWork(mobility_df)
# device_id   home_lat  home_lon  work_lat  work_lon
# abc123      41.023    29.001    41.045    28.987
```

#### `JourneyAnalyzer`

```python
from mapindata.mobility import JourneyAnalyzer

analyzer = JourneyAnalyzer()

# Sadakat: Bar A'ya gidenler Bar B'ye de gidiyor mu?
loyalty = analyzer.calculateLoyalty(visits_df, poiA="BAR_001", poiB="BAR_002")
# {"loyalty_a_to_b": 0.32, "loyalty_b_to_a": 0.28, "shared_visitors": 145}

# Örtüşme: iki rakip grup arasında ortak kitle
overlap = analyzer.calculateOverlap(visits_df, groupA=["BRAND_A_*"], groupB=["BRAND_B_*"])
# {"overlap_score": 0.41, "intersection": 2300, "union": 5600}
```

---

### `analytics` — İş Mantığı

Temel kurulumda dahil. Extra gerektirmez.

#### `LitreEstimator`

```python
from mapindata.analytics import LitreEstimator

estimator = LitreEstimator(capacityWeight=0.4, densityWeight=0.6)

# Tek lokasyon
monthly_litres = estimator.estimateHybrid(
    capacity=80,        # 80 kişilik bar
    category="bar",
    densityScore=72.5,  # FootfallEngine'den gelen skor
)
print(f"Aylık tahmini: {monthly_litres:.0f} litre")

# Toplu tahmin
locations = [
    {"id": "L001", "capacity": 60, "category": "restoran", "density_score": 65.0},
    {"id": "L002", "capacity": 120, "category": "bar", "density_score": 88.0},
]
results = estimator.estimateBatch(locations)
```

#### `Scorer`

```python
from mapindata.analytics import Scorer

scorer = Scorer()

# Tek skor dönüştürme
profile = scorer.calculateProfileScore(rawScore=75.0)   # "B"
population = scorer.calculatePopulationScore(62.0)      # 4

# Bileşen bazlı detaylı skor
detail = scorer.calculateProfileScoreDetailed(
    demographicScore=78.0,
    incomeScore=82.0,
    affinityScore=65.0,
)
# {"raw_score": 76.35, "band": "B", "components": {...}}

# DataFrame'e bant sütunu ekleme
scored_df = scorer.scoreDataFrame(df)
# profile_band ve population_band sütunları eklenir
```

#### `NlpEngine`

```python
from mapindata.analytics import NlpEngine

# Hızlı kural modu (ek paket gerekmez)
engine = NlpEngine(useTransformer=False)

# Türkçe BERT modu (pip install mapindata-sdk[nlp])
engine = NlpEngine(useTransformer=True)

# Tek yorum analizi
result = engine.analyzeSentiment("Harika bir mekan, kesinlikle tavsiye ederim!")
# {"label": "positive", "score": 0.92, "clean_text": "harika bir mekan..."}

# Toplu analiz
results = engine.analyzeReviews(["Çok güzel!", "Berbat servis.", "İdare eder."])

# Sadece metin temizleme
clean = engine.cleanText("Müthiş 🍕 mekan!! https://maps.google.com/...")
```

---

### `scraping` — Veri Toplama

Gereksinim: `pip install mapindata-sdk[scraping]`

#### `ScraperClient` (Async)

```python
import asyncio
from mapindata.scraping import ScraperClient

async def main():
    async with ScraperClient() as client:
        # Google Places arama
        places = await client.scrapeGooglePlaces(
            query="bar istanbul beyoğlu",
            maxResults=20,
        )

        # Belirli bir yer için yorumlar
        reviews = await client.scrapeGoogleReviews(
            placeId="ChIJxxxxxxxx",
            maxReviews=100,
            sortBy="newest",
        )

asyncio.run(main())

# Senkron kullanım (Jupyter için)
client = ScraperClient()
places = client.scrapeGooglePlacesSync("kafe taksim")
```

#### `ApifyClient`

```python
from mapindata.scraping import ApifyClient

apify = ApifyClient()
results = apify.runActor(
    actorId="apify/google-maps-scraper",
    runInput={"searchStringsArray": ["bar istanbul"], "maxCrawledPlaces": 50},
)
```

#### `RocketApiClient`

```python
from mapindata.scraping import RocketApiClient

rocket = RocketApiClient()
places = rocket.searchPlaces(query="restoran kadıköy", maxResults=30)
details = rocket.getPlaceDetails(placeId="rocket_place_id")
```

---

### `viz` — Görselleştirme

Temel kurulumda dahil.

```python
from mapindata.viz import applyMapinTheme, mapinFigure, mapinBarChart, getMapinColorPalette
import matplotlib.pyplot as plt

# Tema uygula (tüm grafikler otomatik olarak MapinData görünümüne geçer)
applyMapinTheme()

# Önceden ayarlanmış figür
fig, ax = mapinFigure("Aylık Ayak İzi", "Ay", "Ziyaretçi Sayısı")
ax.plot(months, visitors)
plt.show()

# Hazır bar grafiği
fig, ax = mapinBarChart(
    labels=["Ocak", "Şubat", "Mart"],
    values=[1200, 1450, 1380],
    title="Çeyrek Ziyaretçi",
    colorIndex=1,  # MAPIN_COLORS[1] = mavi
)

# Renk paleti
colors = getMapinColorPalette(n=5)  # ["#1A3C5E", "#2E86AB", ...]
```

---

## Kod Standartları

SDK, [MAPINDATA_KODLAMA_STANDARDLARI.docx](docs/MAPINDATA_KODLAMA_STANDARDLARI.docx) belgesindeki kurallara uyar:

| Öğe | Kural | Örnek |
|---|---|---|
| Sınıf | PascalCase | `FootfallEngine`, `ConfigManager` |
| Fonksiyon | camelCase | `haversineDistance`, `calculateByPolygon` |
| Değişken | camelCase | `densityScore`, `totalPings` |
| Sabit | UPPER_SNAKE_CASE | `TURKEY_TZ`, `MAPIN_COLORS` |
| Private | `_` prefix | `_buildResourceProfile` |
| Dosya | snake_case | `footfall_engine.py`, `db_connector.py` |

### Ruff ile Linting

```bash
# Lint kontrolü
ruff check src/

# Otomatik düzeltme
ruff check --fix src/

# Kod formatlama
ruff format src/
```

Ruff konfigürasyonu `pyproject.toml` içindedir. `N802/N803/N806` kuralları camelCase standardıyla çeliştiği için devre dışıdır.

---

## Test

```bash
# Tüm testler
pytest

# Kapsam raporu ile
pytest --cov=src/mapindata --cov-report=html

# Sadece core testleri
pytest tests/core/

# Sadece analytics testleri
pytest tests/analytics/ -v
```

### Test Yapısı

```
tests/
├── core/
│   ├── test_geo_utils.py    # haversineDistance, pointInPolygon
│   └── test_config.py       # ConfigManager defaults ve overrides
├── analytics/
│   ├── test_litre_estimator.py
│   └── test_scorer.py
└── mobility/
    └── test_footfall_engine.py
```

---

## Geliştirme

### Mimari Kararlar (ADR)

Tasarım kararları `docs/adr/` klasöründe kayıt altına alınmıştır:

| ADR | Başlık |
|-----|--------|
| [ADR-001](docs/adr/ADR-001-polygon-vs-haversine.md) | Poligon Sayımı vs. Haversine — hangi durumda hangisi? |
| [ADR-002](docs/adr/ADR-002-dynamic-spark-config.md) | Dinamik Spark Konfigürasyonu — 48 Core Bağımlılığını Kırma |

### Yeni Modül Ekleme

1. `src/mapindata/<modül>/` klasörünü oluştur
2. `__init__.py` içinde public API'yi tanımla
3. `tests/<modül>/` klasörünü ve testleri oluştur
4. `pyproject.toml` içine gerekirse yeni extra ekle
5. Bu README'yi güncelle

### GitHub'a Yükleme

```bash
# İlk commit
git init
git add .
git commit -m "feat: initial SDK structure"
git remote add origin https://github.com/MapinData/mapindata-sdk.git
git push -u origin main
```

---

## Lisans

Proprietary — MapinData © 2024
