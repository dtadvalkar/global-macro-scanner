-- Paginated chunk of prices_daily for full-table exports.
-- Params: 1=row limit, 2=row offset.
SELECT ticker, price_date, open, high, low, close, volume
FROM prices_daily
ORDER BY ticker, price_date
LIMIT %s OFFSET %s
