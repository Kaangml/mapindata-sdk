# mapindata.data.s3_client
# Created: 2026-04-09 | Author: MapinData
# Subject: S3 üzerindeki büyük ölçekli mobil veri dosyalarını PySpark ile okur.
#          Spark oturumu ConfigManager.mobilitySparkConfig() ile dinamik kurulur.
#          İki bağlantı modu: IAM Role (EC2) veya Access Key (env).

import os
import sys

from mapindata.core.config import ConfigManager

# Mobil veri standart sütunları (echo schema — ham veri)
MOBILITY_DEFAULT_COLUMNS = [
    "timestamp",
    "device_aid",
    "latitude",
    "longitude",
    "horizontal_accuracy",
]

# V2 H3 zenginleştirilmiş temiz veri sütunları
MOBILITY_CLEAN_COLUMNS = [
    "timestamp",
    "device_aid",
    "latitude",
    "longitude",
    "horizontal_accuracy",
    "neighborhood",
    "h3_res9_id",
]


class S3Client:
    """
    MapinData S3 veri deposundan PySpark ile veri okur.

    Kullanım (temel):
        cfg = ConfigManager()
        client = S3Client(cfg)
        spark = client.createSession("FootfallJob")
        df = client.loadMobilityData(province="Istanbul")

    Kullanım (özel yol):
        df = client.loadData("s3a://mapindata-raw-data/echo_data_partitioned/province=Istanbul/")

    Spark oturumu singleton olarak yönetilir; aynı process içinde createSession tekrar
    çağrılırsa mevcut oturum döndürülür (SparkSession.builder.getOrCreate davranışı).
    """

    def __init__(self, config: ConfigManager):
        self._config = config
        self._spark = None

    # ------------------------------------------------------------------
    # Spark Oturumu
    # ------------------------------------------------------------------

    def createSession(self, appName: str = "MapinDataMobility"):
        """
        Mobil veri için optimize edilmiş Spark oturumu oluşturur ve döndürür.

        ConfigManager.mobilitySparkConfig() üzerinden dinamik bellek/paralellik
        ayarlarını otomatik alır. SPARK_JARS tanımlıysa S3A JAR'ları da eklenir.

        Args:
            appName: Spark UI'da görünecek uygulama adı

        Returns:
            SparkSession
        """
        try:
            from pyspark.sql import SparkSession
        except ImportError as e:
            raise ImportError(
                "PySpark gereklidir. Kurulum: pip install mapindata-sdk[mobility]"
            ) from e

        # Python worker/driver sürümü eşleşmesi — worker mismatch hatasını önler
        # (EC2'de python3.9 varsayılan, python3.11 çalıştırılıyorsa bu zorunlu)
        os.environ["PYSPARK_PYTHON"] = sys.executable
        os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

        # Ortam değişkenlerini Spark başlamadan önce ayarla
        os.environ.setdefault("SPARK_LOCAL_DIRS", "/var/tmp/spark-local")
        os.environ["_JAVA_OPTIONS"] = (
            f"-Djava.io.tmpdir=/var/tmp/spark-local "
            f"{os.environ.get('_JAVA_OPTIONS', '')}"
        ).strip()

        builder = SparkSession.builder
        for key, val in self._config.mobilitySparkConfig(appName).items():
            if val:  # boş string değerleri atla
                builder = builder.config(key, val)

        self._spark = builder.getOrCreate()

        return self._spark

    @property
    def spark(self):
        """Mevcut ya da yeni bir Spark oturumu döndürür (lazy)."""
        if self._spark is None:
            self.createSession()
        return self._spark

    # ------------------------------------------------------------------
    # Veri Okuma
    # ------------------------------------------------------------------

    def loadData(
        self,
        s3Path: str,
        basePath: str | None = None,
        format: str = "parquet",
        columns: list[str] | None = None,
    ):
        """
        S3'teki herhangi bir dosyayı Spark DataFrame olarak okur.

        Args:
            s3Path  : Tam S3 yolu (s3a://bucket/prefix/...)
            basePath: Partition tabanlı tablolarda kök yolu.
                      Belirtilmezse s3Path'den otomatik çıkarılmaz.
            format  : "parquet" (varsayılan) veya "csv"
            columns : Okunacak sütun listesi. None → tüm sütunlar

        Returns:
            pyspark.sql.DataFrame
        """
        reader = self.spark.read
        if basePath:
            reader = reader.option("basePath", basePath)

        if format == "parquet":
            df = reader.parquet(s3Path)
        elif format == "csv":
            df = reader.option("header", "true").csv(s3Path)
        else:
            raise ValueError(f"Desteklenmeyen format: {format}. Geçerli: parquet, csv")

        if columns:
            df = df.select(*columns)

        return df

    def loadMobilityData(
        self,
        province: str | None = None,
        columns: list[str] | None = None,
    ):
        """
        MapinData standart S3 şemasından (echo_data_partitioned) mobil veri yükler.

        S3 yolu ConfigManager üzerinden dinamik oluşturulur:
            s3a://{s3Bucket}/{s3RawPrefix}echo_data_partitioned/

        Partition filter:
            province="Istanbul"  →  .../province=Istanbul/
            province=None        →  tüm partition'lar (dikkatli kullan, büyük veri!)

        Args:
            province: İl adı (partition filter için). None → tüm iller
            columns : Okunacak sütun listesi. None → MOBILITY_DEFAULT_COLUMNS

        Returns:
            pyspark.sql.DataFrame — seçili sütunlarla filtrelenmiş mobil veri
        """
        tableRoot = (
            f"s3a://{self._config.s3Bucket}"
            f"/{self._config.s3RawPrefix.rstrip('/')}"
            f"/echo_data_partitioned"
        )

        readPath = f"{tableRoot}/province={province}/" if province else f"{tableRoot}/"

        return self.loadData(
            s3Path=readPath,
            basePath=f"{tableRoot}/",
            columns=columns or MOBILITY_DEFAULT_COLUMNS,
        )

    def loadCleanMobilityData(
        self,
        province: str,
        columns: list[str] | None = None,
    ):
        """
        MapinData V2 H3 zenginleştirilmiş temiz veri yükler.

        V2 veri seti: repartitionByRange(h3_res9_id, device_aid) ile S3'e yazılmış;
        h3_res9_id üzerinde Parquet row-group skip, footfall sorgularını ~14×
        hızlandırır. FootfallEngine Spark metodlarının önerilen girdi kaynağıdır.

        Desteklenen iller: istanbul, ankara (ConfigManager.mobilityDataPath ile)

        Args:
            province: İl adı (örn. "Istanbul", “istanbul”)
            columns : Okunacak sütun listesi. None → MOBILITY_CLEAN_COLUMNS
                      (timestamp, device_aid, lat, lon, hacc, neighborhood, h3_res9_id)

        Returns:
            pyspark.sql.DataFrame — V2 H3 sıralanmış temiz mobil veri
        """
        path = self._config.mobilityDataPath(province)
        return self.loadData(path, columns=columns or MOBILITY_CLEAN_COLUMNS)

    # ------------------------------------------------------------------
    # Temizlik
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Spark oturumunu kapatır ve dahili referansı temizler."""
        if self._spark:
            self._spark.stop()
            self._spark = None
