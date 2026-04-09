"""LitreEstimator için birim testler."""
import pytest
from mapindata.analytics.litre_estimator import LitreEstimator


class TestLitreEstimatorInit:
    def test_default_weights(self):
        pytest.skip("Henüz implemente edilmedi")


class TestEstimateHybrid:
    def test_bar_high_capacity_high_density(self):
        pytest.skip("Henüz implemente edilmedi")

    def test_invalid_category_raises(self):
        pytest.skip("Henüz implemente edilmedi")

    def test_negative_capacity_raises(self):
        pytest.skip("Henüz implemente edilmedi")


class TestEstimateBatch:
    def test_batch_returns_same_count(self):
        pytest.skip("Henüz implemente edilmedi")
