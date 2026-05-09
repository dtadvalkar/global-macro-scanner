-- Bulk UPSERT into stock_fundamentals_fd via execute_values.
-- Caller must pass tuples in this exact column order; column ordering is the
-- contract between this file and the Python batch builder.
INSERT INTO stock_fundamentals_fd (
    ticker, company_name, city, state, country, currency, exchange, market, website,
    isin, cusip, figi, composite_figi, shareclass_figi,
    industry, industry_group, sector, market_cap_category, zipcode, summary
) VALUES %s
ON CONFLICT (ticker) DO UPDATE SET
    company_name        = EXCLUDED.company_name,
    city                = EXCLUDED.city,
    state               = EXCLUDED.state,
    country             = EXCLUDED.country,
    currency            = EXCLUDED.currency,
    exchange            = EXCLUDED.exchange,
    market              = EXCLUDED.market,
    website             = EXCLUDED.website,
    isin                = EXCLUDED.isin,
    cusip               = EXCLUDED.cusip,
    figi                = EXCLUDED.figi,
    composite_figi      = EXCLUDED.composite_figi,
    shareclass_figi     = EXCLUDED.shareclass_figi,
    industry            = EXCLUDED.industry,
    industry_group      = EXCLUDED.industry_group,
    sector              = EXCLUDED.sector,
    market_cap_category = EXCLUDED.market_cap_category,
    zipcode             = EXCLUDED.zipcode,
    summary             = EXCLUDED.summary,
    last_updated        = CURRENT_TIMESTAMP
