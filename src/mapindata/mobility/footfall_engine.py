# mapindata.mobility.footfall_engine
# Created: 2026-04-09 | Author: MapinData
# Subject: Mobil cihaz verisi üzerinden ayak izi metriklerini hesaplar.
#          Polygon / MultiPolygon / Haversine yarıçapı bazlı filtreleme destekler.
#          DuckDB (varsayılan) ve Spark motorları tek API üzerinden seçilebilir.

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

# Motor sabitleri — engine parametresi için
ENGINE_DUCKDB = "duckdb"
ENGINE_SPARK  = "spark"


class FootfallEngine:
    """
    Mobil konum verisi üzerinden ayak izi metriklerini hesaplar.

    Desteklenen filtreleme yöntemleri:
        - polygon  : Polygon / MultiPolygon / GeoJSON dosyası
        - haversine: Merkez nokta + yarıçap (metre)

    Büyük veri modu (S3):
        - DuckDB: con + s3Path ile başlatılır (varsayılan motor, 70× daha hızlı polygon)
        - Spark : df ile başlatılır

    Motor seçimi her metod çağrısında engine parametresiyle yapılır:
        engine="duckdb"  (varsayılan)
        engine="spark"

    Küçük veri / lokal mod:
        _countByPolygonLocal / _countByRadiusLocal (dahili kullanım)
    """

    def __init__(
        self,
        df=None,
        con=None,
        s3Path: str | None = None,
        latCol: str = _DEFAULT_LAT_COL,
        lonCol: str = _DEFAULT_LON_COL,
        deviceCol: str = _DEFAULT_DEVICE_COL,
    ):
        """
        Args:
            df      : Spark DataFrame (Spark motoru için)
            con     : DuckDB bağlantısı — DuckDBClient.connect() (DuckDB motoru için)
            s3Path  : DuckDB'nin okuyacağı S3 glob yolu — DuckDBClient.s3Path(province)
            latCol  : Enlem sütunu adı
            lonCol  : Boylam sütunu adı
            deviceCol: Cihaz ID sütunu adı
        """
        self._df = df
        self._con = con
        self._s3Path = s3Path
        self.latCol = latCol
        self.lonCol = lonCol
        self.deviceCol = deviceCol

    # ------------------------------------------------------------------
    # Coğrafi girdi normalleştirme
    # ------------------------------------------------------------------

    def _loadPolygonCoords(self, source) -> list:
        """
        Çeşitli girdi formatlarını dahili koordinat listesine dönüştürür.

        Kabul edilen formatlar:
            list          : Doğrudan koordinat dizisi (Polygon veya MultiPolygon)
            str (.json)   : GeoJSON dosya yolu — json.load() ile okunur
            dict          : GeoJSON nesnesi (type: Polygon veya MultiPolygon)

        Dönüş değeri, _normalizeCoords() ile standart forma alınır.
        """
        if isinstance(source, str):
            with open(source, encoding="utf-8") as f:
                source = json.load(f)

        if isinstance(source, dict):
            geoType = source.get("type", "")
            if geoType == "Feature":
                source = source["geometry"]
                geoType = source.get("type", "")
            if geoType in ("Polygon", "MultiPolygon"):
                return source["coordinates"]
            raise ValueError(f"Desteklenmeyen GeoJSON type: '{geoType}'")

        return source  # doğrudan list

    def _normalizeCoords(self, polygonCoords: list) -> list[list]:
        """
        Koordinatları ring listesine normalleştirir.

        Polygon    : [ [[lon,lat], ...] ]         → [ ring ]
        MultiPolygon: [ [[[lon,lat],...]], [...] ] → [ ring1, ring2, ... ]

        Her ring, [ [lon, lat], ... ] formundadır.
        Dönüş değeri: dış halkalar listesi (MultiPolygon → birden fazla eleman).
        """
        if not polygonCoords:
            return []
        # Polygon: ilk eleman bir ring (list of [x,y])
        # MultiPolygon: ilk eleman bir polygon ([ ring, ... ])
        firstElem = polygonCoords[0]
        if isinstance(firstElem[0][0], (int, float)):
            # Polygon koordinatları: [[lon,lat], ...]
            return [firstElem]
        elif isinstance(firstElem[0][0], list):
            # MultiPolygon koordinatları: [ [[lon,lat],...], ... ]
            return [poly[0] for poly in polygonCoords]
        return [firstElem]

    # ------------------------------------------------------------------
    # Unified Public API — Footfall Count
    # ------------------------------------------------------------------

    def getCountByPolygon(
        self, polygonCoords, engine: str = ENGINE_DUCKDB
    ) -> int:
        """
        Polygon / MultiPolygon içindeki unique device sayısını döndürür.

        Coğrafi girdi formatları:
            list  : Doğrudan koordinat dizisi (Polygon veya MultiPolygon)
            str   : GeoJSON dosya yolu (.json)
            dict  : GeoJSON Feature / Geometry nesnesi

        Args:
            polygonCoords: Polygon, MultiPolygon koordinatları veya GeoJSON yolu/nesnesi
            engine       : "duckdb" (varsayılan) veya "spark"

        Returns:
            Unique device sayısı (int)
        """
        coords = self._loadPolygonCoords(polygonCoords)
        if engine == ENGINE_DUCKDB:
            return self._duckCountByPolygon(coords)
        if engine == ENGINE_SPARK:
            return self._sparkCountByPolygon(coords)
        raise ValueError(f"Bilinmeyen engine: '{engine}'. 'duckdb' veya 'spark' kullanın.")

    def getCountByRadius(
        self,
        centerLat: float,
        centerLon: float,
        radiusMeters: float,
        engine: str = ENGINE_DUCKDB,
    ) -> int:
        """
        Haversine yarıçapı içindeki unique device sayısını döndürür.

        Args:
            centerLat   : Merkez enlem
            centerLon   : Merkez boylam
            radiusMeters: Yarıçap (metre)
            engine      : "duckdb" (varsayılan) veya "spark"

        Returns:
            Unique device sayısı (int)
        """
        if engine == ENGINE_DUCKDB:
            return self._duckCountByRadius(centerLat, centerLon, radiusMeters)
        if engine == ENGINE_SPARK:
            return self._sparkCountByRadius(centerLat, centerLon, radiusMeters)
        raise ValueError(f"Bilinmeyen engine: '{engine}'. 'duckdb' veya 'spark' kullanın.")

    # ------------------------------------------------------------------
    # Unified Public API — Device List
    # ------------------------------------------------------------------

    def getDeviceList(self, polygonCoords, engine: str = ENGINE_DUCKDB):
        """
        Polygon / MultiPolygon içindeki unique device ID listesini döndürür.

        DuckDB : list[str]
        Spark  : pyspark.sql.DataFrame (device_aid sütunu)

        Args:
            polygonCoords: Polygon, MultiPolygon koordinatları veya GeoJSON yolu/nesnesi
            engine       : "duckdb" (varsayılan) veya "spark"
        """
        coords = self._loadPolygonCoords(polygonCoords)
        if engine == ENGINE_DUCKDB:
            return self._duckDeviceListByPolygon(coords)
        if engine == ENGINE_SPARK:
            return self._filterByPolygonSpark(self._df, coords).select(self.deviceCol).distinct()
        raise ValueError(f"Bilinmeyen engine: '{engine}'. 'duckdb' veya 'spark' kullanın.")

    def getDeviceListByRadius(
        self,
        centerLat: float,
        centerLon: float,
        radiusMeters: float,
        engine: str = ENGINE_DUCKDB,
    ):
        """
        Haversine yarıçapı içindeki unique device ID listesini döndürür.

        DuckDB : list[str]
        Spark  : pyspark.sql.DataFrame (device_aid sütunu)
        """
        if engine == ENGINE_DUCKDB:
            return self._duckDeviceListByRadius(centerLat, centerLon, radiusMeters)
        if engine == ENGINE_SPARK:
            return (
                self._filterByRadiusSpark(self._df, centerLat, centerLon, radiusMeters)
                .select(self.deviceCol)
                .distinct()
            )
        raise ValueError(f"Bilinmeyen engine: '{engine}'. 'duckdb' veya 'spark' kullanın.")

    # ------------------------------------------------------------------
    # Unified Public API — Device Journey
    # ------------------------------------------------------------------

    def fetchDeviceRecords(self, deviceIds: list, engine: str = ENGINE_DUCKDB):
        """
        Belirtilen device ID'lerin tüm kayıtlarını döndürür.

        DuckDB : pandas.DataFrame
        Spark  : pyspark.sql.DataFrame
        ≤ 1 000 device: isin / IN (hızlı)
        > 1 000 device: broadcast join (Spark) / geçici tablo (DuckDB)

        Args:
            deviceIds: Sorgulanacak device_aid listesi
            engine   : "duckdb" (varsayılan) veya "spark"
        """
        if engine == ENGINE_DUCKDB:
            return self._duckFetchRecords(deviceIds)
        if engine == ENGINE_SPARK:
            return self._sparkFetchRecords(self._df, deviceIds)
        raise ValueError(f"Bilinmeyen engine: '{engine}'. 'duckdb' veya 'spark' kullanın.")

    # ------------------------------------------------------------------
    # DuckDB implementasyon katmanı
    # ------------------------------------------------------------------

    def _duckCountByPolygon(self, polygonCoords: list) -> int:
        """MultiPolygon desteği: UNION ile her ring ayrı sorgu → DISTINCT toplam."""
        rings = self._normalizeCoords(polygonCoords)
        if len(rings) == 1:
            geoJson = json.dumps({"type": "Polygon", "coordinates": polygonCoords
                                  if isinstance(polygonCoords[0][0], list) else polygonCoords})
            return self._runDuckSql(
                f"SELECT COUNT(DISTINCT {self.deviceCol}) FROM read_parquet('{self._s3Path}')"
                f" WHERE ST_Contains(ST_GeomFromGeoJSON('{geoJson}'),"
                f" ST_Point({self.lonCol}, {self.latCol}))"
            )

        # MultiPolygon: her polygon için UNION subquery, en dışta DISTINCT
        subqueries = []
        for ring in rings:
            gj = json.dumps({"type": "Polygon", "coordinates": [ring]})
            subqueries.append(
                f"SELECT {self.deviceCol} FROM read_parquet('{self._s3Path}')"
                f" WHERE ST_Contains(ST_GeomFromGeoJSON('{gj}'),"
                f" ST_Point({self.lonCol}, {self.latCol}))"
            )
        union = " UNION ".join(subqueries)
        return self._runDuckSql(
            f"SELECT COUNT(DISTINCT {self.deviceCol}) FROM ({union}) sub"
        )

    def _duckCountByRadius(
        self, centerLat: float, centerLon: float, radiusMeters: float
    ) -> int:
        """Haversine eşik kontrolü DuckDB SQL ile — Parquet sütun push-down uyumlu."""
        R = 6_371_000.0
        threshold = math.sin(radiusMeters / (2.0 * R)) ** 2
        phi1Cos = math.cos(math.radians(centerLat))
        dLat = math.degrees(radiusMeters / R)
        dLon = math.degrees(radiusMeters / (R * phi1Cos))
        return self._runDuckSql(
            f"""
            SELECT COUNT(DISTINCT {self.deviceCol})
            FROM read_parquet('{self._s3Path}')
            WHERE {self.latCol} BETWEEN {centerLat - dLat} AND {centerLat + dLat}
              AND {self.lonCol} BETWEEN {centerLon - dLon} AND {centerLon + dLon}
              AND (
                    pow(sin(radians({self.latCol} - {centerLat}) / 2.0), 2)
                  + {phi1Cos} * cos(radians({self.latCol}))
                    * pow(sin(radians({self.lonCol} - {centerLon}) / 2.0), 2)
                 ) <= {threshold}
            """
        )

    def _duckDeviceListByPolygon(self, polygonCoords: list) -> list[str]:
        """Polygon içindeki unique device ID listesi (DuckDB)."""
        rings = self._normalizeCoords(polygonCoords)
        subqueries = []
        for ring in rings:
            gj = json.dumps({"type": "Polygon", "coordinates": [ring]})
            subqueries.append(
                f"SELECT {self.deviceCol} FROM read_parquet('{self._s3Path}')"
                f" WHERE ST_Contains(ST_GeomFromGeoJSON('{gj}'),"
                f" ST_Point({self.lonCol}, {self.latCol}))"
            )
        union = " UNION ".join(subqueries)
        rows = self._con.execute(union).fetchall()
        return sorted({r[0] for r in rows})

    def _duckDeviceListByRadius(
        self, centerLat: float, centerLon: float, radiusMeters: float
    ) -> list[str]:
        """Haversine yarıçapı içindeki unique device ID listesi (DuckDB)."""
        R = 6_371_000.0
        threshold = math.sin(radiusMeters / (2.0 * R)) ** 2
        phi1Cos = math.cos(math.radians(centerLat))
        dLat = math.degrees(radiusMeters / R)
        dLon = math.degrees(radiusMeters / (R * phi1Cos))
        rows = self._con.execute(
            f"""
            SELECT DISTINCT {self.deviceCol}
            FROM read_parquet('{self._s3Path}')
            WHERE {self.latCol} BETWEEN {centerLat - dLat} AND {centerLat + dLat}
              AND {self.lonCol} BETWEEN {centerLon - dLon} AND {centerLon + dLon}
              AND (
                    pow(sin(radians({self.latCol} - {centerLat}) / 2.0), 2)
                  + {phi1Cos} * cos(radians({self.latCol}))
                    * pow(sin(radians({self.lonCol} - {centerLon}) / 2.0), 2)
                 ) <= {threshold}
            """
        ).fetchall()
        return sorted(r[0] for r in rows)

    def _duckFetchRecords(self, deviceIds: list):
        """
        Cihaz kayıtlarını DuckDB üzerinden pandas DataFrame olarak döndürür.

        ≤ 1 000 device: IN clause ile hızlı filtre
        > 1 000 device: geçici tablo + JOIN
        """
        if not deviceIds:
            import pandas as pd  # noqa: PLC0415
            return pd.DataFrame()

        if len(deviceIds) <= 1_000:
            ids = ", ".join(f"'{d}'" for d in deviceIds)
            return self._con.execute(
                f"SELECT * FROM read_parquet('{self._s3Path}')"
                f" WHERE {self.deviceCol} IN ({ids})"
            ).df()

        # > 1 000 device — geçici tablo ile JOIN
        import pandas as pd  # noqa: PLC0415

        self._con.execute("DROP TABLE IF EXISTS _tmp_device_ids")
        self._con.execute(f"CREATE TEMP TABLE _tmp_device_ids ({self.deviceCol} VARCHAR)")
        self._con.executemany(
            f"INSERT INTO _tmp_device_ids VALUES (?)",
            [(d,) for d in deviceIds],
        )
        return self._con.execute(
            f"SELECT m.* FROM read_parquet('{self._s3Path}') m"
            f" JOIN _tmp_device_ids t ON m.{self.deviceCol} = t.{self.deviceCol}"
        ).df()

    def _runDuckSql(self, sql: str) -> int:
        """Tek sayısal değer döndüren DuckDB sorgusunu çalıştırır."""
        if self._con is None:
            raise RuntimeError("DuckDB bağlantısı yok. DuckDBClient.connect() çağırın.")
        return self._con.execute(sql.strip()).fetchone()[0]

    # ------------------------------------------------------------------
    # Dahili lokal filtreler (küçük veri — list[dict])
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

    # Lokal / küçük veri hesaplamaları — dahili kullanım
    def _countByPolygonLocal(self, records: list[dict], polygonCoords: list) -> int:
        filtered = self._filterByPolygon(records, polygonCoords)
        return len({r[self.deviceCol] for r in filtered})

    def _countByRadiusLocal(
        self, records: list[dict], centerLat: float, centerLon: float, radiusMeters: float
    ) -> int:
        filtered = self._filterByRadius(records, centerLat, centerLon, radiusMeters)
        return len({r[self.deviceCol] for r in filtered})

    # ------------------------------------------------------------------
    # Spark implementasyon katmanı
    # ------------------------------------------------------------------

    def _makePolygonUdf(self, polygonCoordsJson: str, geoType: str = "Polygon"):
        """Polygon / MultiPolygon içinde-mi kontrolü için Spark UDF üretir."""
        try:
            from pyspark.sql.functions import udf  # noqa: PLC0415
            from pyspark.sql.types import BooleanType  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "PySpark gereklidir. Kurulum: pip install mapindata-sdk[mobility]"
            ) from e

        geoTypeLocal = geoType

        def checkPolygon(lat, lon):
            if lat is None or lon is None:
                return False
            try:
                import json as _json  # noqa: PLC0415
                from shapely.geometry import Point, shape  # noqa: PLC0415

                point = Point(lon, lat)
                polygon = shape({"type": geoTypeLocal, "coordinates": _json.loads(polygonCoordsJson)})
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
        Polygon / MultiPolygon filtrelemesi — üç katmanlı optimize pipeline:

        1. BBox ön filtresi (tüm ring'lerin birleşik sınır kutusu):
           Polygon sınırlayıcı kutusunun dışındaki satırlar UDF'ye hiç girmez.

        2. H3 hücre ön filtresi (h3_res9_id sütunu varsa):
           Parquet min/max row-group skip → sadece ilgili H3 hücrelerindeki
           satırlar okunur.

        3. PiP UDF (Shapely): Polygon ve MultiPolygon için hassas kontrol.
        """
        from pyspark.sql.functions import col, lit  # noqa: PLC0415

        rings = self._normalizeCoords(polygonCoords)

        # 1) Tüm ring'leri kapsayan birleşik BBox
        allPoints = [pt for ring in rings for pt in ring]
        minLat = min(c[1] for c in allPoints)
        maxLat = max(c[1] for c in allPoints)
        minLon = min(c[0] for c in allPoints)
        maxLon = max(c[0] for c in allPoints)
        candidates = df.filter(
            (col(self.latCol) >= lit(minLat)) & (col(self.latCol) <= lit(maxLat))
            & (col(self.lonCol) >= lit(minLon)) & (col(self.lonCol) <= lit(maxLon))
        )

        # 2) H3 hücre ön-filtresi (MultiPolygon → her ring için hücre topla)
        h3Cells = None
        try:
            h3Cells = []
            for ring in rings:
                cells = self._h3CellsForPolygon([ring])
                if cells is None:
                    h3Cells = None
                    break
                h3Cells.extend(cells)
        except Exception:
            h3Cells = None

        schemaFields = {f.name for f in df.schema.fields}
        if h3Cells is not None and "h3_res9_id" in schemaFields:
            candidates = candidates.filter(col("h3_res9_id").isin(h3Cells))

        # 3) PiP UDF — Shapely natively handles both Polygon and MultiPolygon
        # GeoJSON type ve koordinatları orijinal polygon'dan çıkar
        geoType, rawCoords = self._detectGeoType(polygonCoords)
        pipUdf = self._makePolygonUdf(json.dumps(rawCoords), geoType)
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

    def _detectGeoType(self, polygonCoords: list) -> tuple[str, list]:
        """
        Koordinat yapısından GeoJSON type ve raw coordinates'ı tespit eder.

        Polygon    : ilk → ring (list of [x,y])  → ("Polygon", coords)
        MultiPolygon: ilk → polygon (list of rings) → ("MultiPolygon", coords)
        """
        if polygonCoords and polygonCoords[0] and isinstance(polygonCoords[0][0][0], (int, float)):
            return "Polygon", polygonCoords
        return "MultiPolygon", polygonCoords

    def _sparkCountByPolygon(self, polygonCoords: list) -> int:
        from pyspark.sql.functions import countDistinct  # noqa: PLC0415

        if self._df is None:
            raise RuntimeError("Spark motoru için df gereklidir.")
        return (
            self._filterByPolygonSpark(self._df, polygonCoords)
            .agg(countDistinct(self.deviceCol))
            .collect()[0][0]
        )

    def _sparkCountByRadius(
        self, centerLat: float, centerLon: float, radiusMeters: float
    ) -> int:
        from pyspark.sql.functions import countDistinct  # noqa: PLC0415

        if self._df is None:
            raise RuntimeError("Spark motoru için df gereklidir.")
        return (
            self._filterByRadiusSpark(self._df, centerLat, centerLon, radiusMeters)
            .agg(countDistinct(self.deviceCol))
            .collect()[0][0]
        )

    def _sparkFetchRecords(self, df, deviceIds: list):
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

    # ------------------------------------------------------------------
    # Deprecated Spark alias'ları — geriye dönük uyumluluk
    # ------------------------------------------------------------------

    def getCountByPolygonSpark(self, df, polygonCoords: list) -> int:
        """Deprecated: getCountByPolygon(coords, engine='spark') kullanın."""
        from pyspark.sql.functions import countDistinct  # noqa: PLC0415

        return (
            self._filterByPolygonSpark(df, polygonCoords)
            .agg(countDistinct(self.deviceCol))
            .collect()[0][0]
        )

    def getCountByRadiusSpark(
        self, df, centerLat: float, centerLon: float, radiusMeters: float
    ) -> int:
        """Deprecated: getCountByRadius(lat, lon, r, engine='spark') kullanın."""
        from pyspark.sql.functions import countDistinct  # noqa: PLC0415

        return (
            self._filterByRadiusSpark(df, centerLat, centerLon, radiusMeters)
            .agg(countDistinct(self.deviceCol))
            .collect()[0][0]
        )

    def getDeviceListByPolygonSpark(self, df, polygonCoords: list):
        """Deprecated: getDeviceList(coords, engine='spark') kullanın."""
        return (
            self._filterByPolygonSpark(df, polygonCoords)
            .select(self.deviceCol)
            .distinct()
        )

    def getDeviceListByRadiusSpark(
        self, df, centerLat: float, centerLon: float, radiusMeters: float
    ):
        """Deprecated: getDeviceListByRadius(lat, lon, r, engine='spark') kullanın."""
        return (
            self._filterByRadiusSpark(df, centerLat, centerLon, radiusMeters)
            .select(self.deviceCol)
            .distinct()
        )
