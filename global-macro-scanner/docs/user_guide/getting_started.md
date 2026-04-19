# 🚀 Getting Started

> **Canonical setup reference:** `global-macro-scanner/README.md` — installation, env vars, and primary commands are authoritative there.

## Overview

Get up and running with Global Market Scanner in under 15 minutes. This guide covers your first scan and basic usage.

## Prerequisites

Before starting, ensure you have:
- ✅ Python 3.12 or higher
- ✅ PostgreSQL database
- ✅ IBKR Trader Workstation (optional, for live data)
- ✅ Basic command line knowledge

## Quick Start (3 Steps)

### Step 1: Installation
```bash
git clone <repository-url>
cd global-macro-scanner
pip install -r requirements.txt
```

### Step 2: Configuration
Create a `.env` file with your database credentials:
```bash
DB_NAME=your_database
DB_USER=your_username
DB_PASSWORD=your_password
```

### Step 3: First Scan
```bash
# Test with small dataset
python main.py --exchanges NSE --mode test

# Full scan (production)
python main.py --exchanges NSE --mode live
```

## What Happens Next

After your first scan:
1. **Database populated** with NSE stock data
2. **Results logged** to console and files
3. **Status updated** for active/inactive tickers

## Next Steps

- **[Installation Guide](./installation.md)** - Complete setup details
- **[Usage Examples](./usage_examples.md)** - Common workflows
- **[Troubleshooting](./troubleshooting.md)** - Fix common issues

---