SELECT
    ticker,
    COALESCE(last_price, (market_data->'Ticker'->>'last')::numeric) as price,
    COALESCE(market_data->>'close', market_data->'Ticker'->>'close')::numeric as close,
    COALESCE(market_data->>'open', market_data->'Ticker'->>'open')::numeric as open,
    COALESCE(market_data->>'high', market_data->'Ticker'->>'high')::numeric as high,
    COALESCE(market_data->>'low', market_data->'Ticker'->>'low')::numeric as low,
    COALESCE(volume, (market_data->'Ticker'->>'volume')::numeric::bigint) as vol,
    last_updated
FROM ibkr_market_data
WHERE market_data IS NOT NULL
AND last_updated > %s
ORDER BY last_updated ASC
