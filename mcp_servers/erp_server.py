import os
from datetime import datetime, timedelta

import psycopg
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("erp_server")


def get_db_connection():
    """Helper to establish a connection to the PostgreSQL database."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg.connect(db_url)


@mcp.tool()
def write_expense(
    title: str,
    amount: float,
    category: str,
    expense_date: str,
    has_receipt: bool,
    has_itinerary: bool,
    risk_level: str,
    tax_code: str,
    gl_code: str,
    cost_center: str,
    saving_insight: str,
    tax_deductibility: str,
    manager_decision: str = "APPROVE",
    approval_status: str = "APPROVED",
) -> str:
    """
    Writes an audited and approved corporate expense claim into the PostgreSQL ERP ledger.
    Returns the transaction receipt and transaction ID.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Calculate next transaction ID
                cur.execute("SELECT COUNT(*) FROM expenses;")
                cnt = cur.fetchone()[0]
                txn_id = f"TXN-POSTGRES-{cnt + 1:04d}"

                cur.execute(
                    """
                    INSERT INTO expenses (
                        transaction_id, title, amount, category, expense_date,
                        has_receipt, has_itinerary, risk_level, tax_code,
                        gl_code, cost_center, saving_insight, tax_deductibility,
                        manager_decision, approval_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        txn_id,
                        title,
                        amount,
                        category,
                        expense_date,
                        has_receipt,
                        has_itinerary,
                        risk_level,
                        tax_code,
                        gl_code,
                        cost_center,
                        saving_insight,
                        tax_deductibility,
                        manager_decision,
                        approval_status,
                    ),
                )
            conn.commit()
        return f"Successfully committed transaction {txn_id} to PostgreSQL database."
    except Exception as e:
        return f"Database Error: Failed to write expense: {e}"


@mcp.tool()
def search_expenses(query: str | None = None, category: str | None = None) -> str:
    """
    Searches the historical PostgreSQL ERP ledger for matching expense records
    by title query or category.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                sql = "SELECT transaction_id, title, amount, category, expense_date, risk_level FROM expenses WHERE 1=1"
                params = []

                if query:
                    sql += " AND title ILIKE %s"
                    params.append(f"%{query}%")
                if category:
                    sql += " AND category = %s"
                    params.append(category.lower())

                cur.execute(sql, params)
                rows = cur.fetchall()
                if not rows:
                    return "No matching expenses found."

                results = []
                for r in rows:
                    results.append(
                        f"Txn: {r[0]} | Title: {r[1]} | Amount: ${r[2]:.2f} | Category: {r[3]} | Date: {r[4]} | Risk: {r[5]}"
                    )
                return "\n".join(results)
    except Exception as e:
        return f"Database Error: Failed to search expenses: {e}"


@mcp.tool()
def check_duplicate_claim(
    title: str, amount: float, category: str, expense_date: str
) -> str:
    """
    Scans the PostgreSQL ledger to check if a identical claim has been submitted
    within a 48-hour window of the target date.
    """
    try:
        date_str = str(expense_date).split(" ")[0].split("T")[0]
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=2)
        end_date = target_date + timedelta(days=2)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT transaction_id, expense_date FROM expenses
                    WHERE title = %s AND amount = %s AND category = %s
                    AND expense_date >= %s AND expense_date <= %s;
                    """,
                    (title, amount, category.lower(), start_date, end_date),
                )
                rows = cur.fetchall()
                if rows:
                    matches = [f"{r[0]} on {r[1]}" for r in rows]
                    return f"Duplicate claim detected. Matches found: {', '.join(matches)}."
                return "No duplicate claim detected."
    except Exception as e:
        return f"Database Error: Failed to check duplicates: {e}"


@mcp.tool()
def generate_summary() -> str:
    """
    Generates a financial summary of all expense records in the ledger,
    including transaction counts, total spend, and category breakdowns.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses;")
                count, total = cur.fetchone()

                cur.execute(
                    "SELECT category, COUNT(*), COALESCE(SUM(amount), 0) FROM expenses GROUP BY category;"
                )
                breakdowns = cur.fetchall()

                lines = [
                    "=== Financial ERP Ledger Summary ===",
                    f"Total Transactions: {count}",
                    f"Total Spend: ${total:.2f}",
                    "\nCategory Breakdown:",
                ]
                for cat, cnt, amt in breakdowns:
                    lines.append(
                        f"- {cat}: {cnt} transaction(s) | Total Spend: ${amt:.2f}"
                    )
                return "\n".join(lines)
    except Exception as e:
        return f"Database Error: Failed to generate summary: {e}"


if __name__ == "__main__":
    mcp.run()
