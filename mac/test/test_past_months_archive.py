"""
test/test_past_months_archive.py

Validates the past months review, archive ledger, and time-machine mode.
"""

import sys
import os
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import init_db, get_connection
from app.categories import create_category
from app.transactions import add_transaction
from app import budget_logic

TEST_DB = PROJECT_ROOT / "test" / "test_archive.db"

def setup_test_environment():
    if TEST_DB.exists():
        TEST_DB.unlink()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    init_db(TEST_DB)

def run_tests():
    setup_test_environment()
    print("Testing Feature 2: Past Months Archive & Time Machine Mode...")

    # 1. Create categories
    cat_food_id = create_category("Food", 5000.0, 8000.0, db_path=TEST_DB)
    cat_rent_id = create_category("Rent", 15000.0, 15000.0, db_path=TEST_DB)

    # 2. Add income and expenses in July 2026
    add_transaction(txn_date="2026-07-01", amount=50000.0, type="income", description="Salary July", db_path=TEST_DB)
    add_transaction(txn_date="2026-07-05", amount=15000.0, type="expense", category_id=cat_rent_id, description="Rent July", db_path=TEST_DB)
    add_transaction(txn_date="2026-07-15", amount=4200.0, type="expense", category_id=cat_food_id, description="Food July", db_path=TEST_DB)

    # 3. Add income and expenses in August 2026
    add_transaction(txn_date="2026-08-01", amount=55000.0, type="income", description="Salary August", db_path=TEST_DB)
    add_transaction(txn_date="2026-08-05", amount=15000.0, type="expense", category_id=cat_rent_id, description="Rent August", db_path=TEST_DB)
    add_transaction(txn_date="2026-08-20", amount=6800.0, type="expense", category_id=cat_food_id, description="Food August", db_path=TEST_DB)

    # 4. Add transactions in September 2026 (current month)
    add_transaction(txn_date="2026-09-01", amount=60000.0, type="income", description="Salary Sept", db_path=TEST_DB)
    add_transaction(txn_date="2026-09-03", amount=15000.0, type="expense", category_id=cat_rent_id, description="Rent Sept", db_path=TEST_DB)

    # 5. Run rollover for July and August
    rollover_jul = budget_logic.run_month_end_rollover("2026-07", db_path=TEST_DB)
    assert rollover_jul["month"] == "2026-07"

    rollover_aug = budget_logic.run_month_end_rollover("2026-08", db_path=TEST_DB)
    assert rollover_aug["month"] == "2026-08"

    # 6. Test get_available_months
    avail_months = budget_logic.get_available_months(db_path=TEST_DB)
    assert "2026-07" in avail_months, "2026-07 should be in available months"
    assert "2026-08" in avail_months, "2026-08 should be in available months"
    # Ensure descending order
    for i in range(len(avail_months) - 1):
        assert avail_months[i] >= avail_months[i+1], f"Months not sorted descending: {avail_months}"

    # 7. Test get_closed_months_ledger
    ledger = budget_logic.get_closed_months_ledger(db_path=TEST_DB)
    assert len(ledger) == 2, f"Expected 2 closed months in ledger, got {len(ledger)}"
    
    aug_entry = next((item for item in ledger if item["month"] == "2026-08"), None)
    assert aug_entry is not None, "August entry should be present in ledger"
    assert aug_entry["total_income"] == 55000.0, f"Expected 55000 income in August, got {aug_entry['total_income']}"
    assert aug_entry["total_spent"] == 21800.0, f"Expected 21800 spent in August, got {aug_entry['total_spent']}"

    jul_entry = next((item for item in ledger if item["month"] == "2026-07"), None)
    assert jul_entry is not None, "July entry should be present in ledger"
    assert jul_entry["total_income"] == 50000.0
    assert jul_entry["total_spent"] == 19200.0

    # 8. Test dashboard_summary for archived past month vs current month
    summary_aug = budget_logic.dashboard_summary(month="2026-08", db_path=TEST_DB)
    assert summary_aug["is_closed"] is True, "August should be marked as closed"
    assert summary_aug["month"] == "2026-08"
    assert summary_aug["total_income"] == 55000.0
    assert summary_aug["total_spent"] == 21800.0

    summary_curr = budget_logic.dashboard_summary(month="2026-09", db_path=TEST_DB)
    assert summary_curr["is_closed"] is False, "September should not be marked as closed"
    assert summary_curr["total_income"] == 60000.0
    assert summary_curr["total_spent"] == 15000.0

    print("✅ Feature 2 tests passed successfully!")

    if TEST_DB.exists():
        TEST_DB.unlink()

if __name__ == "__main__":
    run_tests()
