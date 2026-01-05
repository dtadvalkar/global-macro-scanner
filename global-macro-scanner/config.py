from config.criteria import CRITERIA
from config.markets import MARKETS, get_market_type, get_min_market_cap
from config.settings import (
    DATA_SOURCE, IBKR_CONFIG, TELEGRAM, 
    TEST_MODE, SCAN_INTERVAL_MINUTES, DB_CONFIG
)
from storage.database import DatabaseManager
import financedatabase as fd

db = DatabaseManager()

