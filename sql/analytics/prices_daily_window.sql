-- OHLCV rows for a list of tickers across a date window.
-- Params: 1=tickers (array, e.g. ['ABC.NS','DEF.NS']), 2=window start, 3=window end.
SELECT ticker, price_date, open, high, low, close, volume
FROM prices_daily
WHERE ticker = ANY(%s) AND price_date BETWEEN %s AND %s
ORDER BY ticker, price_date
