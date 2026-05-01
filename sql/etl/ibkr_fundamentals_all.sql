SELECT ticker, xml_snapshot, last_updated
FROM ibkr_fundamentals
WHERE xml_snapshot IS NOT NULL
ORDER BY ticker
