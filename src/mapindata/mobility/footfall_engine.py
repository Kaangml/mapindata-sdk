# mapindata.mobility.footfall_engine
# Created: 2026-04-09 | Author: MapinData
# Subject: Mobil cihaz verisi üzerinden ayak izi metriklerini hesaplar.
#          Polygon veya Haversine yarıçapı bazlı filtreleme destekler.
#          Girdi olarak dict listesi alır; Spark entegrasyonu FUTURE FEATURE.

from mapindata.core.geo_utils import haversineDistance, pointInPolygon

# Varsayılan sütun adları (FilterData.py kaynak dosyasıyla uyumlu)
_DEFAULT_LAT_COL = "latitude"
_DEFAULT_LON_COL = "longitude"
_DEFAULT_DEVICE_COL = "device_aid"


class FootfallEngine:
    """
    Mobil konum verisi üzerinden ayak izi metriklerini hesaplar.

    Desteklenen filtreleme yöntemleri:
        - polygon  : Shapely + GeoJSON koordinatlarıyla nokta-polygon testi
        - haversine: Merkez nokta + yarıçap (metre) ile mesafe filtresi

    Girdi formatı (records):
        [
            {"device_aid": "abc123", "latitude": 41.01, "longitude": 28.97},
            ...
        ]

    Sütun adları özelleştirilebilir (latCol, lonCol, deviceCol parametreleri).

    FUTURE: Spark DataFrame desteği, S3 stream okuma → bkz. docs/future-features.md
    """

    def __init__(
        self,
        latCol: str = _DEFAULT_LAT_COL,
        lonCol: str = _DEFAULT_LON_COL,
        deviceCol: str = _DEFAULT_DEVICE_COL,
    ):
        self.latCol = latCol
        self.lonCol = lonCol
        self.deviceCol = deviceCol

    # ------------------------------------------------------------------
    # Dahili filtreler
    # ------------------------------------------------------------------

    def _filterByPolygon(self, records: list[dict], polygonCoords: list) -> list[dict]:
        return [
            r for r in records
            if pointInPolygon(r[self.latCol], r[self.lonCol], polygonCoords)
        ]

    def _filterByRadius(
        self,
        records: list[dict],
        centerLat: float,
        centerLon: float,
        radiusMeters: float,
    ) -> list[dict]:
        return [
            r for r in records
            if haversineDistance(r[self.latCol], r[self.lonCol], centerLat, centerLon)
            <= radiusMeters
        ]

    # ------------------------------------------------------------------
    # Footfall Count — unique device sayısı
    # ------------------------------------------------------------------

    def getCountByPolygon(self, records: list[dict], polygonCoords: list) -> int:
        """
        Polygon içindeki unique device sayısını döndürür.

        Args:
            records      : Konum kayıtları listesi
            polygonCoords: GeoJSON Polygon coordinates dizisi

        Returns:
            Unique device sayısı (int)
        """
        filtered = self._filterByPolygon(records, polygonCoords)
        return len({r[self.deviceCol] for r in filtered})

    def getCountByRadius(
        self,
        records: list[dict],
        centerLat: float,
        centerLon: float,
        radiusMeters: float,
    ) -> int:
        """
        Haversine yarıçapı içindeki unique device sayısını döndürür.

        Args:
            records     : Konum kayıtları listesi
            centerLat   : Merkez enlem
            centerLon   : Merkez boylam
            radiusMeters: Yarıçap (metre)

        Returns:
            Unique device sayısı (int)
        """
        filtered = self._filterByRadius(records, centerLat, centerLon, radiusMeters)
        return len({r[self.deviceCol] for r in filtered})

    # ------------------------------------------------------------------
    # Footfall Device List — ham device listesi
    # ------------------------------------------------------------------

    def getDeviceListByPolygon(
        self, records: list[dict], polygonCoords: list
    ) -> list[str]:
        """
        Polygon içindeki unique device ID'lerini döndürür.

        Returns:
            Sıralı device ID listesi
        """
        filtered = self._filterByPolygon(records, polygonCoords)
        return sorted({r[self.deviceCol] for r in filtered})

    def getDeviceListByRadius(
        self,
        records: list[dict],
        centerLat: float,
        centerLon: float,
        radiusMeters: float,
    ) -> list[str]:
        """
        Haversine yarıçapı içindeki unique device ID'lerini döndürür.

        Returns:
            Sıralı device ID listesi
        """
        filtered = self._filterByRadius(records, centerLat, centerLon, radiusMeters)
        return sorted({r[self.deviceCol] for r in filtered})
