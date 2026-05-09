"""
Phase 4 — pandas baseline mirroring data/providers.py semantics.

Reads the same Parquet sample as the Spark job and computes 52w low +
days_since_low using the producer logic from data/providers.py:66,247,270-273:

    low_52w   = hist['Low'].min()                                   # full hist (1y)
    low_series= hist['Low'].tail(252) if len(hist)>=252 else hist['Low']
    low_date  = low_series.idxmin()
    days_since_low = (datetime.now() - low_date.replace(tzinfo=None)).days

For determinism we substitute datetime.now() with the pinned AS_OF_DATE.
The semantics (trailing-252, tie-break to earliest date via Series.idxmin)
match the Spark implementation in 02_features_spark.py.

Output: data_files/spark/features_pandas.parquet
"""

from datetime import date
from pathlib import Path

import pandas as pd

AS_OF_DATE = pd.Timestamp(date(2026, 4, 17))
LOOKBACK_TRADING_DAYS = 252
IN_PATH = Path("data_files/spark/prices_daily_sample.parquet")
OUT_PATH = Path("data_files/spark/features_pandas.parquet")


def compute_one(group: pd.DataFrame) -> pd.Series:
    hist = group.sort_values("price_date").reset_index(drop=True)
    hist = hist.set_index("price_date")

    low_series = hist["low"].tail(LOOKBACK_TRADING_DAYS) if len(hist) >= LOOKBACK_TRADING_DAYS else hist["low"]
    low_52w = low_series.min()
    low_date = low_series.idxmin()  # first label with min value
    days_since_low = (AS_OF_DATE.date() - low_date).days

    return pd.Series({
        "low_52w": low_52w,
        "low_date": low_date,
        "days_since_low": days_since_low,
    })


def main():
    df = pd.read_parquet(IN_PATH)
    print(f"Loaded sample: rows={len(df)} tickers={df['ticker'].nunique()}")

    features = (
        df.groupby("ticker", group_keys=False)
          .apply(compute_one, include_groups=False)
          .reset_index()
    )
    features["days_since_low"] = features["days_since_low"].astype("int64")

    print("\nPreview (first 10 by ticker):")
    print(features.head(10).to_string(index=False))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(OUT_PATH, index=False)
    print(f"\nWrote {OUT_PATH}: rows={len(features)}")


if __name__ == "__main__":
    main()
