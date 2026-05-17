-- Pull mkt_cap_usd for a set of tickers. Returns one row per ticker that
-- has a positive USD market cap; tickers missing a row should be treated
-- as having no fundamentals coverage.
-- Params: 1=tickers (text[]).
SELECT ticker, mkt_cap_usd
FROM stock_fundamentals
WHERE ticker = ANY(%s)
  AND mkt_cap_usd IS NOT NULL
  AND mkt_cap_usd > 0
