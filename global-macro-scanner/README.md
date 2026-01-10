# Global Macro Scanner

A sophisticated stock screening system that identifies stocks near their 52-week lows with strong volume characteristics across multiple global markets.

## 📊 Project Status
**Development Progress: 2 of 9 Major Tasks Completed**

See **[Master Development Plan](docs/master_development_plan.md)** for complete roadmap and task tracking.

### ✅ Completed Features
- **Enhanced Scanning Logic** - Technical indicators (RSI, MA, ATR) and pattern recognition
- **Performance Optimizations** - Optimized YFinance provider with caching and parallel processing

### 🚧 Next Priorities
- IBKR market permissions (waiting for support)
- Current markets testing (India, Australia, Singapore)
- Automated scheduling system
- Telegram alert enhancements

## Architecture Overview

The scanner uses a centralized criteria-driven architecture:

### Core Components

1. **`config/criteria.py`** - Single source of truth for all screening criteria
2. **`screening/screening_utils.py`** - Shared filtering logic applied to all data sources
3. **`data/providers.py`** - Data providers (IBKR, YFinance) that fetch and filter data
4. **`screener/core.py`** - Orchestrates the scanning process with fallback strategies

### Data Flow

```
Universe Generation → Provider Selection → Data Fetching → Centralized Filtering → Results
```

### Supported Markets

| Market | Code | Provider | Notes |
|--------|------|----------|-------|
| US | SMART | IBKR/YFinance | Primary provider |
| Canada | TSX (.TO) | IBKR/YFinance | Primary provider |
| India | NSE (.NS) | IBKR/YFinance | Primary provider |
| Indonesia | IDX (.JK) | YFinance only | IBKR not supported |
| Thailand | SET (.BK) | YFinance only | IBKR not supported |

## Screening Criteria

All criteria are centrally managed in `config/criteria.py`. Current active filters:

### Price & Momentum
- Within 1% of 52-week low (core signal)
- Optional: At least 50% below 52-week high (avoid dead cats)

### Volume & Liquidity
- Daily volume ≥ 100,000 OR
- Relative volume (RVOL) ≥ 2.0x 30-day average

### Market Cap Thresholds
- US/Canada: $500M minimum
- Emerging markets: $150M minimum

### Future Criteria (Planned)
- RSI filters (20-40 range)
- Moving average analysis
- Debt-to-equity ratios
- Fundamental metrics

## Installation & Setup

### Prerequisites

1. **Python 3.8+** with required packages:
   ```bash
   pip install yfinance ib_async psycopg2-binary python-dotenv financedatabase pandas numpy
   ```

2. **PostgreSQL database** for ticker caching (optional but recommended)

3. **IBKR TWS or IB Gateway** for IBKR data access (optional - YFinance fallback available)

### Configuration

1. **Environment Variables** (create `.env` file):
   ```bash
   # Database (optional)
   DB_NAME=global_scanner
   DB_USER=postgres
   DB_PASS=password
   DB_HOST=localhost
   DB_PORT=5432

   # IBKR (optional - for IBKR data access)
   IBKR_HOST=127.0.0.1
   IBKR_PORT=7497  # 7497=paper, 7496=live
   IBKR_CLIENT_ID=55

   # Telegram (optional - for alerts)
   TELEGRAM_TOKEN=your_bot_token
   CHAT_ID=your_chat_id
   ```

2. **Market Selection** (`config/markets.py`):
   - Enable/disable markets as needed
   - Modify market cap thresholds if desired

3. **Criteria Tuning** (`config/criteria.py`):
   - Adjust filter thresholds
   - Enable/disable optional criteria
   - Use presets for different strategies

## Usage

### Basic Scan

```bash
# Run single scan (TEST_MODE=True prevents alerts)
python main.py

# Production mode with scheduled scanning
# Edit config/settings.py: TEST_MODE = False
python main.py
```

### Custom Criteria

