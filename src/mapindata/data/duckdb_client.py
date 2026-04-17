# mapindata.data.duckdb_client
# Created: 2026-05-01 | Author: MapinData
# Subject: DuckDB ile S3 üzerindeki Parquet veri dosyalarına doğrudan erişim sağlar.
#          httpfs + spatial extension kurulumu, S3 kimlik doğrulaması ve
#          veri yolu yönetimini kapsar. FootfallEngine DuckDB metodlarının
#          bağlantı kaynağıdır.

import duckdb

from mapindata.core.config import ConfigManager


class DuckDBClient:
    """
    DuckDB bağlantısı ve S3 yol yönetimi.

    S3 kimlik doğrulaması boto3 DefaultCredentialChain üzerinden yapılır
    (EC2 IAM Role veya env var — AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY).

    Başlatma sırası:
        1. Bellek içi DuckDB bağlantısı oluştur
        2. httpfs + spatial extension kur / yükle
        3. AWS kimlik bilgilerini boto3'ten al, DuckDB'ye aktar
        4. Thread sayısını ConfigManager.sparkCores üzerinden ayarla

    Kullanım:
        cfg = ConfigManager()
        client = DuckDBClient(cfg)
        con = client.connect()
        path = client.s3Path("istanbul")
        # con ve path → FootfallEngine(con=con, s3Path=path)
    """

    def __init__(self, config: ConfigManager):
        self._config = config
        self._con = None

    # ------------------------------------------------------------------
    # Bağlantı
    # ------------------------------------------------------------------

    def connect(self) -> duckdb.DuckDBPyConnection:
        """
        DuckDB bağlantısını başlatır; zaten açıksa mevcut bağlantıyı döndürür.

        Yapılanlar:
          - httpfs extension: S3 okuma desteği
          - spatial extension: ST_Contains / ST_GeomFromGeoJSON coğrafi sorgular
          - boto3 DefaultCredentialChain → DuckDB S3 kimlik aktarımı
          - Thread sayısı → ConfigManager.sparkCores (tek makinede optimum parallelik)

        Returns:
            duckdb.DuckDBPyConnection
        """
        if self._con is not None:
            return self._con

        self._con = duckdb.connect()
        self._loadExtensions()
        self._configureS3()
        self._configureCores()
        return self._con

    def close(self) -> None:
        """DuckDB bağlantısını kapatır ve dahili referansı temizler."""
        if self._con is not None:
            self._con.close()
            self._con = None

    # ------------------------------------------------------------------
    # S3 Yol Yönetimi
    # ------------------------------------------------------------------

    def s3Path(self, province: str) -> str:
        """
        Verilen il için DuckDB-uyumlu S3 glob yolunu döndürür.

        mobilityDataPath s3a:// şemasıyla döner; DuckDB httpfs s3:// bekler.
        Bu metod şema dönüşümünü ve *.parquet glob eklemesini otomatik yapar.

        Args:
            province: İl adı (örn. "istanbul", "Istanbul")

        Returns:
            str — s3://bucket/prefix/province/suffix/*.parquet
        """
        # ConfigManager s3a:// döndürür, DuckDB httpfs s3:// bekler
        base = self._config.mobilityDataPath(province).replace("s3a://", "s3://")
        return f"{base.rstrip('/')}/*.parquet"

    # ------------------------------------------------------------------
    # Dahili kurulum
    # ------------------------------------------------------------------

    def _loadExtensions(self) -> None:
        """httpfs ve spatial extension'larını kurar ve yükler."""
        self._con.execute("INSTALL httpfs")
        self._con.execute("INSTALL spatial")
        self._con.execute("LOAD httpfs")
        self._con.execute("LOAD spatial")

    def _configureS3(self) -> None:
        """
        DuckDB için AWS kimlik doğrulamasını iki kademeli olarak kurar.

        Kademe 1 — Native credential chain (tercih edilen):
            SET s3_use_credential_chain = true
            DuckDB 1.0+ built-in AWS SDK sırası:
              env var → IAM Role (EC2 metadata) → ~/.aws/credentials → container role
            Tek bir SQL komutu, kimlik bilgileri Python katmanından geçmez.

        Kademe 2 — boto3 açık kimlik aktarımı (fallback):
            DuckDB build'inde credential chain devre dışıysa boto3 üzerinden alıp
            SET komutuyla aktar. Sadece bu kademede geçici token da aktarılır.

        Her iki kademede de S3 bölgesi ayarlanır.
        """
        region = self._config.awsRegion
        self._con.execute(f"SET s3_region='{region}'")

        # Kademe 1: native credential chain
        try:
            self._con.execute("SET s3_use_credential_chain=true")
            return
        except Exception:
            pass

        # Kademe 2: boto3 fallback — kimlik bilgileri SQL string'ine geçirilir
        # sadece credential chain desteklenmediğinde çalışır
        try:
            import boto3  # noqa: PLC0415

            session = boto3.Session()
            creds = session.get_credentials()
            if creds is not None:
                resolved = creds.get_frozen_credentials()
                self._con.execute(
                    "SET s3_access_key_id=?", [resolved.access_key]
                )
                self._con.execute(
                    "SET s3_secret_access_key=?", [resolved.secret_key]
                )
                if resolved.token:
                    self._con.execute(
                        "SET s3_session_token=?", [resolved.token]
                    )
        except ImportError:
            pass

    def _configureCores(self) -> None:
        """Thread sayısını Spark core ayarından türetir (tek makine optimizasyonu)."""
        try:
            # sparkMaster "local[8]" formatında — kaç core kullanılacağını çıkar
            master = self._config.sparkMaster
            if master.startswith("local[") and master.endswith("]"):
                cores = master[6:-1]
                if cores != "*":
                    self._con.execute(f"SET threads={int(cores)}")
        except Exception:
            # Belirlenemezse DuckDB kendi varsayılanını kullanır
            pass
