
from storage.database import DatabaseManager

db = DatabaseManager()

print("--- Clearing Database Data (Truncate) ---")
try:
    db.truncate_tables()
    print("✅ All tables cleared. Ready for fresh scan.")
except Exception as e:
    print(f"❌ Reset failed: {e}")
