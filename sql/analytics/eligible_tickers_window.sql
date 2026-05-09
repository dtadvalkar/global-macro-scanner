-- Eligible tickers for a date window with a minimum trading-day floor.
-- Params: 1=ticker LIKE pattern (e.g. ending in .NS), 2=window start,
--         3=window end, 4=min trading-day count, 5=row limit.
SELECT ticker
FROM prices_daily
WHERE ticker LIKE %s AND price_date BETWEEN %s AND %s
GROUP BY ticker
HAVING COUNT(*) >= %s
ORDER BY ticker
LIMIT %s
