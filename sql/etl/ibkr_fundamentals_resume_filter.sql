SELECT ticker
FROM ibkr_fundamentals
WHERE xml_snapshot IS NOT NULL
  AND last_updated > NOW() - (%s || ' days')::INTERVAL
