# mapindata.mobility.footfall_engine
# Created: 2026-04-09 | Author: MapinData
# Subject: Mobil cihaz verisi üzerinden ayak izi metriklerini hesaplar.
#          Polygon veya Haversine yarıçapı bazlı filtreleme destekler.
#          Pure Python metodları (list[dict] girdi) + PySpark metodları
#          (Spark DataFrame girdi) olmak üzere iki katman sunar.

import json
import math

from mapindata.core.geo_utils import (
    autoKringK,
    h3PolygonCells,
    haversineDistance,
    pointInPolygon,
    polygonAreaM2,
)

_DEFAULT_LAT_COL = "latitude"
_DEFAULT_LON_COL = "longitude"
_DEFAULT_DEVICE_COL = "device_aid"

# Polyfill güvenilir olmadığı alan eşiği (< res9 hücre alanı ≈ 0.1 km²)
_SMALL_POLYGON_AREA_M2 = 100_000


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
        """Polygon içinde-mi kontrolü için Spark UDF üretir (PiP hassasiyet katmanı)."""
        try:
            from pyspark.sql.functions import udf  # noqa: PLC0415
            from pyspark.sql.types import BooleanType  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "PySpark gereklidir. Kurulum: pip install mapindata-sdk[mobility]"
            ) from e

        def checkPolygon(lat, lon):
            if lat is None or lon is None:
                return False
            try:
                import json as _json  # noqa: PLC0415
                from shapely.geometry import Point, shape  # noqa: PLC0415

                point = Point(lon, lat)
                polygon = shape({"type": "Polygon", "coordinates": _json.loads(polygonCoordsJson)})
                return bool(polygon.contains(point))
            except Exception:
                return False

        return udf(checkPolygon, BooleanType())

    def _h3CellsForPolygon(self, polygonCoords: list) -> list | None:
        """
        Polygon için H3 INT64 hücre listesi hesaplar.

        Alan < 100 000 m² (küçük polygon) → centroid cell + kring(autoKringK)
        Alan ≥ 100 000 m²  (büyük polygon) → polyfill + buffer(k=1)

        h3 kurulu değilse None döner (pre-filter atlanır).
        """
        try:
            import h3  # noqa: PLC0415

            area = polygonAreaM2(polygonCoords)
            if area < _SMALL_POLYGON_AREA_M2:
                k = autoKringK(polygonCoords)
                ring = polygonCoords[0]
                centLat = sum(c[1] for c in ring) / len(ring)
                centLon = sum(c[0] for c in ring) / len(ring)
                centCell = h3.latlng_to_cell(centLat, centLon, 9)
                return [h3.str_to_int(c) for c in h3.grid_disk(centCell, k)]
            else:
                return h3PolygonCells(polygonCoords, bufferK=1)
        except ImportError:
            return None

    def _filterByPolygonSpark(self, df, polygonCoords: list):
        """
        Polygon filtrelemesi — üç katmanlı optimize pipeline:

        1. BBox ön filtresi (Parquet sütun istatistikleri + Catalyst push-down):
           Polygon sınırlayıcı kutusunun dışındaki satırlar UDF'ye hiç girmez.
           Benchmark: BBox pre-filter, H3+PiP pipeline'ını 6-14× hızlandırdı.

        2. H3 hücre ön filtresi (h3_res9_id sütunu varsa):
           Parquet min/max row-group skip → sadece ilgili H3 hücrelerindeki
           satırlar okunur. Küçük polygon → centroid+kring; büyük → polyfill+buffer.

        3. PiP UDF (Shapely): Küçük aday küme üzerinde hassas nokta-polygon testi.
           h3 veya h3_res9_id yoksa BBox→PiP iki adımla devam eder.
        """
        from pyspark.sql.functions import col, lit  # noqa: PLC0415

        # 1) Polygon BBox ön-filtresi — Catalyst push-down, UDF öncesi
        ring = polygonCoords[0]
        minLat = min(c[1] for c in ring)
        maxLat = max(c[1] for c in ring)
        minLon = min(c[0] for c in ring)
        maxLon = max(c[0] for c in ring)
        candidates = df.filter(
            (col(self.latCol) >= lit(minLat)) & (col(self.latCol) <= lit(maxLat))
            & (col(self.lonCol) >= lit(minLon)) & (col(self.lonCol) <= lit(maxLon))
        )

        # 2) H3 hücre ön-filtresi
        h3Cells = self._h3CellsForPolygon(polygonCoords)
        schemaFields = {f.name for f in df.schema.fields}
        if h3Cells is not None and "h3_res9_id" in schemaFields:
            candidates = candidates.filter(col("h3_res9_id").isin(h3Cells))

        # 3) PiP UDF — sadece küçük aday küme üzerinde
        pipUdf = self._makePolygonUdf(json.dumps(polygonCoords))
        return candidates.filter(pipUdf(col(self.latCol), col(self.lonCol)))

    def _filterByRadiusSpark(self, df, centerLat: float, centerLon: float, radiusMeters: float):
        """
        BBox ön filtresi + H3 kring ön filtresi + Spark-native Haversine eşik kontrolü
        ile yarıçap filtrelemesi uygular. Python UDF kullanmaz.

        Spark-native Haversine:
            a = sin(Δφ/2)² + cos(φ₁)·cos(φ₂)·sin(Δλ/2)²
            d ≤ r  ↔  a ≤ sin(r / 2R)²   (UDF gerektirmez, Catalyst tarafından optimize edilir)

        Kring k formülü:
            k = ceil(radiusMeters / 174m)  — H3 res9 kenar uzunluğu ≈ 174m
            Komşu hücre merkez-merkez mesafesi ≈ 301m (174 × √3)
            kring dışında kalabilecek en yakın nokta = (k+1)×301 - 300m
            Bu her zaman > r olduğundan false negative imkansız (300/174 = 1.72 marjı)
            Benchmark doğrulaması: k=3 için r=500m → %0.00 sapma
        """
        from pyspark.sql.functions import col, cos, lit, radians, sin  # noqa: PLC0415

        R = 6_371_000.0

        # 1) BBox ön filtresi
        dLat = math.degrees(radiusMeters / R)
        dLon = math.degrees(radiusMeters / (R * math.cos(math.radians(centerLat))))
        candidates = df.filter(
            (col(self.latCol) >= centerLat - dLat)
            & (col(self.latCol) <= centerLat + dLat)
            & (col(self.lonCol) >= centerLon - dLon)
            & (col(self.lonCol) <= centerLon + dLon)
        )

        # 2) H3 kring ön filtresi (Parquet min/max skip için opsiyonel)
        try:
            import h3  # noqa: PLC0415

            # H3 res9 kenar uzunluğu ≈ 174m; komşu merkez-merkez ≈ 301m (174×√3)
            # kring(k) worst-case kapsaması = k×301 - 300m > r (false negative yok)
            # k=ceil(r/174) → k×300 > r çünkü 300/174 = 1.72 → güvenlik marjı var
            # Benchmark: k=3 → r=500m → %0.00 sapma
            k = max(1, math.ceil(radiusMeters / 174.0))
            centerCell = h3.latlng_to_cell(centerLat, centerLon, 9)
            kringCells = [h3.str_to_int(c) for c in h3.grid_disk(centerCell, k)]
            if "h3_res9_id" in {f.name for f in df.schema.fields}:
                candidates = candidates.filter(col("h3_res9_id").isin(kringCells))
        except ImportError:
            pass

        # 3) Spark-native Haversine eşik kontrolü (UDF yok)
        phi1Cos = math.cos(math.radians(centerLat))
        threshold = math.sin(radiusMeters / (2.0 * R)) ** 2
        dPhi = radians(col(self.latCol) - lit(centerLat))
        dLambda = radians(col(self.lonCol) - lit(centerLon))
        phi2 = radians(col(self.latCol))
        a = (
            sin(dPhi / lit(2.0)) * sin(dPhi / lit(2.0))
            + lit(phi1Cos) * cos(phi2) * sin(dLambda / lit(2.0)) * sin(dLambda / lit(2.0))
        )
        return candidates.filter(a <= lit(threshold))

    def getCountByPolygonSpark(self, df, polygonCoords: list) -> int:
        """
        Spark DataFrame üzerinde polygon filtresi uygulayarak unique device sayısını döndürür.

        Polygon boyutuna göre otomatik yöntem seçimi:
          - Alan < 100 000 m² → centroid+kring(0 veya 1) + PiP
          - Alan ≥ 100 000 m² → polyfill+buffer(1) + PiP

        Args:
            df           : Spark DataFrame (latitude, longitude, device_aid içermeli;
                           h3_res9_id INT64 varsa dosya seviyesinde I/O optimizasyonu sağlanır)
            polygonCoords: GeoJSON Polygon coordinates dizisi

        Returns:
            Unique device sayısı (int)
        """
        from pyspark.sql.functions import countDistinct  # noqa: PLC0415

        return (
            self._filterByPolygonSpark(df, polygonCoords)
            .agg(countDistinct(self.deviceCol))
            .collect()[0][0]
        )

    def getCountByRadiusSpark(
        self, df, centerLat: float, centerLon: float, radiusMeters: float
    ) -> int:
        """
        Spark DataFrame üzerinde Haversine filtresi uygulayarak unique device sayısını döndürür.

        BBox + H3 kring ön filtresi + Spark-native Haversine eşik karşılaştırması kullanır.
        Python UDF kullanmaz; Catalyst tarafından tamamen optimize edilir.

        Args:
            df          : Spark DataFrame (h3_res9_id INT64 varsa Parquet min/max skip etkin)
            centerLat   : Merkez enlem
            centerLon   : Merkez boylam
            radiusMeters: Yarıçap (metre)

        Returns:
            Unique device sayısı (int)
        """
        from pyspark.sql.functions import countDistinct  # noqa: PLC0415

        return (
            self._filterByRadiusSpark(df, centerLat, centerLon, radiusMeters)
            .agg(countDistinct(self.deviceCol))
            .collect()[0][0]
        )

    def getDeviceListByPolygonSpark(self, df, polygonCoords: list):
        """
        Polygon içindeki unique device ID'lerini Spark DataFrame olarak döndürür.

        Büyük veri için collect() yerine DataFrame döndürür;
        kullanıcı kendi iş akışında .collect() veya .write() çağırır.

        Returns:
            pyspark.sql.DataFrame — device_aid sütunu, tekrarsız
        """
        return (
            self._filterByPolygonSpark(df, polygonCoords)
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
        return (
            self._filterByRadiusSpark(df, centerLat, centerLon, radiusMeters)
            .select(self.deviceCol)
            .distinct()
        )

    def fetchDeviceRecords(self, df, deviceIds: list):
        """
        Belirtilen device ID'lerin tüm kayıtlarını Spark DataFrame olarak döndürür.

        ≤ 1 000 device: isin filtresi (Parquet min/max skip ile hızlı)
        > 1 000 device: broadcast join

        Args:
            df       : Kaynak Spark DataFrame
            deviceIds: Sorgulanacak device ID listesi

        Returns:
            pyspark.sql.DataFrame — sadece belirtilen device'ların satırları
        """
        from pyspark.sql import SparkSession  # noqa: PLC0415
        from pyspark.sql.functions import broadcast, col  # noqa: PLC0415

        if not deviceIds:
            spark = SparkSession.getActiveSession()
            if spark is None:
                raise RuntimeError("Aktif Spark oturumu bulunamadı.")
            return spark.createDataFrame(spark.sparkContext.emptyRDD(), df.schema)

        if len(deviceIds) <= 1_000:
            return df.filter(col(self.deviceCol).isin(deviceIds))

        spark = SparkSession.getActiveSession()
        if spark is None:
            raise RuntimeError("Aktif Spark oturumu bulunamadı.")
        deviceDf = spark.createDataFrame([(did,) for did in deviceIds], [self.deviceCol])
        return df.join(broadcast(deviceDf), on=self.deviceCol, how="inner")
