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

