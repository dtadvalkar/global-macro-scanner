-- One-off cleanup: delete stock_fundamentals_fd rows whose ticker is already
-- in the canonical .NSE format, leaving only legacy .NS.NSE rows that the
-- caller will then rename. Used by scripts/utils/fix_ticker_formats.py.
DELETE FROM stock_fundamentals_fd
WHERE ticker LIKE '%.NSE' AND ticker NOT LIKE '%.NS.NSE'
