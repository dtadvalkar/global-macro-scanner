"""Quick market-cap distribution check against the curated stock_fundamentals."""
from db import get_db

db = get_db()

print("--- Market Cap Distribution (curated stock_fundamentals) ---")
rows = db.query("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE mkt_cap_usd > 0) AS with_mcap,
        COUNT(*) FILTER (WHERE mkt_cap_usd IS NULL) AS null_mcap
    FROM stock_fundamentals
""", fetch='one')
print(f"total={rows[0]}, with_mcap={rows[1]}, null_mcap={rows[2]}")

print("\n--- Top 10 by mkt_cap_usd ---")
for row in db.query("""
    SELECT ticker, mkt_cap_usd, industry_trbc
    FROM stock_fundamentals
    WHERE mkt_cap_usd IS NOT NULL
    ORDER BY mkt_cap_usd DESC
    LIMIT 10
"""):
    print(row)
