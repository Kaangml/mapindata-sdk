# Geo Utils — Fonksiyon Referansı

`mapindata.core.geo_utils` modülü, coğrafi hesaplama için saf Python fonksiyonları içerir.  
Harici bağımlılık gerektirmez; `pointInPolygon` için `shapely` opsiyonel olarak kullanılır.

---

## `haversineDistance`

```python
haversineDistance(lat1: float, lon1: float, lat2: float, lon2: float) -> float
```

İki koordinat arasındaki yüzey mesafesini **metre** cinsinden hesaplar.  
Haversine formülünü kullanır — kısa ve orta mesafelerde yüksek doğruluk sağlar.

**Parametre sırası:** `(lat, lon)` — GeoJSON'daki `(lon, lat)` sırasının tersidir.

| Parametre | Tip | Açıklama |
|---|---|---|
| `lat1` | float | Birinci noktanın enlemi (derece) |
| `lon1` | float | Birinci noktanın boylamı (derece) |
| `lat2` | float | İkinci noktanın enlemi (derece) |
| `lon2` | float | İkinci noktanın boylamı (derece) |

**Döndürür:** `float` — iki nokta arası mesafe (metre)

**Örnek:**
```python
from mapindata.core import haversineDistance

dist = haversineDistance(41.01, 28.97, 39.92, 32.85)
# → ~350 000 metre (İstanbul–Ankara)
```

**Formül:**

$$
a = \sin^2\!\left(\frac{\Delta\phi}{2}\right) + \cos\phi_1 \cdot \cos\phi_2 \cdot \sin^2\!\left(\frac{\Delta\lambda}{2}\right)
$$
$$
d = 2R \cdot \arctan2\!\left(\sqrt{a},\,\sqrt{1-a}\right) \quad R = 6\,371\,000 \text{ m}
$$

---

## `pointInPolygon`

```python
pointInPolygon(lat: float, lon: float, polygonCoords: list) -> bool
```

Bir koordinatın GeoJSON polygon içinde olup olmadığını kontrol eder.  
İçeride `shapely.geometry.shape` kullanılır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `lat` | float | Noktanın enlemi |
| `lon` | float | Noktanın boylamı |
| `polygonCoords` | list | GeoJSON `Polygon.coordinates` dizisi — `[[[lon, lat], ...]]` |

**Döndürür:** `bool` — `True` nokta içinde, `False` dışında ya da hatalı girdi

> **Not:** GeoJSON koordinat sırası `[lon, lat]`'tır (boylam önce). Bu fonksiyon bu dönüşümü dahili olarak yapar.

**Örnek:**
```python
from mapindata.core import pointInPolygon

polygon = [[[28.97, 41.03], [28.98, 41.03], [28.98, 41.04], [28.97, 41.04], [28.97, 41.03]]]
result = pointInPolygon(41.035, 28.975, polygon)
# → True
```

---

## `boundingBox`

```python
boundingBox(coords: list[list[float]]) -> dict
```

Koordinat listesinden minimum sınırlayıcı dikdörtgeni hesaplar.

**Girdi formatı:** `[[lat, lon], [lat, lon], ...]`

**Döndürür:**
```python
{"minLat": float, "maxLat": float, "minLon": float, "maxLon": float}
```

**Kullanım amacı:** Büyük veri kümelerini bounding box ile ön filtrelemek — örn. S3'ten okunurken gereksiz kayıtları erken elemek.

---

## `centroid`

```python
centroid(coords: list[list[float]]) -> dict
```

Koordinat listesinin aritmetik merkezini hesaplar.

**Girdi formatı:** `[[lat, lon], [lat, lon], ...]`

**Döndürür:** `{"lat": float, "lon": float}`

---

## Neden Haversine? Neden Polygon?

| Durum | Önerilen Yöntem |
|---|---|
| Mağaza/POI ziyareti (giriş noktası) | Haversine + küçük yarıçap (15–50 m) |
| AVM, park, büyük yapı | Polygon (şekil düzensiz, alan büyük) |
| Semt / ilçe analizi | Polygon (idari sınır verisi) |
| Hızlı ön filtresi | Bounding Box → ardından Polygon |

Daha fazla bilgi için bkz. [kodlama-standartlari.md](kodlama-standartlari.md)

---

## S3Client ile Büyük Veri Akışı

S3'ten okunan mobil veri `FootfallEngine`'in Spark metodlarıyla birleştirilerek
tam analiz yapılır. Tipik iş akışı:

```
S3Client.loadMobilityData()          → Spark DataFrame
  └─▶ boundingBox()                  → ön filtre koordinatları
        └─▶ FootfallEngine.*Spark()  → polygon / radius filtresi
              └─▶ unique device sayısı veya DataFrame
```

```python
from mapindata.core.config import ConfigManager
from mapindata.core.geo_utils import boundingBox
from mapindata.data.s3_client import S3Client
from mapindata.mobility.footfall_engine import FootfallEngine

cfg = ConfigManager()
client = S3Client(cfg)
spark = client.createSession("FootfallJob")

# 1. Veriyi yükle
df = client.loadMobilityData(province="Istanbul")

# 2. Polygon listenden bounding box hesapla → ön filtre
coords = [[41.03, 28.97], [41.07, 28.97], [41.07, 29.01], [41.03, 29.01]]
bb = boundingBox(coords)
df = df.filter(
    (df.latitude  >= bb["minLat"]) & (df.latitude  <= bb["maxLat"]) &
    (df.longitude >= bb["minLon"]) & (df.longitude <= bb["maxLon"])
).cache()

# 3. Footfall hesapla
engine = FootfallEngine()
polygon = [[[28.97, 41.03], [29.01, 41.03], [29.01, 41.07], [28.97, 41.07], [28.97, 41.03]]]
count = engine.getCountByPolygonSpark(df, polygon)
print(f"Footfall: {count:,} unique device")

client.stop()
```

Spark konfigürasyonu için bkz. [S3 ve EC2 Ortamı](../README.md#s3-ve-ec2-ortamı)

