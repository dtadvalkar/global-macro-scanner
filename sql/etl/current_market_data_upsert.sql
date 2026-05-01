INSERT INTO current_market_data
    (ticker, last_price, close_price, open_price, high_price, low_price, volume, last_updated)
VALUES %s
ON CONFLICT (ticker)
DO UPDATE SET
    last_price = EXCLUDED.last_price,
    close_price = EXCLUDED.close_price,
    open_price = EXCLUDED.open_price,
    high_price = EXCLUDED.high_price,
    low_price = EXCLUDED.low_price,
    volume = EXCLUDED.volume,
    last_updated = EXCLUDED.last_updated
WHERE EXCLUDED.last_updated >= current_market_data.last_updated
