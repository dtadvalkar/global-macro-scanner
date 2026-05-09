"""
Phase 3 — Spark transformation over the bounded sample.

Reads data_files/spark/prices_daily_sample.parquet with an explicit StructType
(no inferSchema), computes 52w low + days_since_low per ticker against a fixed
as-of date, prints a deterministic preview, and writes the per-ticker feature
table to Parquet for the Phase 4 comparison.

Mirrors data/providers.py:66,247,270-273 semantics:
  - low_52w = min(low) over the trailing-252 window per ticker
  - low_date = date of FIRST occurrence of that min (tie-break: earliest date)
  - days_since_low = calendar days from AS_OF_DATE to low_date

Output: data_files/spark/features_spark.parquet
"""

from datetime import date
from pathlib import Path

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
AS_OF_DATE = date(2026, 4, 17)
LOOKBACK_TRADING_DAYS = 252
IN_PATH = "data_files/spark/prices_daily_sample.parquet"
OUT_PATH = "data_files/spark/features_spark.parquet"

# Expected column set; the precise Decimal precision comes from the Parquet
# footer (pyarrow chose it from psycopg2's Decimal payload). Verified post-read.
EXPECTED_COLS = {"ticker", "price_date", "open", "high", "low", "close", "volume"}


def main():
    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("spark_pilot_features")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    df = spark.read.parquet(IN_PATH)
    actual_cols = set(df.columns)
    if actual_cols != EXPECTED_COLS:
        raise ValueError(f"Schema mismatch: got {actual_cols}, expected {EXPECTED_COLS}")
    print("Schema:")
    df.printSchema()
    print(f"Loaded sample: rows={df.count()} tickers={df.select('ticker').distinct().count()}")

    # Trailing-252 window per ticker, ordered by price_date desc; rn=1 is the most recent row.
    w_recent = Window.partitionBy("ticker").orderBy(F.col("price_date").desc())
    trailing = (
        df.withColumn("rn", F.row_number().over(w_recent))
          .filter(F.col("rn") <= LOOKBACK_TRADING_DAYS)
          .drop("rn")
    )

    # Within the trailing window, find the row with min(low). Tie-break on earliest date
    # so this matches pandas Series.idxmin() (first label with the min value).
    w_min = Window.partitionBy("ticker").orderBy(F.col("low").asc(), F.col("price_date").asc())
    features = (
        trailing.withColumn("rn_min", F.row_number().over(w_min))
                .filter(F.col("rn_min") == 1)
                .select(
                    F.col("ticker"),
                    F.col("low").alias("low_52w"),
                    F.col("price_date").alias("low_date"),
                )
    )

    as_of_lit = F.lit(AS_OF_DATE)
    features = features.withColumn(
        "days_since_low",
        F.datediff(as_of_lit, F.col("low_date")).cast("int"),
    )

    out = features.orderBy("ticker")
    print("\nPreview (first 10 by ticker):")
    out.show(10, truncate=False)

    out.write.mode("overwrite").parquet(OUT_PATH)
    print(f"Wrote {OUT_PATH}: rows={out.count()}")

    spark.stop()


if __name__ == "__main__":
    main()
