"""
Phase 5 — scale test.

Export the entire prices_daily table to Parquet (chunked, memory-safe), then
run the same feature transformation as 02_features_spark.py over the full
dataset. Reports per-stage timing and output row count.

Output:
  data_files/spark/prices_daily_full.parquet/  (Parquet directory)
  data_files/spark/features_full.parquet/      (per-ticker features)
"""

import time
from datetime import date
from pathlib import Path

import pandas as pd
from db import get_db
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

AS_OF_DATE = date(2026, 4, 17)
LOOKBACK_TRADING_DAYS = 252
CHUNK_ROWS = 500_000

FULL_PARQUET = Path("data_files/spark/prices_daily_full.parquet")
FEATURES_PARQUET = "data_files/spark/features_full.parquet"


def export_full():
    db = get_db()
    print(f"Exporting prices_daily to {FULL_PARQUET} (chunks of {CHUNK_ROWS:,})...")
    t0 = time.time()

    cols = ["ticker", "price_date", "open", "high", "low", "close", "volume"]
    parts: list[pd.DataFrame] = []
    offset = 0
    total = 0
    while True:
        rows = db.query_file(
            'analytics/prices_daily_chunk.sql',
            (CHUNK_ROWS, offset),
        )
        if not rows:
            break
        parts.append(pd.DataFrame(rows, columns=cols))
        total += len(rows)
        print(f"  fetched {total:>10,} rows ({time.time()-t0:.1f}s)")
        if len(rows) < CHUNK_ROWS:
            break
        offset += CHUNK_ROWS

    df = pd.concat(parts, ignore_index=True)
    print(f"In-memory: {len(df):,} rows, {df.memory_usage(deep=True).sum()/1e6:.1f} MB")

    FULL_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(FULL_PARQUET, index=False)
    elapsed = time.time() - t0
    size_mb = FULL_PARQUET.stat().st_size / 1e6
    print(f"Wrote {FULL_PARQUET} ({size_mb:.1f} MB) in {elapsed:.1f}s")
    return len(df), elapsed


def run_spark(input_rows):
    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("spark_pilot_scale")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    t0 = time.time()
    df = spark.read.parquet(str(FULL_PARQUET))
    n_rows = df.count()
    n_tickers = df.select("ticker").distinct().count()
    t_read = time.time() - t0
    print(f"\nSpark read: {n_rows:,} rows / {n_tickers:,} tickers in {t_read:.1f}s")
    if n_rows != input_rows:
        print(f"  WARN: row count drift {n_rows} vs export {input_rows}")

    t0 = time.time()
    w_recent = Window.partitionBy("ticker").orderBy(F.col("price_date").desc())
    trailing = (
        df.withColumn("rn", F.row_number().over(w_recent))
          .filter(F.col("rn") <= LOOKBACK_TRADING_DAYS)
          .drop("rn")
    )
    w_min = Window.partitionBy("ticker").orderBy(F.col("low").asc(), F.col("price_date").asc())
    features = (
        trailing.withColumn("rn_min", F.row_number().over(w_min))
                .filter(F.col("rn_min") == 1)
                .select(
                    F.col("ticker"),
                    F.col("low").alias("low_52w"),
                    F.col("price_date").alias("low_date"),
                )
                .withColumn("days_since_low",
                            F.datediff(F.lit(AS_OF_DATE), F.col("low_date")).cast("int"))
    )
    features.write.mode("overwrite").parquet(FEATURES_PARQUET)
    t_xform = time.time() - t0
    out = spark.read.parquet(FEATURES_PARQUET)
    n_out = out.count()
    print(f"Spark transform+write: {n_out:,} feature rows in {t_xform:.1f}s")

    print("\nPer-suffix sanity check:")
    out = out.withColumn("suffix",
        F.when(F.col("ticker").endswith(".NS"), F.lit("NSE"))
         .when(F.col("ticker").endswith(".HK"), F.lit("SEHK"))
         .when(F.col("ticker").endswith(".AX"), F.lit("ASX"))
         .when(F.col("ticker").endswith(".L"), F.lit("LSE"))
         .when(F.col("ticker").endswith(".SI"), F.lit("SGX"))
         .when(F.col("ticker").endswith(".SR"), F.lit("TADAWUL"))
         .when(F.col("ticker").endswith(".JO"), F.lit("JSE"))
         .otherwise(F.lit("OTHER")))
    out.groupBy("suffix").count().orderBy(F.col("count").desc()).show(truncate=False)

    spark.stop()
    return n_out, t_read, t_xform


def main():
    t_total = time.time()
    n_export, t_export = export_full()
    n_features, t_read, t_xform = run_spark(n_export)
    elapsed = time.time() - t_total
    print(f"\nSummary:")
    print(f"  export       : {n_export:>10,} rows -> parquet  ({t_export:.1f}s)")
    print(f"  spark read   : {n_export:>10,} rows              ({t_read:.1f}s)")
    print(f"  spark xform  : {n_features:>10,} feature rows    ({t_xform:.1f}s)")
    print(f"  total        : {elapsed:.1f}s")


if __name__ == "__main__":
    main()
