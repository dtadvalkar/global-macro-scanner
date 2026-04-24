# 📦 Installation Guide

> **Canonical setup reference:** `README.md` at the repo root — canonical Python version, venv location, and primary commands live there. This guide covers platform-specific detail and IBKR setup.

## Overview

Complete installation instructions for Global Market Scanner across different environments.

## System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Python**: 3.12 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB free space
- **Network**: Stable internet connection

### Recommended Setup
- **Python**: 3.12+
- **PostgreSQL**: 13+
- **RAM**: 16GB+
- **CPU**: Multi-core processor

## Installation Steps

### 1. Clone Repository
```bash
git clone <repository-url>
cd "Global Market Scanner"
```

### 2. Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
# Install PostgreSQL (varies by OS)
# Create database and user
createdb global_macro_scanner
createuser --createdb --login your_username
```

### 5. Configuration
Create `.env` file in project root:
```bash
# Database Configuration
DB_NAME=global_macro_scanner
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# IBKR Configuration (optional)
IBKR_HOST=127.0.0.1
IBKR_PORT=7496  # 7496 for live, 7497 for paper
IBKR_CLIENT_ID=1

# Telegram Notifications (optional)
TELEGRAM_TOKEN=your_bot_token
CHAT_ID=your_chat_id
```

### 6. Verify Installation
```bash
python db.py health
```

## IBKR Setup (Optional)

### Trader Workstation Installation
1. Download TWS from IBKR website
2. Install and configure API access
3. Enable API connections in TWS settings
4. Start TWS before running scans

### API Permissions
- Ensure your IBKR account has market data permissions
- Some exchanges require specific subscriptions

## Troubleshooting Installation

### Common Issues

**Python Version Error**
```bash
python --version  # Should be 3.12+
# If not, install Python 3.12+ from python.org
```

**PostgreSQL Connection Failed**
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Start PostgreSQL service (varies by OS)
# Windows: services.msc
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

**Import Errors**
```bash
pip install --force-reinstall -r requirements.txt
```

## Environment-Specific Setup

### Windows
- Use PowerShell or Command Prompt
- Ensure firewall allows Python/PostgreSQL
- Use forward slashes in paths

### macOS
- Use Terminal
- Consider using `pyenv` for Python version management
- PostgreSQL via Homebrew: `brew install postgresql`

### Linux (Ubuntu/Debian)
```bash
# System dependencies
sudo apt update
sudo apt install python3-dev postgresql postgresql-contrib

# Python virtual environment
sudo apt install python3-venv
```

### Docker Setup (Alternative)
```dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
```

## Post-Installation

### Run Tests
```bash
python -m pytest tests/  # If tests exist
```

### First Scan
```bash
python main.py --exchanges NSE --mode test
```

### Verify Database
```bash
python scripts/testing/check_progress.py
```

## Related Documentation

- **[Getting Started](./getting_started.md)** - Your first scan
- **[Usage Examples](./usage_examples.md)** - Common workflows
- **[Troubleshooting](./troubleshooting.md)** - Fix runtime issues

---