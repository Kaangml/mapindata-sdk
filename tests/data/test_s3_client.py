"""S3Client için birim testler."""
import pytest


class TestS3ClientSession:
    def test_create_session_requires_pyspark(self):
        pytest.skip(
            "PySpark gerektiriyor — entegrasyon ortamında çalıştırılmalı"
        )

    def test_mobility_spark_config_keys(self):
        """mobilitySparkConfig'in beklenen anahtarları içerdiğini doğrular."""
        import os
        os.environ.pop("MAPIN_DB_PASSWORD", None)

        from mapindata.core.config import ConfigManager
        cfg = ConfigManager()
        conf = cfg.mobilitySparkConfig("TestApp")

        assert "spark.driver.memory" in conf
        assert "spark.default.parallelism" in conf
        assert "spark.hadoop.fs.s3a.connection.timeout" in conf
        assert conf["spark.app.name"] == "TestApp"
        assert conf["spark.master"].startswith("local[")

    def test_spark_jars_empty_by_default(self):
        import os
        os.environ.pop("SPARK_JARS", None)

        from mapindata.core.config import ConfigManager
        cfg = ConfigManager()
        # SPARK_JARS boşken mobilitySparkConfig'de spark.jars olmamalı
        conf = cfg.mobilitySparkConfig()
        assert "spark.jars" not in conf

    def test_spark_jars_included_when_set(self):
        import os
        os.environ["SPARK_JARS"] = "/tmp/fake.jar"

        from mapindata.core.config import ConfigManager
        cfg = ConfigManager()
        conf = cfg.mobilitySparkConfig()
        assert conf.get("spark.jars") == "/tmp/fake.jar"
        os.environ.pop("SPARK_JARS", None)


class TestS3ClientLoadData:
    def test_load_data_requires_spark(self):
        pytest.skip(
            "Gerçek S3 bağlantısı gerektiriyor — entegrasyon ortamında çalıştırılmalı"
        )

    def test_load_mobility_data_requires_spark(self):
        pytest.skip(
            "Gerçek S3 bağlantısı gerektiriyor — entegrasyon ortamında çalıştırılmalı"
        )

    def test_invalid_format_raises(self):
        pytest.skip(
            "Spark oturumu gerektiriyor — entegrasyon ortamında çalıştırılmalı"
        )
