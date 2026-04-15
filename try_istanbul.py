# mapindata-sdk gerçek veri denemesi
# İstanbul V2 → 149 m² Kadıköy polygon + 500m radius sorgusu

import os
import sys
import time

sys.path.insert(0, "src")

os.environ["SPARK_JARS"] = (
    "/home/ec2-user/jars/hadoop-aws-3.3.4.jar,"
    "/home/ec2-user/jars/aws-java-sdk-bundle-1.12.262.jar"
)
os.environ["PYSPARK_PYTHON"] = "/usr/bin/python3.11"
os.environ["PYSPARK_DRIVER_PYTHON"] = "/usr/bin/python3.11"

from pyspark.sql import SparkSession

from mapindata.core.config import ConfigManager
from mapindata.mobility.footfall_engine import FootfallEngine

# ---------------------------------------------------------------------------
# 1. Config + Spark
# ---------------------------------------------------------------------------
cfg = ConfigManager()
print(f"\n[CONFIG] province path : {cfg.mobilityDataPath('istanbul')}")
print(f"[CONFIG] sparkMaster   : {cfg.sparkMaster}")
print(f"[CONFIG] driverMemory  : {cfg.sparkDriverMemory}")

builder = SparkSession.builder
for k, v in cfg.mobilitySparkConfig("SDK_TryIstanbul").items():
    builder = builder.config(k, v)
spark = builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
print("[SPARK] session hazır\n")

# ---------------------------------------------------------------------------
# 2. Veri yükle
# ---------------------------------------------------------------------------
DATA_PATH = cfg.mobilityDataPath("istanbul")
t0 = time.time()
df = spark.read.parquet(DATA_PATH)
print(f"[DATA] schema: {[f.name for f in df.schema.fields]}")
print(f"[DATA] yüklendi ({time.time()-t0:.1f}s)")

engine = FootfallEngine(latCol="latitude", lonCol="longitude", deviceCol="device_aid")

# ---------------------------------------------------------------------------
# 3. Küçük Polygon — Kadıköy 149 m²
#    Beklenti: ~46 unique device (benchmark M2 sonucu)
# ---------------------------------------------------------------------------
SMALL_POLYGON = [
    [
        [29.02580158538396,  40.989444763077984],
        [29.025822868565854, 40.989545585936526],
        [29.025806722704033, 40.98958214803335],
        [29.025709847532767, 40.989591565539854],
        [29.025683427031623, 40.98945695046467],
        [29.02580158538396,  40.989444763077984],
    ]
]

print("\n── Küçük Polygon (Kadıköy 149 m²) ──────────────────────────")
t1 = time.time()
count_poly = engine.getCountByPolygonSpark(df, SMALL_POLYGON)
dur_poly = time.time() - t1
print(f"  unique device : {count_poly}")
print(f"  süre          : {dur_poly:.2f}s")
print(f"  beklenti      : ~46  (benchmark M2)")

# ---------------------------------------------------------------------------
# 4. Radius — Kadıköy merkez 500 m
# ---------------------------------------------------------------------------
CENTER_LAT = 40.989518
CENTER_LON = 29.025753
RADIUS_M   = 500

print("\n── Radius 500m (Kadıköy) ────────────────────────────────────")
t2 = time.time()
count_rad = engine.getCountByRadiusSpark(df, CENTER_LAT, CENTER_LON, RADIUS_M)
dur_rad = time.time() - t2
print(f"  unique device : {count_rad}")
print(f"  süre          : {dur_rad:.2f}s")

# ---------------------------------------------------------------------------
# 5. fetchDeviceRecords — polygon sonucundaki device'ları çek
# ---------------------------------------------------------------------------
if count_poly > 0:
    print("\n── fetchDeviceRecords (polygon cihazları) ───────────────────")
    device_df = engine.getDeviceListByPolygonSpark(df, SMALL_POLYGON)
    device_ids = [row.device_aid for row in device_df.collect()]
    print(f"  device listesi ({len(device_ids)} adet): {device_ids[:5]}{'...' if len(device_ids)>5 else ''}")

    t3 = time.time()
    records_df = engine.fetchDeviceRecords(df, device_ids[:10])
    row_count = records_df.count()
    dur_fetch = time.time() - t3
    print(f"  ilk 10 device'ın toplam kaydı: {row_count}  ({dur_fetch:.2f}s)")

spark.stop()
print("\n[DONE]")
