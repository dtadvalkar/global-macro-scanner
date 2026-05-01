INSERT INTO ibkr_fundamentals
    (ticker, xml_snapshot, xml_ratios, contract_details, last_updated)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (ticker) DO UPDATE SET
    xml_snapshot     = EXCLUDED.xml_snapshot,
    xml_ratios       = EXCLUDED.xml_ratios,
    contract_details = EXCLUDED.contract_details,
    last_updated     = EXCLUDED.last_updated
