-- Audit log of universe cleanup runs (which exchange, how many tickers
-- processed/valid/invalid, timestamp). Written by scripts/clean_nse_universe.py.
CREATE TABLE IF NOT EXISTS universe_cleanup_log (
    id              SERIAL PRIMARY KEY,
    exchange        VARCHAR(10),
    total_processed INTEGER,
    valid_count     INTEGER,
    invalid_count   INTEGER,
    cleaned_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes           TEXT
)
