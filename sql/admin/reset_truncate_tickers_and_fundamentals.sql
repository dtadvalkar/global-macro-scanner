-- DESTRUCTIVE — irreversible local-DB reset.
-- TRUNCATE both `tickers` and `stock_fundamentals`, restart identity, cascade.
-- Caller (scripts/utils/reset_db_schema.py) gates this behind a typed
-- confirmation phrase. Never invoke without that gate.
TRUNCATE TABLE tickers, stock_fundamentals RESTART IDENTITY CASCADE
