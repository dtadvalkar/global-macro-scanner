-- OHLCV rows scoped by market(s) and date window, used by the offline
-- backtest workflow. Joins tickers so the caller can supply market names
-- (e.g. 'NSE','IDX','SET') instead of pre-resolving ticker lists.
-- Params: 1=markets (text[], e.g. ['NSE','IDX']),
--         2=window start, 3=window end.
SELECT t.market, pd.ticker, pd.price_date, pd.open, pd.high, pd.low, pd.close, pd.volume
FROM prices_daily pd
JOIN tickers t USING (ticker)
WHERE t.market = ANY(%s)
  AND pd.price_date BETWEEN %s AND %s
ORDER BY pd.ticker, pd.price_date
