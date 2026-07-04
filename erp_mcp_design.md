# ERP MCP Server Design Report

This report summarizes the design, implementation, and verification of the **ERP Model Context Protocol (MCP) Server** for **FinOps Guardian**.

---

## 1. Database Architecture & Schema (`mcp_servers/schema.sql`)

The simulated ERP ledger is built on a PostgreSQL relational database. We defined a persistent table called `expenses` with indexes optimized for duplicate checks:

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    expense_date DATE NOT NULL,
    has_receipt BOOLEAN DEFAULT FALSE,
    has_itinerary BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20),
    tax_code VARCHAR(20),
    gl_code VARCHAR(20),
    cost_center VARCHAR(20),
    saving_insight TEXT,
    tax_deductibility TEXT,
    manager_decision VARCHAR(50),
    approval_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Model Context Protocol Tools (`mcp_servers/erp_server.py`)

Using the Anthropic Python MCP `FastMCP` framework, we expose four core JSON-RPC tools for agent consumption:

1. **`write_expense`**: Commits audited and approved expense claims to PostgreSQL. Generates transactional sequence IDs (e.g. `TXN-POSTGRES-0001`).
2. **`search_expenses`**: Queries historical claims from the database with optional search terms and category filters.
3. **`check_duplicate_claim`**: Performs exact duplicates verification using a 48-hour sliding window.
4. **`generate_summary`**: Aggregates totals (transaction count, sum spent) and provides breakdowns by category.

*Tool definitions schemas are documented in `mcp_servers/tools_definitions.json`.*

---

## 3. Database Migration Script (`mcp_servers/migration.py`)

We created a migration utility that reads `DATABASE_URL` from the `.env` file, connects to the PostgreSQL database, and executes the SQL schema definition to initialize the database tables.

---

## 4. Integration Verification

- **Real Integration**: Updated the Root Agent `run_audit` and `commit_to_ledger` nodes to call `check_duplicate_claim` and `write_expense` tools directly.
- **Isolated Tests (`tests/integration/test_erp_server.py`)**: Tests truncating and re-initializing the database on each run to verify the correctness of the tool operations.
- **Run & Test Status**: All 48 tests pass cleanly.
