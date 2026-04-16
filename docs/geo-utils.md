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

---

## `polygonAreaM2`

```python
polygonAreaM2(polygonCoords: list) -> float
```

GeoJSON polygon alanını **metre kare** cinsinden hesaplar.

Shoelace (Gauss alan) formülünü kullanır; sonucu derece² → m² katsayısıyla çarpar.  
Küçük polygon / büyük polygon karar eşiğinde (`_SMALL_POLYGON_AREA_M2 = 100 000 m²`) kullanılır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `polygonCoords` | list | GeoJSON `Polygon.coordinates` — `[[[lon, lat], ...]]` |

**Döndürür:** `float` — alan (m²)

**Örnek:**
```python
from mapindata.core.geo_utils import polygonAreaM2

polygon = [[[28.972, 41.018], [28.978, 41.018], [28.978, 41.022], [28.972, 41.022], [28.972, 41.018]]]
area = polygonAreaM2(polygon)
# → ~300 000 m²  (yaklaşık 0.3 km²)
```

---

## `h3CentroidCell`

```python
h3CentroidCell(lat: float, lon: float, res: int = 9) -> int
```

Koordinatın H3 hücresini **INT64** olarak döndürür.

Parquet dosyalarında `h3_res9_id` sütunu INT64 olarak saklandığından bu çıktı  
doğrudan Spark `filter` ifadelerinde kullanılabilir.

| Parametre | Tip | Açıklama |
|---|---|---|
| `lat` | float | Enlem |
| `lon` | float | Boylam |
| `res` | int | H3 çözünürlük (varsayılan 9) |

**Döndürür:** `int` — H3 hücre indeksi (64-bit)

**Örnek:**
```python
from mapindata.core.geo_utils import h3CentroidCell

cell = h3CentroidCell(41.0370, 28.9850)
# → 613146799897739263  (Taksim Meydanı H3 res9 hücresi)
```

---

## `h3PolygonCells`

```python
h3PolygonCells(polygonCoords: list, res: int = 9, bufferK: int = 1) -> list[int]
```

GeoJSON polygon için H3 hücrelerini **INT64 listesi** olarak döndürür.

`h3shape_to_cells` polyfill uygular; ardından sınır hücrelerine `grid_disk(bufferK)` tamponu ekler.  
Büyük / orta polygonlar (alan ≥ 100 000 m²) için uygundur.  
Polyfill boş dönerse (< 1 H3 hücresi) boş liste döner — bu durumda `h3CentroidCell` + `autoKringK` kullanın.

| Parametre | Tip | Açıklama |
|---|---|---|
| `polygonCoords` | list | GeoJSON `Polygon.coordinates` — `[[[lon, lat], ...]]` |
| `res` | int | H3 çözünürlük (varsayılan 9) |
| `bufferK` | int | Kenar tamponu halka sayısı (varsayılan 1) |

**Döndürür:** `list[int]` — H3 hücre INT64 listesi

**Örnek:**
```python
from mapindata.core.geo_utils import h3PolygonCells

polygon = [[[28.820, 41.050], [28.880, 41.050], [28.880, 41.080], [28.820, 41.080], [28.820, 41.050]]]
cells = h3PolygonCells(polygon)
# → [613146..., 613147..., ...]  (Bağcılar bölgesi H3 hücreleri)
```

---

## `autoKringK`

```python
autoKringK(polygonCoords: list, res: int = 9) -> int
```

Polygon kenar uzunluğuna göre H3 kring yarıçapını (`0` veya `1`) **otomatik** seçer.

Karar kriteri: en kısa polygon kenarı H3 res9 çapından (≈ 174 m) büyükse `k=0` (sadece centroid),  
küçükse `k=1` (centroid + 1 halka çevre hücreler).  
`FootfallEngine._filterByPolygonSpark` tarafından küçük polygon yolunda kullanılır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `polygonCoords` | list | GeoJSON `Polygon.coordinates` — `[[[lon, lat], ...]]` |
| `res` | int | Şu an yalnızca res=9 desteklenir |

**Döndürür:** `int` — `0` veya `1`

**H3 res9 referans değerleri:**

| Değer | Ölçüm |
|---|---|
| Hücre kenarı | ≈ 87 m |
| Hücre çapı (köşe–köşe) | ≈ 174 m |
| Kapsama alanı | ≈ 0.105 km² |

**Örnek:**
```python
from mapindata.core.geo_utils import autoKringK

small = [[[28.972, 41.018], [28.974, 41.018], [28.974, 41.020], [28.972, 41.020], [28.972, 41.018]]]
print(autoKringK(small))   # → 1  (kenar < 174 m)

large = [[[28.820, 41.050], [28.880, 41.050], [28.880, 41.080], [28.820, 41.080], [28.820, 41.050]]]
print(autoKringK(large))   # → 0  (kenar >> 174 m)
```

