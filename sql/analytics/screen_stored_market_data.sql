-- Latest stored market-data snapshot for a list of tickers, used by the
-- offline-feed screening path in data/providers.py:_screen_stored_market_data.
-- Params: 1=tickers (array, e.g. ['AAA.NS','BBB.NS']).
SELECT
    ticker,
    last_price,
    close_price,
    open_price,
    high_price,
    low_price,
    volume,
    last_updated
FROM current_market_data
WHERE ticker = ANY(%s)
ORDER BY ticker
