-- Bulk UPSERT into stock_fundamentals from a yahooquery quotes payload.
-- Sparse columns: marketCap + currency + identity only. Other ~70 columns
-- stay NULL for exchanges without IBKR XML coverage (IDX/SET).
--
-- Tuple contract (caller must pass values in this exact order):
--   ticker, company_name, mkt_cap_usd, price_currency, exchange_code, exchange_country
--
-- last_fundamental_update is intentionally NOT in the INSERT column list;
-- it is set to CURRENT_TIMESTAMP only on conflict, matching the existing
-- stock_fundamentals_fd_upsert.sql convention. First insert leaves it NULL.
INSERT INTO stock_fundamentals (
    ticker, company_name, mkt_cap_usd, price_currency, exchange_code, exchange_country
) VALUES %s
ON CONFLICT (ticker) DO UPDATE SET
    company_name            = EXCLUDED.company_name,
    mkt_cap_usd             = EXCLUDED.mkt_cap_usd,
    price_currency          = EXCLUDED.price_currency,
    exchange_code           = EXCLUDED.exchange_code,
    exchange_country        = EXCLUDED.exchange_country,
    last_fundamental_update = CURRENT_TIMESTAMP
