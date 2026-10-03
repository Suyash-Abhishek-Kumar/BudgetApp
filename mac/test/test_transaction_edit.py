"""
test/test_transaction_edit.py

Validates transaction updating, field validation, and funding source balance adjustments.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import init_db, get_connection
from app.categories import create_category
from app.transactions import add_transaction, get_transaction, update_transaction, category_spent_this_month
from app import budget_logic

TEST_DB = PROJECT_ROOT / "test" / "test_edit.db"

def setup_test_environment():
    if TEST_DB.exists():
        TEST_DB.unlink()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    init_db(TEST_DB)

def run_tests():
    setup_test_environment()
    print("Testing Feature 3: Transaction In-Place Edit...")

    cat_id = create_category("Dining", 1000.0, 1500.0, db_path=TEST_DB)

    # 1. Add normal transaction
    txn_id = add_transaction(
        txn_date="2026-09-04",
        amount=400.0,
        type="expense",
        category_id=cat_id,
        description="Quick snack",
        db_path=TEST_DB
    )

    txn = get_transaction(txn_id, db_path=TEST_DB)
    assert txn is not None, "get_transaction should return the added transaction"
    assert txn["amount"] == 400.0
    assert txn["description"] == "Quick snack"

    # 2. Update transaction fields (amount, description, date)
    update_transaction(
        txn_id,
        amount=650.0,
        description="Family dinner",
        txn_date="2026-09-05",
        db_path=TEST_DB
    )

    updated_txn = get_transaction(txn_id, db_path=TEST_DB)
    assert updated_txn["amount"] == 650.0, f"Expected 650.0, got {updated_txn['amount']}"
    assert updated_txn["description"] == "Family dinner"
    assert updated_txn["date"] == "2026-09-05"

    spent = category_spent_this_month(cat_id, "2026-09", db_path=TEST_DB)
    assert spent == 650.0, f"Expected category spent 650.0, got {spent}"

    # 3. Test Funding Source Overflows and Reversals on Edit
    # Hard limit is 1500. Currently spent: 650. Remaining limit: 850.
    # Adding an expense of 1000 with funding_source="savings" means 150 is overflow from savings.
    txn2_id = add_transaction(
        txn_date="2026-09-06",
        amount=1000.0,
        type="expense",
        category_id=cat_id,
        description="Party Catering",
        funding_source="savings",
        db_path=TEST_DB
    )

    conn = get_connection(TEST_DB)
    sav_row = conn.execute("SELECT rollover_amount FROM savings WHERE month = '2026-09'").fetchone()
    conn.close()
    assert sav_row is not None, "Savings row should be created for overflow"
    assert sav_row["rollover_amount"] == -150.0, f"Expected savings -150.0, got {sav_row['rollover_amount']}"

    # Now edit txn2 to amount=800 (which is within the 850 remaining limit).
    # The 150 overflow should be refunded!
    update_transaction(
        txn2_id,
        amount=800.0,
        funding_source="savings",
        db_path=TEST_DB
    )

    conn = get_connection(TEST_DB)
    sav_row2 = conn.execute("SELECT rollover_amount FROM savings WHERE month = '2026-09'").fetchone()
    conn.close()
    assert sav_row2["rollover_amount"] == 0.0, f"Expected savings 0.0 after refund, got {sav_row2['rollover_amount']}"

    print("✅ Feature 3 tests passed successfully!")

    if TEST_DB.exists():
        TEST_DB.unlink()

if __name__ == "__main__":
    run_tests()
