import os

import psycopg
import pytest

from mcp_servers.erp_server import (
    check_duplicate_claim,
    generate_summary,
    search_expenses,
    write_expense,
)


@pytest.fixture(autouse=True)
def clean_database():
    """Cleans the expenses database before each test run."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL is not set.")

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE expenses RESTART IDENTITY CASCADE;")
        conn.commit()


def test_write_expense_tool():
    """Verifies that the write_expense tool inserts a record into the database."""
    res = write_expense(
        title="Laptop Charger",
        amount=79.99,
        category="office",
        expense_date="2026-07-02",
        has_receipt=True,
        has_itinerary=False,
        risk_level="LOW",
        tax_code="OFF-100",
        gl_code="6300",
        cost_center="CC-OPS",
        saving_insight="Standard purchase.",
        tax_deductibility="100% deduction",
    )
    assert "Successfully committed transaction" in res
    assert "TXN-POSTGRES-0001" in res

    # Verify in DB
    db_url = os.getenv("DATABASE_URL")
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title, amount, category FROM expenses WHERE transaction_id = 'TXN-POSTGRES-0001';"
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == "Laptop Charger"
            assert float(row[1]) == 79.99
            assert row[2] == "office"


def test_search_expenses_tool():
    """Verifies that search_expenses tool queries database records accurately."""
    # Write two records
    write_expense(
        title="Lunch with client A",
        amount=45.00,
        category="meals",
        expense_date="2026-07-01",
        has_receipt=True,
        has_itinerary=False,
        risk_level="LOW",
        tax_code="ME-50",
        gl_code="6200",
        cost_center="CC-MARKETING",
        saving_insight="",
        tax_deductibility="",
    )
    write_expense(
        title="Hotel stay Sales B",
        amount=350.00,
        category="travel",
        expense_date="2026-07-02",
        has_receipt=True,
        has_itinerary=True,
        risk_level="LOW",
        tax_code="TRV-100",
        gl_code="6100",
        cost_center="CC-SALES",
        saving_insight="",
        tax_deductibility="",
    )

    # Test query match
    res_query = search_expenses(query="Lunch")
    assert "Lunch with client A" in res_query
    assert "Hotel stay" not in res_query

    # Test category match
    res_cat = search_expenses(category="travel")
    assert "Hotel stay" in res_cat
    assert "Lunch" not in res_cat

    # Test no results
    res_none = search_expenses(query="Nonexistent")
    assert "No matching expenses found." in res_none


def test_check_duplicate_claim_tool():
    """Verifies duplicate check flags duplicates within 48-hour window but ignores others."""
    # Write a baseline claim
    write_expense(
        title="Team Lunch",
        amount=120.00,
        category="meals",
        expense_date="2026-07-02",
        has_receipt=True,
        has_itinerary=False,
        risk_level="LOW",
        tax_code="ME-50",
        gl_code="6200",
        cost_center="CC-MARKETING",
        saving_insight="",
        tax_deductibility="",
    )

    # Exact duplicate within 48h (same date)
    dup_res = check_duplicate_claim(
        title="Team Lunch", amount=120.00, category="meals", expense_date="2026-07-02"
    )
    assert "Duplicate claim detected" in dup_res

    # Duplicate within 48h (1 day offset)
    dup_res_offset = check_duplicate_claim(
        title="Team Lunch", amount=120.00, category="meals", expense_date="2026-07-03"
    )
    assert "Duplicate claim detected" in dup_res_offset

    # No duplicate (different amount)
    diff_amount = check_duplicate_claim(
        title="Team Lunch", amount=125.00, category="meals", expense_date="2026-07-02"
    )
    assert "No duplicate claim detected." in diff_amount

    # No duplicate (outside 48h window - 4 days offset)
    outside_window = check_duplicate_claim(
        title="Team Lunch", amount=120.00, category="meals", expense_date="2026-07-06"
    )
    assert "No duplicate claim detected." in outside_window


def test_generate_summary_tool():
    """Verifies that generate_summary aggregates counts and categories correctly."""
    write_expense(
        title="Lunch",
        amount=50.00,
        category="meals",
        expense_date="2026-07-02",
        has_receipt=True,
        has_itinerary=False,
        risk_level="LOW",
        tax_code="ME-50",
        gl_code="6200",
        cost_center="CC-MARKETING",
        saving_insight="",
        tax_deductibility="",
    )
    write_expense(
        title="Monitor",
        amount=200.00,
        category="office",
        expense_date="2026-07-02",
        has_receipt=True,
        has_itinerary=False,
        risk_level="LOW",
        tax_code="OFF-100",
        gl_code="6300",
        cost_center="CC-OPS",
        saving_insight="",
        tax_deductibility="",
    )

    summary = generate_summary()
    assert "Total Transactions: 2" in summary
    assert "Total Spend: $250.00" in summary
    assert "meals: 1 transaction(s)" in summary
    assert "office: 1 transaction(s)" in summary
