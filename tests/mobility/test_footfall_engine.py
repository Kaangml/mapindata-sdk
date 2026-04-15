"""FootfallEngine için birim testler."""
import pytest
from mapindata.mobility.footfall_engine import FootfallEngine

# ---------------------------------------------------------------------------
# Ortak fixture
# ---------------------------------------------------------------------------

# Basit test verisi: İstanbul Beyoğlu civarı
RECORDS = [
    {"device_aid": "d001", "latitude": 41.033, "longitude": 28.978},
    {"device_aid": "d002", "latitude": 41.034, "longitude": 28.979},
    {"device_aid": "d001", "latitude": 41.033, "longitude": 28.978},  # tekrar (d001)
    {"device_aid": "d003", "latitude": 41.200, "longitude": 29.100},  # uzak nokta
]

# Polygon: d001 ve d002'yi içine alan küçük kare (GeoJSON: [[lon, lat], ...])
POLYGON = [
    [
        [28.970, 41.030],
        [28.990, 41.030],
        [28.990, 41.040],
        [28.970, 41.040],
        [28.970, 41.030],
    ]
]

# Merkez nokta ve yarıçap (d001, d002 içinde; d003 dışında)
CENTER_LAT, CENTER_LON = 41.033, 28.978
RADIUS_M = 500  # 500 metre

# Gerçek 149 m² Kadıköy polygon (benchmark M2 WINNER: centroid k=0 + PiP)
SMALL_POLYGON = [
    [
        [29.02580158538396, 40.989444763077984],
        [29.025822868565854, 40.989545585936526],
        [29.025806722704033, 40.98958214803335],
        [29.025709847532767, 40.989591565539854],
        [29.025683427031623, 40.98945695046467],
        [29.02580158538396, 40.989444763077984],
    ]
]


class TestCalculateByPolygon:
    def test_unique_visitors_inside(self):
        engine = FootfallEngine()
        assert engine.getCountByPolygon(RECORDS, POLYGON) == 2  # d001, d002

    def test_empty_polygon_returns_zero(self):
        engine = FootfallEngine()
        # Küçük nokta gibi polygon — hiçbir kayıt içinde değil
        emptyPolygon = [[[0.0, 0.0], [0.001, 0.0], [0.001, 0.001], [0.0, 0.001], [0.0, 0.0]]]
        assert engine.getCountByPolygon(RECORDS, emptyPolygon) == 0

    def test_result_columns(self):
        engine = FootfallEngine()
        devices = engine.getDeviceListByPolygon(RECORDS, POLYGON)
        assert isinstance(devices, list)
        assert "d001" in devices
        assert "d002" in devices
        assert "d003" not in devices


class TestCalculateByRadius:
    def test_center_includes_nearby_points(self):
        engine = FootfallEngine()
        count = engine.getCountByRadius(RECORDS, CENTER_LAT, CENTER_LON, RADIUS_M)
        assert count >= 2  # d001 ve d002 yakın; d003 uzak

    def test_result_has_expected_keys(self):
        engine = FootfallEngine()
        devices = engine.getDeviceListByRadius(RECORDS, CENTER_LAT, CENTER_LON, RADIUS_M)
        assert isinstance(devices, list)
        assert "d003" not in devices


class TestCalculateHourlyDistribution:
    def test_returns_24_hours(self):
        pytest.skip("Henüz implemente edilmedi — FUTURE FEATURE")


# ---------------------------------------------------------------------------
# Spark Tabanlı Metodlar
# ---------------------------------------------------------------------------

pyspark = pytest.importorskip("pyspark", reason="PySpark kurulu değil; pip install mapindata-sdk[mobility]")

# Spark testlerinde h3_res9_id YOK → H3 pre-filter atlanır, BBox+Haversine çalışır
RECORDS_SPARK = [
    {"device_aid": "d001", "latitude": 41.033, "longitude": 28.978},
    {"device_aid": "d002", "latitude": 41.034, "longitude": 28.979},
    {"device_aid": "d001", "latitude": 41.033, "longitude": 28.978},  # tekrar
    {"device_aid": "d003", "latitude": 41.200, "longitude": 29.100},  # uzak nokta
]


@pytest.fixture(scope="module")
def spark():
    import os
    from pyspark.sql import SparkSession

    os.environ.setdefault("PYSPARK_PYTHON", "/usr/bin/python3.11")
    os.environ.setdefault("PYSPARK_DRIVER_PYTHON", "/usr/bin/python3.11")

    session = (
        SparkSession.builder.master("local[2]")
        .appName("MapinDataSDKTest")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


class TestSparkRadiusOptimized:
    def test_count_nearby_devices(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        count = engine.getCountByRadiusSpark(df, CENTER_LAT, CENTER_LON, RADIUS_M)
        assert count >= 2  # d001, d002

    def test_far_point_excluded(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        result = engine.getDeviceListByRadiusSpark(df, CENTER_LAT, CENTER_LON, RADIUS_M)
        deviceIds = {row.device_aid for row in result.collect()}
        assert "d003" not in deviceIds

    def test_count_matches_pure_python(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        sparkCount = engine.getCountByRadiusSpark(df, CENTER_LAT, CENTER_LON, RADIUS_M)
        pythonCount = engine.getCountByRadius(RECORDS, CENTER_LAT, CENTER_LON, RADIUS_M)
        assert sparkCount == pythonCount


class TestSparkPolygonOptimized:
    def test_large_polygon_count(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        count = engine.getCountByPolygonSpark(df, POLYGON)
        assert count == 2  # d001, d002

    def test_large_polygon_matches_pure_python(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        sparkCount = engine.getCountByPolygonSpark(df, POLYGON)
        pythonCount = engine.getCountByPolygon(RECORDS, POLYGON)
        assert sparkCount == pythonCount

    def test_small_polygon_no_exception(self, spark):
        """
        Küçük polygon (149 m², < 1 H3 hücresi): centroid kring yöntemi
        RuntimeError / ZeroDivisionError fırlatmamalı.
        Test verisi bu koordinatlarda olmadığından 0 dönmesi beklenir.
        """
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        count = engine.getCountByPolygonSpark(df, SMALL_POLYGON)
        assert isinstance(count, int)
        assert count == 0  # test verisi Kadıköy'de değil

    def test_device_list_type(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        result = engine.getDeviceListByPolygonSpark(df, POLYGON)
        # DataFrame dönmeli, collect edilebilmeli
        rows = result.collect()
        deviceIds = {row.device_aid for row in rows}
        assert "d001" in deviceIds
        assert "d003" not in deviceIds


class TestFetchDeviceRecords:
    def test_fetch_known_device(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        result = engine.fetchDeviceRecords(df, ["d001"])
        rows = result.collect()
        assert len(rows) == 2  # d001 iki kez geçiyor
        assert all(r.device_aid == "d001" for r in rows)

    def test_fetch_empty_returns_no_rows(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        result = engine.fetchDeviceRecords(df, [])
        assert result.count() == 0

    def test_fetch_unknown_device_returns_empty(self, spark):
        df = spark.createDataFrame(RECORDS_SPARK)
        engine = FootfallEngine()
        result = engine.fetchDeviceRecords(df, ["d_nonexistent"])
        assert result.count() == 0

