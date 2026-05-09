-- Delete stock_fundamentals rows whose ticker matches a given suffix pattern.
-- Used by flatten_ibkr_final.py --replace to clear a single exchange before re-flatten.
-- Params: 1=ticker LIKE pattern (e.g. ending in .NS).
DELETE FROM stock_fundamentals WHERE ticker LIKE %s
