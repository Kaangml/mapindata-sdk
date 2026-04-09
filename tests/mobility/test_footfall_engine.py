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
