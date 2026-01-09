Below is a self‑contained markdown “spec + sketch” you can drop into your repo (e.g., cashtag_backtest_plan.md). It outlines data structures and Python code skeletons for Phase‑1 backtesting using any cashtag‑tweet dataset (e.g., Piggybacking / StockNet).

Cashtag Backtest Plan
This document sketches a minimal pipeline to backtest cashtag tweet activity against subsequent stock returns using open datasets. It assumes:

A tweets dataset with at least: tweet_id, created_at, text, cashtags, ticker (or a way to parse one).
​

A price dataset with at least: date_time (or date), ticker, close, volume.
​

The goal is to derive simple rules like “tweet‑volume spike → higher/lower returns next day/week”.

1. Data layout
Assume two parquet/CSV files:

tweets.parquet

tweet_id: int / str

created_at: UTC timestamp

text: tweet text

cashtags: list/str of cashtags (e.g., ['AAPL', 'TSLA'] or "$AAPL $TSLA").
​

ticker: single primary ticker per tweet (you can derive this as first cashtag or using existing dataset field).

prices.parquet

ticker: stock symbol (e.g., AAPL)

date: date (or date_time intraday)

close: closing price

volume: traded volume

If your dataset does not have ticker explicitly in tweets, define:

ticker = first cashtag in tweet, stripping the $ sign.

2. Python environment setup
python
import pandas as pd
import numpy as np

# Optional: for speed
# pip install pyarrow fastparquet
3. Load and normalize tweets
python
# Load tweets
tweets = pd.read_parquet("tweets.parquet")  # or read_csv

# Ensure timestamp
tweets["created_at"] = pd.to_datetime(tweets["created_at"], utc=True)

# Simple cashtag → ticker (if needed)
def extract_first_cashtag(text):
    # very basic: split by space and look for words starting with '$'
    tokens = text.split()
    for tok in tokens:
        if tok.startswith("$") and len(tok) > 1:
            return tok[1:].upper()
    return None

if "ticker" not in tweets.columns:
    tweets["ticker"] = tweets["text"].map(extract_first_cashtag)

# Drop tweets without a valid ticker
tweets = tweets.dropna(subset=["ticker"])
4. Aggregate tweet activity into time buckets
Start simple: daily buckets per ticker.

python
# Convert to date for daily grouping
tweets["date"] = tweets["created_at"].dt.floor("D")

# Aggregate
agg = (
    tweets
    .groupby(["ticker", "date"])
    .agg(
        tweet_count=("tweet_id", "count"),
        unique_authors=("user_id", "nunique") if "user_id" in tweets.columns else ("tweet_id", "count")
    )
    .reset_index()
)
If you have sentiment scores in the dataset (some do: average polarity, etc.), you can include them:

python
if "sentiment" in tweets.columns:
    agg["avg_sentiment"] = tweets.groupby(["ticker", "date"])["sentiment"].transform("mean")
    agg = agg.drop_duplicates(subset=["ticker", "date"])
5. Merge with prices and compute returns
Assume daily OHLC data.

python
prices = pd.read_parquet("prices.parquet")  # or read_csv
prices["date"] = pd.to_datetime(prices["date"]).dt.floor("D")

# Keep only needed columns
prices = prices[["ticker", "date", "close"]]

# Merge tweet aggregates into price series
df = pd.merge(
    prices,
    agg,
    on=["ticker", "date"],
    how="left",
)

# Fill missing tweet metrics with 0
df["tweet_count"] = df["tweet_count"].fillna(0)
df["unique_authors"] = df["unique_authors"].fillna(0)
if "avg_sentiment" in df.columns:
    df["avg_sentiment"] = df["avg_sentiment"].fillna(0)
Compute forward returns (e.g., next‑day and 5‑day):

python
df = df.sort_values(["ticker", "date"])

for horizon in [1, 5]:
    df[f"fwd_ret_{horizon}d"] = (
        df.groupby("ticker")["close"]
        .pct_change(periods=horizon)
        .shift(-horizon)  # align today’s tweets with future returns
    )
6. Define “tweet spikes”
Compute rolling baseline tweet activity per ticker and a spike metric.

python
window = 10  # 10 trading days as baseline

df["tweet_roll_mean"] = (
    df.groupby("ticker")["tweet_count"]
    .transform(lambda s: s.rolling(window, min_periods=5).mean())
)

df["tweet_spike_ratio"] = df["tweet_count"] / (df["tweet_roll_mean"] + 1e-6)
Optionally cap extreme values:

python
df["tweet_spike_ratio"] = df["tweet_spike_ratio"].clip(upper=50)
Define spike buckets:

python
# Example: top 10% of spike_ratio vs the rest
quantile_cut = df["tweet_spike_ratio"].quantile(0.9)
df["is_spike_top10"] = df["tweet_spike_ratio"] >= quantile_cut
If sentiment exists:

python
if "avg_sentiment" in df.columns:
    pos_thresh = df["avg_sentiment"].quantile(0.7)
    neg_thresh = df["avg_sentiment"].quantile(0.3)
    
    df["is_pos_sent"] = df["avg_sentiment"] >= pos_thresh
    df["is_neg_sent"] = df["avg_sentiment"] <= neg_thresh
7. Simple backtest: conditional returns
Compare forward returns when there is a spike vs when there isn’t.

python
def summarize_condition(mask, horizon=1):
    subset = df[mask & df[f"fwd_ret_{horizon}d"].notna()]
    return {
        "n_obs": len(subset),
        "mean_ret": subset[f"fwd_ret_{horizon}d"].mean(),
        "median_ret": subset[f"fwd_ret_{horizon}d"].median(),
        "win_rate": (subset[f"fwd_ret_{horizon}d"] > 0).mean(),
    }

summary = {
    "spike_top10_1d": summarize_condition(df["is_spike_top10"], horizon=1),
    "spike_top10_5d": summarize_condition(df["is_spike_top10"], horizon=5),
    "no_spike_1d": summarize_condition(~df["is_spike_top10"], horizon=1),
    "no_spike_5d": summarize_condition(~df["is_spike_top10"], horizon=5),
}
summary
If sentiment exists, test interaction:

python
if "avg_sentiment" in df.columns:
    cond_pos_spike = df["is_spike_top10"] & df["is_pos_sent"]
    cond_neg_spike = df["is_spike_top10"] & df["is_neg_sent"]
    
    sentiment_summary = {
        "pos_spike_1d": summarize_condition(cond_pos_spike, horizon=1),
        "pos_spike_5d": summarize_condition(cond_pos_spike, horizon=5),
        "neg_spike_1d": summarize_condition(cond_neg_spike, horizon=1),
        "neg_spike_5d": summarize_condition(cond_neg_spike, horizon=5),
    }
    sentiment_summary
This tells you whether high tweet spikes (and optionally positive/negative sentiment) actually tilt future returns in your historical sample.
​

8. Mapping this into your live screener
Once you find a rule that looks promising, you can express it in screener‑friendly terms, e.g.:

“Flag a ticker if: tweet_count today ≥ k × 10‑day average AND unique_authors ≥ m AND stock meets liquidity filter.”

Your live pipeline later only needs:

A daily (or intraday) tweet count per ticker.

The same spike logic as above.

Because the backtest is fully in Python/pandas on open datasets, you can iterate on window lengths, thresholds, and horizons before touching any live source.
​

If you want a variant that’s intraday (e.g., 30‑minute buckets instead of daily), you can swap dt.floor("D") for dt.floor("30min") and repeat essentially the same aggregation and forward‑return logic on intraday bars.