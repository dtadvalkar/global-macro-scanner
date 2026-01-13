# Tests Directory

This directory contains all test scripts organized by purpose and functionality.

## 📁 Directory Structure

### `provider_tests/`
Tests for individual data providers and their functionality.
- `test_provider_data.py` - Tests fundamental data availability from YFinance

### `integration_tests/`
End-to-end integration tests combining multiple components.
- `test_enhanced_features.py` - Tests enhanced scanning features (technical indicators, pattern recognition)

## 🧪 Running Tests

```bash
# Run all provider tests
cd tests/provider_tests
python test_provider_data.py

# Run integration tests
cd tests/integration_tests
python test_enhanced_features.py

# Run from project root
python tests/provider_tests/test_provider_data.py
```

## 📋 Test Categories

### Provider Tests
- Data availability verification
- API response validation
- Error handling testing

### Integration Tests
- End-to-end scanning workflows
- Multi-component interaction
- Performance benchmarking
- Feature validation

## 🔄 Continuous Integration

Tests are designed to be run:
- During development (feature validation)
- Before deployments (regression testing)
- Performance monitoring (benchmarking)

## 📊 Test Results

Recent test results:
- ✅ YFinance provides all fundamental fields (market cap, sector, industry, currency, country, exchange)
- ✅ Enhanced scanning features working correctly
- ✅ Technical indicators (RSI, MA, ATR) integrated
- ✅ Pattern recognition operational