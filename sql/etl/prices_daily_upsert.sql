INSERT INTO prices_daily
    (ticker, price_date, open, high, low, close, volume)
VALUES %s
ON CONFLICT (ticker, price_date) DO UPDATE
    SET open = EXCLUDED.open,
        high = EXCLUDED.high,
        low  = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        datetimestamp = NOW()
