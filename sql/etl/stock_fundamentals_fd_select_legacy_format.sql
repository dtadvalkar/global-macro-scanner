-- Select stock_fundamentals_fd tickers still in the legacy .NS.NSE format.
-- Used by scripts/utils/fix_ticker_formats.py to drive a per-row rename.
SELECT ticker FROM stock_fundamentals_fd WHERE ticker LIKE '%.NS.NSE'
