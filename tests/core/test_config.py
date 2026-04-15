"""ConfigManager için birim testler."""
import os
import pytest
from mapindata.core.config import ConfigManager


class TestConfigManagerDefaults:
    def test_default_aws_region(self):
        os.environ.pop("AWS_DEFAULT_REGION", None)
        cfg = ConfigManager()
        assert cfg.awsRegion == "eu-central-1"

    def test_default_db_host(self):
        os.environ.pop("MAPIN_DB_HOST", None)
        cfg = ConfigManager()
        assert cfg.dbHost == "localhost"

    def test_default_environment(self):
        os.environ.pop("MAPIN_ENV", None)
        cfg = ConfigManager()
        assert cfg.environment == "development"


class TestConfigManagerRequiredFields:
    def test_missing_required_raises_valueerror(self):
        os.environ.pop("MAPIN_DB_PASSWORD", None)
        cfg = ConfigManager()
        with pytest.raises(ValueError, match="MAPIN_DB_PASSWORD"):
            _ = cfg.dbPassword

    def test_db_connection_string_format(self):
        os.environ["MAPIN_DB_PASSWORD"] = "testpass"
        cfg = ConfigManager()
        cs = cfg.dbConnectionString
        assert cs.startswith("postgresql+psycopg2://")
        assert "testpass" in cs
        os.environ.pop("MAPIN_DB_PASSWORD", None)


class TestConfigManagerProvince:
    def test_default_test_province_is_istanbul(self):
        os.environ.pop("MAPIN_TEST_PROVINCE", None)
        cfg = ConfigManager()
        assert cfg.testProvince == "istanbul"

    def test_test_province_env_override(self):
        os.environ["MAPIN_TEST_PROVINCE"] = "ankara"
        cfg = ConfigManager()
        assert cfg.testProvince == "ankara"
        os.environ.pop("MAPIN_TEST_PROVINCE", None)

    def test_mobility_data_path_istanbul(self):
        cfg = ConfigManager()
        path = cfg.mobilityDataPath("istanbul")
        assert path == "s3a://mapindata-athena/results/bench_spatial/istanbul/v2_h3_alt_dev_sorted/"

    def test_mobility_data_path_lowercases_province(self):
        cfg = ConfigManager()
        assert cfg.mobilityDataPath("Istanbul") == cfg.mobilityDataPath("istanbul")

    def test_mobility_data_path_ankara(self):
        cfg = ConfigManager()
        path = cfg.mobilityDataPath("ankara")
        assert "ankara" in path
        assert path.startswith("s3a://")

