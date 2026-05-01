SELECT ticker, xml_snapshot, last_updated
FROM ibkr_fundamentals
WHERE xml_snapshot IS NOT NULL
  AND ticker LIKE %s
ORDER BY ticker