```python
from config.criteria import CRITERIA, PRESETS

# Use conservative preset
criteria = {**CRITERIA, **PRESETS['conservative']}

# Or modify specific criteria
custom_criteria = CRITERIA.copy()
custom_criteria['price_52w_low_pct'] = 1.005  # More strict
```

### Testing Individual Components

```python
# Test screening utility
from screening.screening_utils import should_pass_screening
from config.criteria import CRITERIA

test_data = {
    'symbol': 'AAPL',
    'price': 150,
    'low_52w': 140,
    'usd_mcap': 2000,
    'rvol': 3.0,
    'volume': 50000
}

result = should_pass_screening(test_data, CRITERIA)
print("Passes screening:", result is not None)
```

## Architecture Details

### Criteria Centralization

**Before:** Filtering logic scattered across providers with hardcoded thresholds.

**After:** All criteria defined in `config/criteria.py`, applied via `screening_utils.should_pass_screening()`.

### Provider Abstraction

Each provider:
1. Fetches raw market data
2. Calls centralized screening logic
3. Returns filtered results

### Fallback Strategy

1. **Option B:** IBKR server-side scanner (fast, pre-filtered)
2. **Option A:** IBKR bulk historical scan (comprehensive)
3. **Option C:** YFinance fallback (always works)

## Extending the System

### Adding New Criteria

1. Add to `config/criteria.py` with appropriate documentation
2. Implement logic in `screening_utils.should_pass_screening()`
3. Test with sample data

### Adding New Markets

1. Update `config/markets.py` with exchange mapping
2. Add market cap thresholds
3. Ensure provider supports the exchange

### Adding New Data Providers

1. Implement `BaseProvider` interface
2. Integrate with centralized screening
3. Add to `screener/core.py` fallback chain

## Troubleshooting

### Common Issues

1. **Unicode Encoding Errors**
   - Fixed: All emoji characters removed for Windows compatibility

2. **IBKR Connection Failures**
   - Ensure TWS/IB Gateway is running
   - Check port configuration (7497=paper, 7496=live)
   - Verify API is enabled in TWS settings

3. **No Results Found**
   - Check market activation in `config/markets.py`
   - Verify criteria aren't too restrictive
   - Check data provider connectivity

4. **Thailand/Indonesia Missing**
   - Expected: These markets use YFinance only
   - IBKR doesn't support delayed data for these exchanges

### Diagnostic Tools

```bash
# Test individual components
python -c "from screening.screening_utils import should_pass_screening; print('OK')"

# Check market data connectivity
python diagnostics.py

# Test specific providers
python tests/test_indonesia_access.py
```

## Development

### Code Structure

```
├── config/                 # Configuration files
│   ├── criteria.py        # Screening criteria (single source of truth)
│   ├── markets.py         # Market mappings and thresholds
│   └── settings.py        # Technical settings (API keys, DB, etc.)
├── screening/             # Core screening logic
│   ├── screening_utils.py # Centralized filtering logic
│   └── core.py            # Orchestration and fallback logic
├── data/                  # Data providers
│   ├── providers.py       # IBKR and YFinance implementations
│   └── currency.py        # Currency conversion utilities
├── screener/              # Market-specific scanning
│   ├── universe.py        # Stock universe generation
│   └── ibkr/              # IBKR-specific utilities
├── storage/               # Data persistence
│   ├── database.py        # PostgreSQL caching
│   └── csvlogging.py      # Result logging
├── alerts/                # Notification systems
│   └── telegram.py        # Telegram alerts
└── tests/                 # Diagnostic and testing tools
```

### Adding Features

1. **New Criteria:** Define in `criteria.py`, implement in `screening_utils.py`
2. **New Markets:** Add to `markets.py`, ensure provider compatibility
3. **New Providers:** Implement `BaseProvider` interface, integrate with core
4. **New Alerts:** Add to `alerts/` directory, integrate with main loop

## License

This project is for educational and research purposes. Always verify compliance with your broker's terms of service and local regulations before using in production.