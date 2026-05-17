-- Strict "dead .JK / .BK ticker" rule for IDX/SET universe cleanup.
-- Candidate = currently-active (or NULL status) IDX/SET ticker with
-- ZERO prices_daily rows AND no positive stock_fundamentals.mkt_cap_usd.
-- This is the conservative cleanup criterion used by
-- scripts/maintenance/mark_inactive_idx_set_dead_tickers.py.
--
-- Params: 1=IDX suffix LIKE pattern (the .JK wildcard),
--         2=SET suffix LIKE pattern (the .BK wildcard).
-- Suffix patterns are bound parameters so psycopg2's placeholder
-- parser does not mis-interpret literal percent characters in the SQL.
SELECT
    t.ticker,
    t.market,
    t.status,
    COALESCE(p.n_rows, 0)                                          AS prices_rows,
    COALESCE(f.mkt_cap_usd, 0)                                     AS mkt_cap_usd
FROM tickers t
LEFT JOIN (
    SELECT ticker, COUNT(*) AS n_rows
    FROM prices_daily
    GROUP BY ticker
) p USING (ticker)
LEFT JOIN (
    SELECT ticker, mkt_cap_usd
    FROM stock_fundamentals
    WHERE mkt_cap_usd IS NOT NULL AND mkt_cap_usd > 0
) f USING (ticker)
WHERE t.market IN ('IDX', 'SET')
  AND (t.ticker LIKE %s OR t.ticker LIKE %s)
  AND (t.status = 'ACTIVE' OR t.status IS NULL)
  AND COALESCE(p.n_rows, 0) = 0
  AND COALESCE(f.mkt_cap_usd, 0) = 0
ORDER BY t.market, t.ticker
