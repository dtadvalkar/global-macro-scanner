-- Rename a single stock_fundamentals_fd row's ticker.
-- Used by scripts/utils/fix_ticker_formats.py to convert .NS.NSE → .NSE.
-- Params: 1=new ticker, 2=old ticker.
UPDATE stock_fundamentals_fd
SET ticker = %s
WHERE ticker = %s
