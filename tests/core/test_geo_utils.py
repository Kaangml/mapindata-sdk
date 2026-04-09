"""GeoUtils fonksiyonları için birim testler."""
import pytest
from mapindata.core.geo_utils import haversineDistance, pointInPolygon, boundingBox, centroid


class TestHaversineDistance:
    def test_istanbul_ankara_approximately_350km(self):
        # İstanbul (41.01, 28.97) – Ankara (39.92, 32.85) ≈ 350 km
        dist = haversineDistance(41.01, 28.97, 39.92, 32.85)
        assert 340_000 < dist < 360_000

    def test_same_point_returns_zero(self):
        assert haversineDistance(41.0, 29.0, 41.0, 29.0) == 0.0

    def test_symmetry(self):
        d1 = haversineDistance(41.0, 29.0, 40.0, 28.0)
        d2 = haversineDistance(40.0, 28.0, 41.0, 29.0)
        assert abs(d1 - d2) < 1  # 1 metre tolerans


class TestPointInPolygon:
    # Basit kare polygon: (0,0) – (0,1) – (1,1) – (1,0)
    # GeoJSON format: [[[lon, lat], ...]]  lat=x, lon=y burada
    SQUARE = [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]]

    def test_center_point_is_inside(self):
        assert pointInPolygon(0.5, 0.5, self.SQUARE) is True

    def test_outside_point_is_false(self):
        assert pointInPolygon(2.0, 2.0, self.SQUARE) is False


class TestBoundingBox:
    def test_basic_bounding_box(self):
        coords = [[1.0, 10.0], [3.0, 20.0], [2.0, 15.0]]
        bb = boundingBox(coords)
        assert bb["minLat"] == 1.0
        assert bb["maxLat"] == 3.0
        assert bb["minLon"] == 10.0
        assert bb["maxLon"] == 20.0


class TestCentroid:
    def test_square_centroid_is_center(self):
        coords = [[0.0, 0.0], [0.0, 2.0], [2.0, 2.0], [2.0, 0.0]]
        c = centroid(coords)
        assert c["lat"] == pytest.approx(1.0)
        assert c["lon"] == pytest.approx(1.0)

