"""
Phase 4 — diff Spark and pandas feature outputs.

Acceptance criteria (from spark_pilot_plan.md):
  - Same row count.
  - Per-ticker low_52w matches exactly (Decimal min, no tolerance).
  - Per-ticker days_since_low matches exactly.
  - Empty/sparse-history tickers handled identically (we exclude them upstream
    via MIN_TRADING_DAYS in 01_export_sample.py, so no NULL handling needed in
    this pilot).

Exits non-zero on any mismatch.
"""

import sys
from pathlib import Path

import pandas as pd

SPARK_PATH = Path("data_files/spark/features_spark.parquet")
PANDAS_PATH = Path("data_files/spark/features_pandas.parquet")


def load_spark():
    # Spark writes a directory of part files; pandas.read_parquet handles that.
    return pd.read_parquet(SPARK_PATH).sort_values("ticker").reset_index(drop=True)


def load_pandas():
    return pd.read_parquet(PANDAS_PATH).sort_values("ticker").reset_index(drop=True)


def main():
    spark_df = load_spark()
    pandas_df = load_pandas()

    print(f"spark rows:  {len(spark_df)}  cols: {list(spark_df.columns)}")
    print(f"pandas rows: {len(pandas_df)} cols: {list(pandas_df.columns)}")

    if len(spark_df) != len(pandas_df):
        print(f"FAIL: row counts differ ({len(spark_df)} vs {len(pandas_df)})")
        sys.exit(1)

    if not (spark_df["ticker"].values == pandas_df["ticker"].values).all():
        print("FAIL: ticker sets differ after sort")
        sys.exit(1)

    merged = spark_df.merge(pandas_df, on="ticker", suffixes=("_spark", "_pandas"))

    # Cast Decimal -> str for exact compare; the values come from the same Postgres
    # numeric column written via parquet -> identical underlying decimal payload.
    low_match = (merged["low_52w_spark"].astype(str) == merged["low_52w_pandas"].astype(str))
    days_match = (merged["days_since_low_spark"].astype(int) == merged["days_since_low_pandas"].astype(int))
    date_match = (pd.to_datetime(merged["low_date_spark"]) == pd.to_datetime(merged["low_date_pandas"]))

    n = len(merged)
    print(f"\nlow_52w        matches: {low_match.sum()}/{n}")
    print(f"low_date       matches: {date_match.sum()}/{n}")
    print(f"days_since_low matches: {days_match.sum()}/{n}")

    if not (low_match.all() and days_match.all() and date_match.all()):
        print("\nFAIL: mismatches detected. Sample of disagreements:")
        bad = merged[~(low_match & days_match & date_match)].head(10)
        print(bad.to_string(index=False))
        sys.exit(1)

    print("\nPASS: Spark and pandas baselines agree on all 50 tickers.")


if __name__ == "__main__":
    main()
