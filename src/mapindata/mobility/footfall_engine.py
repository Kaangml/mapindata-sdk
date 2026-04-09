# mapindata.mobility.footfall_engine
# Created: 2026-04-09 | Author: MapinData
# Subject: Mobil cihaz verisi üzerinden ayak izi metriklerini hesaplar.
#          Polygon veya Haversine yarıçapı bazlı filtreleme destekler.
#          Pure Python metodları (list[dict] girdi) + PySpark metodları
#          (Spark DataFrame girdi) olmak üzere iki katman sunar.

import json

from mapindata.core.geo_utils import haversineDistance, pointInPolygon

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

    İki çalışma modu:
        Pure Python : getCount*/getDeviceList* — list[dict] kabul eder, küçük/orta veri için
        Spark       : getCount*Spark/getDeviceList*Spark — DataFrame kabul eder, büyük/S3 verisi için
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

    # ------------------------------------------------------------------
    # Spark Tabanlı Metodlar — büyük/S3 verisi
    # ------------------------------------------------------------------
    # PySpark opsiyonel bağımlılıktır.
    # Kurulum: pip install mapindata-sdk[mobility]
    # ------------------------------------------------------------------

    def _makePolygonUdf(self, polygonCoordsJson: str):
        """Polygon içinde-mi kontrolü için Spark UDF üretir."""
        try:
            from pyspark.sql.functions import udf
            from pyspark.sql.types import BooleanType
        except ImportError as e:
            raise ImportError(
                "PySpark gereklidir. Kurulum: pip install mapindata-sdk[mobility]"
            ) from e

        def checkPolygon(lat, lon):
            if lat is None or lon is None:
                return False
            try:
                import json as _json
                from shapely.geometry import Point, shape
                point = Point(lon, lat)
                polygon = shape({"type": "Polygon", "coordinates": _json.loads(polygonCoordsJson)})
                return bool(polygon.contains(point))
            except Exception:
                return False

        return udf(checkPolygon, BooleanType())

    def _makeRadiusUdf(self, centerLat: float, centerLon: float, radiusMeters: float):
        """Haversine yarıçap kontrolü için Spark UDF üretir."""
        try:
            from pyspark.sql.functions import udf
            from pyspark.sql.types import BooleanType
        except ImportError as e:
            raise ImportError(
                "PySpark gereklidir. Kurulum: pip install mapindata-sdk[mobility]"
            ) from e

        def checkRadius(lat, lon):
            if lat is None or lon is None:
                return False
            import math as _math
            R = 6_371_000
            phi1 = _math.radians(centerLat)
            phi2 = _math.radians(lat)
            dPhi = _math.radians(lat - centerLat)
            dLambda = _math.radians(lon - centerLon)
            a = (
                _math.sin(dPhi / 2) ** 2
                + _math.cos(phi1) * _math.cos(phi2) * _math.sin(dLambda / 2) ** 2
            )
            c = 2 * _math.atan2(_math.sqrt(a), _math.sqrt(1 - a))
            return (R * c) <= radiusMeters

        return udf(checkRadius, BooleanType())

    def getCountByPolygonSpark(self, df, polygonCoords: list) -> int:
        """
        Spark DataFrame üzerinde polygon filtresi uygulayarak unique device sayısını döndürür.

        Args:
            df           : Spark DataFrame (latitude, longitude, device_aid sütunları içermeli)
            polygonCoords: GeoJSON Polygon coordinates dizisi

        Returns:
            Unique device sayısı (int)
        """
        from pyspark.sql.functions import col, countDistinct

        polygonJson = json.dumps(polygonCoords)
        checkUdf = self._makePolygonUdf(polygonJson)
        filtered = df.filter(checkUdf(col(self.latCol), col(self.lonCol)))
        return filtered.agg(countDistinct(self.deviceCol)).collect()[0][0]

    def getCountByRadiusSpark(
        self, df, centerLat: float, centerLon: float, radiusMeters: float
    ) -> int:
        """
        Spark DataFrame üzerinde Haversine filtresi uygulayarak unique device sayısını döndürür.

        Args:
            df          : Spark DataFrame
            centerLat   : Merkez enlem
            centerLon   : Merkez boylam
            radiusMeters: Yarıçap (metre)

        Returns:
            Unique device sayısı (int)
        """
        from pyspark.sql.functions import col, countDistinct

        checkUdf = self._makeRadiusUdf(centerLat, centerLon, radiusMeters)
        filtered = df.filter(checkUdf(col(self.latCol), col(self.lonCol)))
        return filtered.agg(countDistinct(self.deviceCol)).collect()[0][0]

    def getDeviceListByPolygonSpark(self, df, polygonCoords: list):
        """
        Polygon içindeki unique device ID'lerini Spark DataFrame olarak döndürür.

        Büyük veri için collect() yerine DataFrame döndürür;
        kullanıcı kendi iş akışında .collect() veya .write() çağırır.

        Returns:
            pyspark.sql.DataFrame — device_aid sütunu, tekrarsız
        """
        from pyspark.sql.functions import col

        polygonJson = json.dumps(polygonCoords)
        checkUdf = self._makePolygonUdf(polygonJson)
        return (
            df.filter(checkUdf(col(self.latCol), col(self.lonCol)))
            .select(self.deviceCol)
            .distinct()
        )

    def getDeviceListByRadiusSpark(
        self, df, centerLat: float, centerLon: float, radiusMeters: float
    ):
        """
        Haversine yarıçapı içindeki unique device ID'lerini Spark DataFrame olarak döndürür.

        Returns:
            pyspark.sql.DataFrame — device_aid sütunu, tekrarsız
        """
        from pyspark.sql.functions import col

        checkUdf = self._makeRadiusUdf(centerLat, centerLon, radiusMeters)
        return (
            df.filter(checkUdf(col(self.latCol), col(self.lonCol)))
            .select(self.deviceCol)
            .distinct()
        )
