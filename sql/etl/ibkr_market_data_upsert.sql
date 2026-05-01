INSERT INTO ibkr_market_data
    (ticker, market_data, last_price, bid_price, ask_price, volume, avg_volume, last_updated)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (ticker) DO UPDATE SET
    market_data = EXCLUDED.market_data,
    last_price = EXCLUDED.last_price,
    bid_price = EXCLUDED.bid_price,
    ask_price = EXCLUDED.ask_price,
    volume = EXCLUDED.volume,
    avg_volume = EXCLUDED.avg_volume,
    last_updated = EXCLUDED.last_updated
