# mapindata.core.config
# Created: 2026-04-09 | Author: MapinData
# Subject: Uygulama genelinde merkezi konfigürasyon yönetimi.
#          Tüm ayarlar ortam değişkenlerinden (env) okunur; hiçbir
#          değer doğrudan kodda sabitlenmez.
#          Spark ayarları boş bırakıldığında sistemin mevcut
#          CPU ve RAM kapasitesine göre otomatik hesaplanır.

import multiprocessing
import os


def _autoDriverMemory() -> str:
    """Sistemdeki kullanılabilir RAM'in %75'ini hesaplar, 'Xg' formatında döner."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    totalKb = int(line.split()[1])
                    totalGb = (totalKb // 1024 // 1024) * 3 // 4  # %75
                    return f"{max(totalGb, 4)}g"
    except OSError:
        pass
    return "4g"


class ConfigManager:
    """
    Ortam değişkenlerinden SDK konfigürasyonunu yönetir.

    Kullanım:
        cfg = ConfigManager()
        print(cfg.sparkMaster)          # local[8]
        print(cfg.sparkDriverMemory)    # 24g  (otomatik)
        print(cfg.s3Bucket)             # mapindata-prod
        print(cfg.radiusMeters)         # 15

    Ortam değişkenleri .env dosyasından ya da sistem env'inden okunur.
    Zorunlu alan eksikse ValueError fırlatılır.
    """

    # --- Dahili yardımcılar -----------------------------------------------

    @staticmethod
    def _getEnv(key: str, default: str | None = None, required: bool = False) -> str:
        val = os.environ.get(key, default)
        if required and not val:
            raise ValueError(f"Zorunlu ortam değişkeni eksik: {key}")
        return val or ""

    # --- Spark (dinamik) --------------------------------------------------

    @property
    def sparkCores(self) -> int:
        """Kullanılacak CPU çekirdek sayısı. SPARK_EXECUTOR_CORES yoksa tüm çekirdekler."""
        raw = os.environ.get("SPARK_EXECUTOR_CORES", "")
        return int(raw) if raw.isdigit() else multiprocessing.cpu_count()

    @property
    def sparkMaster(self) -> str:
        """Spark master URL. Örn: local[8]"""
        return f"local[{self.sparkCores}]"

    @property
    def sparkDriverMemory(self) -> str:
        """Driver belleği. SPARK_DRIVER_MEMORY yoksa sistem RAM'inin %75'i."""
        raw = os.environ.get("SPARK_DRIVER_MEMORY", "")
        return raw if raw else _autoDriverMemory()

    @property
    def sparkExecutorMemory(self) -> str:
        """Executor belleği. SPARK_EXECUTOR_MEMORY yoksa sparkDriverMemory ile aynı."""
        raw = os.environ.get("SPARK_EXECUTOR_MEMORY", "")
        return raw if raw else self.sparkDriverMemory

    @property
    def sparkDefaultParallelism(self) -> int:
        """spark.default.parallelism = çekirdek sayısı × 10"""
        return self.sparkCores * 10

    @property
    def sparkShufflePartitions(self) -> int:
        """spark.sql.shuffle.partitions = sparkDefaultParallelism ile senkron"""
        return self.sparkDefaultParallelism

    # --- AWS / S3 ---------------------------------------------------------

    @property
    def awsRegion(self) -> str:
        return self._getEnv("AWS_DEFAULT_REGION", "eu-central-1")

    @property
    def s3Bucket(self) -> str:
        return self._getEnv("MAPIN_S3_BUCKET", "mapindata-prod")

    @property
    def s3RawPrefix(self) -> str:
        return self._getEnv("MAPIN_S3_RAW_PREFIX", "raw/")

    @property
    def s3ProcessedPrefix(self) -> str:
        return self._getEnv("MAPIN_S3_PROCESSED_PREFIX", "processed/")

    # --- Veritabanı -------------------------------------------------------

    @property
    def dbHost(self) -> str:
        return self._getEnv("MAPIN_DB_HOST", "localhost")

    @property
    def dbPort(self) -> int:
        return int(self._getEnv("MAPIN_DB_PORT", "5432"))

    @property
    def dbName(self) -> str:
        return self._getEnv("MAPIN_DB_NAME", "mapindata")

    @property
    def dbUser(self) -> str:
        return self._getEnv("MAPIN_DB_USER", "mapindata_user")

    @property
    def dbPassword(self) -> str:
        return self._getEnv("MAPIN_DB_PASSWORD", required=True)

    @property
    def dbConnectionString(self) -> str:
        """SQLAlchemy formatında bağlantı dizesi."""
        return (
            f"postgresql+psycopg2://{self.dbUser}:{self.dbPassword}"
            f"@{self.dbHost}:{self.dbPort}/{self.dbName}"
        )

    # --- Genel ------------------------------------------------------------

    @property
    def environment(self) -> str:
        return self._getEnv("MAPIN_ENV", "development")

    @property
    def logLevel(self) -> str:
        return self._getEnv("MAPIN_LOG_LEVEL", "INFO")

    @property
    def radiusMeters(self) -> int:
        """Varsayılan Haversine yarıçapı (metre). MAPIN_RADIUS_METERS ile override edilebilir."""
        return int(self._getEnv("MAPIN_RADIUS_METERS", "15"))

    @property
    def sparkJars(self) -> str:
        """S3A erişimi için gerekli JAR dosyaları. SPARK_JARS env değişkeninden okunur."""
        return self._getEnv("SPARK_JARS", "")

    # --- Mobil Veri Spark Konfigürasyonu ---------------------------------

    def mobilitySparkConfig(self, appName: str = "MapinDataMobility") -> dict:
        """
        Büyük ölçekli mobil veri işleme için optimize edilmiş Spark konfigürasyon sözlüğü.

        Bellek ve paralellik ayarları ConfigManager'dan dinamik gelir.
        S3A bağlantı ayarları sabit fakat prod ortamında environment variable ile
        override edilebilir.

        Kullanım:
            cfg = ConfigManager()
            for key, val in cfg.mobilitySparkConfig("FootfallJob").items():
                builder = builder.config(key, val)

        Returns:
            dict — SparkSession.builder.config(key, value) çiftleri
        """
        config = {
            # --- Temel ---
            "spark.app.name": appName,
            "spark.master": self.sparkMaster,
            "spark.local.dir": "/var/tmp/spark-local",
            "spark.sql.warehouse.dir": "/var/tmp/spark-warehouse",
            # --- S3A Kimlik Doğrulama ---
            "spark.hadoop.fs.s3a.aws.credentials.provider": (
                "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
            ),
            # --- S3A Bağlantı ---
            "spark.hadoop.fs.s3a.connection.timeout": "60000",
            "spark.hadoop.fs.s3a.connection.establish.timeout": "60000",
            "spark.hadoop.fs.s3a.threads.max": "256",
            "spark.hadoop.fs.s3a.connection.maximum": "256",
            # --- S3A Upload / Multipart ---
            "spark.hadoop.fs.s3a.multipart.size": "268435456",       # 256 MB
            "spark.hadoop.fs.s3a.multipart.threshold": "536870912",   # 512 MB
            "spark.hadoop.fs.s3a.block.size": "268435456",
            "spark.hadoop.fs.s3a.fast.upload": "true",
            "spark.hadoop.fs.s3a.fast.upload.buffer": "disk",
            "spark.hadoop.fs.s3a.committer.name": "magic",
            # --- Bellek ---
            "spark.driver.memory": self.sparkDriverMemory,
            "spark.executor.memory": self.sparkExecutorMemory,
            "spark.driver.maxResultSize": "0",
            "spark.memory.fraction": "0.9",
            "spark.memory.storageFraction": "0.3",
            # --- Paralellik ---
            "spark.default.parallelism": str(self.sparkDefaultParallelism),
            "spark.sql.shuffle.partitions": str(self.sparkShufflePartitions),
            "spark.sql.files.maxPartitionBytes": "268435456",
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.sql.adaptive.advisoryPartitionSizeInBytes": "268435456",
            # --- Python Worker ---
            "spark.python.worker.reuse": "true",
            # --- Serileştirme ---
            "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
            "spark.kryoserializer.buffer.max": "1024m",
            "spark.kryoserializer.buffer": "128m",
            # --- Parquet / I/O ---
            "spark.sql.parquet.compression.codec": "snappy",
            "spark.sql.parquet.filterPushdown": "true",
            "spark.sql.parquet.mergeSchema": "false",
        }
        # JAR dosyaları tanımlıysa ekle
        if self.sparkJars:
            config["spark.jars"] = self.sparkJars
        return config

    # --- Mobil Veri Yol Yapılandırması ------------------------------------

    def mobilityDataPath(self, province: str) -> str:
        """
        Verilen il için V2 H3 zenginleştirilmiş Parquet veri yolunu döndürür.

        Suffix MAPIN_MOBILITY_DATA_SUFFIX env var ile override edilebilir.
        Varsayılan suffix il bazlı:
          - istanbul → v2_h3_alt_rowsorted  (repartitionByRange(130) + sortWithinPartitions(h3_res9_id) + 64MB block)
          - diğerleri → v2_h3_dev_sorted

        Args:
            province: İl adı (büyük/küçük harf duyarsız, örn. "Istanbul" → "istanbul")

        Returns:
            S3A uyumlu tam yol (str)
        """
        suffix = self._getEnv("MAPIN_MOBILITY_DATA_SUFFIX", "")
        if not suffix:
            suffix = (
                "v2_h3_alt_rowsorted"
                if province.lower() == "istanbul"
                else "v2_h3_dev_sorted"
            )
        return (
            f"s3a://mapindata-athena/results/bench_spatial/"
            f"{province.lower()}/{suffix}/"
        )

    @property
    def testProvince(self) -> str:
        """Test ve geliştirme için varsayılan il. MAPIN_TEST_PROVINCE ile override edilebilir."""
        return self._getEnv("MAPIN_TEST_PROVINCE", "istanbul")
