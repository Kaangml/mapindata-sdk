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
