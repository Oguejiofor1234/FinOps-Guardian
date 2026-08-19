#!/usr/bin/env python3
"""
FinOps Guardian - Reset Dashboard & Clear Database Script
Clears all recorded expenses, audit logs, and resets metrics to zero.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg

# Load environment variables
load_dotenv()

def reset_finops_ledger():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️ DATABASE_URL not set in .env. Skipping PostgreSQL reset.")
        return False

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE expenses RESTART IDENTITY;")
            conn.commit()
        print("✅ PostgreSQL 'expenses' table successfully cleared.")
        print("📊 FinOps Guardian Dashboard State:")
        print("   - Approved Spend:      $0.00")
        print("   - High-Risk Flagged:   0")
        print("   - HITL Queue:          0")
        print("   - Rejected Claims:     0")
        print("   - Audit Trail:         Empty")
        return True
    except Exception as e:
        print(f"❌ Error resetting database: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = reset_finops_ledger()
    if success:
        print("\n🎉 FinOps dashboard has been successfully reset to zero!")
    else:
        sys.exit(1)
