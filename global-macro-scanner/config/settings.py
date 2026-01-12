# ⚙️ TECHNICAL SETTINGS (Keys, DB, API)
import os
from dotenv import load_dotenv

load_dotenv()

# 1. DATABASE & CACHE
DB_CONFIG = {
    'db_name': os.getenv("DB_NAME", "global_scanner"),
    'db_user': os.getenv("DB_USER", "postgres"),
    'db_pass': os.getenv("DB_PASS", "postgres"),
    'db_host': os.getenv("DB_HOST", "localhost"),
    'db_port': os.getenv("DB_PORT", "5432")
}

# 2. DATA PROVIDERS
DATA_SOURCE = os.getenv("DATA_SOURCE", "auto") # options: 'ibkr', 'yfinance', 'auto'

IBKR_CONFIG = {
    'host': os.getenv("IBKR_HOST", "127.0.0.1"),
    'port': int(os.getenv("IBKR_PORT", "7497")), # 7497 = Paper, 7496 = Live
    'client_id': int(os.getenv("IBKR_CLIENT_ID", "103")),
    # Data Type: Type 3 (Delayed) - Primary for ALL markets
    # Provides global delayed data access without rate limiting
}

# 3. ALERTS
TELEGRAM = {
    'token': os.getenv("TELEGRAM_TOKEN", ""),
    'chat_id': os.getenv("CHAT_ID", "")
}

# 4. RUNTIME
TEST_MODE = False                       # Console debugging
SCAN_INTERVAL_MINUTES = 30              # Production frequency
