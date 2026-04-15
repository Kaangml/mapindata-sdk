# mapindata.core.geo_utils
# Created: 2026-04-09 | Author: MapinData
# Subject: Coğrafi hesaplama yardımcıları.
#          Harici bağımlılık gerektirmez; saf Python ile çalışır.
#          Shapely sadece polygon işlemleri için opsiyonel olarak kullanılır.

import math


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------

def haversineDistance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    İki koordinat arasındaki yüzey mesafesini metre cinsinden hesaplar.

    Haversine formülü kullanır; kısa mesafeler için yeterince doğrudur.
    GeoJSON koordinat sırası olan (lon, lat) yerine burada (lat, lon) kullanılır.

    Args:
        lat1: Birinci noktanın enlemi (derece)
        lon1: Birinci noktanın boylamı (derece)
        lat2: İkinci noktanın enlemi (derece)
        lon2: İkinci noktanın boylamı (derece)

    Returns:
        Mesafe (metre)
    """
    EARTH_RADIUS_M = 6_371_000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    deltaPhi = math.radians(lat2 - lat1)
    deltaLambda = math.radians(lon2 - lon1)

    a = (
        math.sin(deltaPhi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(deltaLambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


# ---------------------------------------------------------------------------
# Point-in-Polygon
# ---------------------------------------------------------------------------

def pointInPolygon(lat: float, lon: float, polygonCoords: list) -> bool:
    """
    Bir koordinatın verilen polygon içinde olup olmadığını kontrol eder.

    GeoJSON formatındaki koordinat listesini kabul eder:
    polygonCoords = [ [[lon, lat], [lon, lat], ...] ]  (dış halka + iç halkalar)

    İçeride Shapely kullanılır. Shapely kurulu değilse ImportError fırlatılır.

    Args:
        lat: Noktanın enlemi
        lon: Noktanın boylamı
        polygonCoords: GeoJSON Polygon coordinates dizisi

    Returns:
        True → nokta polygon içinde, False → dışında ya da hatalı girdi
    """
    try:
        from shapely.geometry import Point, shape  # noqa: PLC0415

        point = Point(lon, lat)  # GeoJSON sırası: (lon, lat)
        polygon = shape({"type": "Polygon", "coordinates": polygonCoords})
        return bool(polygon.contains(point))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Bounding Box
# ---------------------------------------------------------------------------

def boundingBox(coords: list[list[float]]) -> dict:
    """
    Koordinat listesinden minimum sınırlayıcı dikdörtgeni (bounding box) hesaplar.

    Args:
        coords: [[lat, lon], [lat, lon], ...] formatında koordinat listesi

    Returns:
        {"minLat": ..., "maxLat": ..., "minLon": ..., "maxLon": ...}
    """
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    return {
        "minLat": min(lats),
        "maxLat": max(lats),
        "minLon": min(lons),
        "maxLon": max(lons),
    }


# ---------------------------------------------------------------------------
# Polygon Alan Hesabı
# ---------------------------------------------------------------------------


def polygonAreaM2(polygonCoords: list) -> float:
    """
    GeoJSON Polygon koordinatlarından yüzey alanını metre² cinsinden hesaplar.

    Shapely'nin derece cinsinden alanını enlem/boylam ölçek faktörleriyle metre²'ye
    dönüştürür. Yüksek enlemlerde küçük sapmalar olabilir; polygon sınıf ayrımı
    (küçük / büyük) için yeterince doğrudur.

    Args:
        polygonCoords: GeoJSON Polygon coordinates dizisi [ [[lon, lat], ...] ]

    Returns:
        Yaklaşık alan (metre²). Shapely kurulu değilse 0.0 döner.
    """
    try:
        from shapely.geometry import shape  # noqa: PLC0415

        polygon = shape({"type": "Polygon", "coordinates": polygonCoords})
        centroid = polygon.centroid
        latRad = math.radians(centroid.y)
        mPerDegLat = 111_320.0
        mPerDegLon = 111_320.0 * math.cos(latRad)
        return abs(polygon.area) * mPerDegLat * mPerDegLon
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# H3 Yardımcıları
# ---------------------------------------------------------------------------
# h3 opsiyonel bağımlılıktır.
# Kurulum: pip install mapindata-sdk[mobility]
# ---------------------------------------------------------------------------


def h3CentroidCell(lat: float, lon: float, res: int = 9) -> int:
    """
    Verilen koordinatın H3 hücresini 64-bit tam sayı olarak döndürür.

    Parquet dosyalarında h3_res9_id INT64 olarak saklandığından bu çıktı
    doğrudan Spark filter ifadelerinde kullanılabilir.

    Args:
        lat: Enlem
        lon: Boylam
        res: H3 çözünürlük (varsayılan 9)

    Returns:
        H3 hücre indeksi (int64).

    Raises:
        ImportError: h3 kurulu değilse
    """
    import h3  # noqa: PLC0415

    return h3.str_to_int(h3.latlng_to_cell(lat, lon, res))


def h3PolygonCells(polygonCoords: list, res: int = 9, bufferK: int = 1) -> list:
    """
    GeoJSON Polygon için H3 hücrelerini INT64 listesi olarak döndürür.

    Önce polyfill uygular; ardından sınır hücrelerine kring(bufferK) tamponu ekler.
    Büyük / orta polygonlar (alan ≥ 100 000 m²) için uygundur.

    Polyfill sonucu boşsa (küçük polygon, < 1 H3 hücresi) boş liste döner —
    bu durumda h3CentroidCell + grid_disk kullanın.

    Args:
        polygonCoords: GeoJSON Polygon coordinates [ [[lon, lat], ...] ]
        res          : H3 çözünürlük (varsayılan 9)
        bufferK      : Kenar tamponu halka sayısı (varsayılan 1)

    Returns:
        H3 hücre INT64 listesi.

    Raises:
        ImportError: h3 kurulu değilse
    """
    import h3  # noqa: PLC0415

    # GeoJSON [lon, lat] → h3 LatLngPoly [lat, lon]
    outerRing = [(c[1], c[0]) for c in polygonCoords[0]]
    holeRings = [[(c[1], c[0]) for c in ring] for ring in polygonCoords[1:]]

    poly = h3.LatLngPoly(outerRing, *holeRings)
    coreCells = set(h3.h3shape_to_cells(poly, res))

    if not coreCells or bufferK == 0:
        return [h3.str_to_int(c) for c in coreCells]

    # Sınır hücrelerine kring tamponu ekle
    buffered = set(coreCells)
    for cell in coreCells:
        buffered.update(h3.grid_disk(cell, bufferK))

    return [h3.str_to_int(c) for c in buffered]


def autoKringK(polygonCoords: list, res: int = 9) -> int:
    """
    Polygon boyutuna göre H3 kring yarıçapını otomatik seçer.

    Karar kriteri: en kısa polygon kenarı H3 res9 hücre çapından (≈ 174 m) büyükse
    k=0 (sadece centroid cell), değilse k=1 (1 halka çevre hücreler).

    Args:
        polygonCoords: GeoJSON Polygon coordinates [ [[lon, lat], ...] ]
        res          : H3 çözünürlük (şu an sadece res=9 desteklenir)

    Returns:
        0 veya 1 (int)
    """
    H3_RES9_DIAMETER_M = 174.0  # yaklaşık H3 res9 hücre çapı (kenar ≈ 87 m)
    ring = polygonCoords[0]
    n = len(ring)
    minEdge = float("inf")
    for i in range(n - 1):
        lon1, lat1 = ring[i]
        lon2, lat2 = ring[i + 1]
        d = haversineDistance(lat1, lon1, lat2, lon2)
        if d < minEdge:
            minEdge = d
    return 0 if minEdge >= H3_RES9_DIAMETER_M else 1


# ---------------------------------------------------------------------------
# Centroid
# ---------------------------------------------------------------------------

def centroid(coords: list[list[float]]) -> dict:
    """
    Koordinat listesinin aritmetik merkezini (centroid) hesaplar.

    Args:
        coords: [[lat, lon], [lat, lon], ...] formatında koordinat listesi

    Returns:
        {"lat": ..., "lon": ...}
    """
    n = len(coords)
    return {
        "lat": sum(c[0] for c in coords) / n,
        "lon": sum(c[1] for c in coords) / n,
    }
