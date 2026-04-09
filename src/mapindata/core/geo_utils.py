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
