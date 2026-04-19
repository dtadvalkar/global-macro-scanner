# MCP Database Server Setup Guide

This guide explains how to set up MCP (Model Context Protocol) server for PostgreSQL database interaction in your Global Macro Scanner project.

## 🚀 Quick Setup

### 1. Install MCP Server
```bash
# Install the MCP PostgreSQL server
pip install mcp-server-postgres

# Or install via uvx for isolated execution
pip install uvx
```

### 2. Configure Environment Variables
Create a `.env` file or set environment variables:
```bash
# PostgreSQL connection details
DB_NAME=global_macro
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432

# MCP Server configuration
MCP_POSTGRES_CONNECTION_STRING=postgresql://postgres:your_password_here@localhost:5432/global_macro
```

### 3. Test MCP Server
```bash
# Test basic connection
mcp-server-postgres --connection-string "postgresql://postgres:your_password@localhost:5432/global_macro" --help

# Or using uvx
uvx mcp-server-postgres --connection-string "postgresql://postgres:your_password@localhost:5432/global_macro" --help
```

## 🔧 Cursor IDE Integration

### Option 1: MCP Settings Configuration
Add to your Cursor MCP settings (`.cursor/mcp.json` or via Cursor settings):

```json
{
  "mcpServers": {
    "postgres-db": {
      "command": "uvx",
      "args": ["mcp-server-postgres", "--connection-string", "postgresql://postgres:your_password@localhost:5432/global_macro"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://postgres:your_password@localhost:5432/global_macro"
      }
    }
  }
}
```

### Option 2: Direct Command Integration
Configure Cursor to use the MCP server directly:
```json
{
  "mcpServers": {
    "postgres-db": {
      "command": "mcp-server-postgres",
      "args": ["--connection-string", "postgresql://postgres:your_password@localhost:5432/global_macro"]
    }
  }
}
```

## 🎯 Usage Examples

### In Cursor IDE
Once configured, you can use natural language queries like:

- "Show me the count of records in stock_fundamentals table"
- "What are the columns in the prices_daily table?"
- "Find all tickers with market cap > $1B"
- "Show me the latest price data for RELIANCE.NSE"
- "Check for data integrity issues in current_market_data"

### Advanced Queries
- "Compare the row counts between raw_fd_nse and stock_fundamentals"
- "Find tickers that exist in prices_daily but not in stock_fundamentals"
- "Show me the distribution of market cap categories"
- "Check when data was last updated in current_market_data"

## 🔄 Workflow Integration

### Development Phase
1. **Use `db.py` methods** for application logic and ETL processes
2. **Use MCP queries** for exploratory data analysis and debugging
3. **Add new `db.py` methods** as you identify common query patterns

### Debugging Phase
1. **MCP for quick inspection**: "What's in the current_market_data table?"
2. **db.py health checks**: `python db.py health` and `python db.py validate`
3. **Combined investigation**: Use both tools to understand data flow issues

### Maintenance Phase
1. **MCP for monitoring**: Check table sizes, data freshness, anomalies
2. **db.py for operations**: Bulk operations, schema changes, migrations

## 🛡️ Security Considerations

### Connection String Security
- Never commit connection strings with real passwords to git
- Use environment variables or `.env` files
- Consider using connection pooling for production workloads

### Query Safety
- MCP server provides read-only access by default
- Be cautious with write operations
- Use `db.py` for controlled write operations in production

## 🔍 Troubleshooting

### Common Issues

1. **Connection refused**
   ```bash
   # Check if PostgreSQL is running
   sudo systemctl status postgresql

   # Check connection details
   psql -h localhost -U postgres -d global_macro
   ```

2. **MCP server not found**
   ```bash
   # Ensure MCP server is installed
   pip list | grep mcp-server-postgres

   # Try installing again
   pip install --upgrade mcp-server-postgres
   ```

3. **Cursor integration issues**
   - Restart Cursor IDE
   - Check MCP configuration syntax
   - Verify environment variables are set

### Performance Tips
- Use connection pooling for high-frequency queries
- Index frequently queried columns
- Use `EXPLAIN ANALYZE` for query optimization
- Monitor connection pool usage

## 📚 Resources

- [MCP Server Postgres Documentation](https://github.com/modelcontextprotocol/server-postgres)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Cursor MCP Configuration](https://cursor.sh/docs/mcp)

## 🎯 Next Steps

1. Set up MCP server with your database credentials
2. Configure Cursor IDE integration
3. Test basic queries
4. Start using for data exploration and debugging

This setup provides you with both programmatic database access (`db.py`) and interactive exploration capabilities (MCP), giving you the best of both worlds for database operations.