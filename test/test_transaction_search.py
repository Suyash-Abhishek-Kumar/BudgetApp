"""
test/test_transaction_search.py

Validates text search filtering and date range filtering in list_transactions.
"""

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import init_db
from app.categories import create_category
from app.transactions import add_transaction, list_transactions

TEST_DB = PROJECT_ROOT / "test" / "test_search.db"

def setup_test_environment():
    if TEST_DB.exists():
        TEST_DB.unlink()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    init_db(TEST_DB)

def run_tests():
    setup_test_environment()
    print("Testing Feature 4: Live Text Search & Date Range Filters...")

    cat_id = create_category("General", 20000.0, 30000.0, db_path=TEST_DB)

    # 1. Seed transactions
    add_transaction(txn_date="2026-09-02", amount=450.0, type="expense", category_id=cat_id, description="Swiggy dinner order", db_path=TEST_DB)
    add_transaction(txn_date="2026-08-15", amount=649.0, type="expense", category_id=cat_id, description="Netflix subscription", db_path=TEST_DB)
    add_transaction(txn_date="2026-08-28", amount=12999.0, type="expense", category_id=cat_id, description="Amazon electronics purchase", db_path=TEST_DB)
    add_transaction(txn_date="2026-09-10", amount=1200.0, type="expense", category_id=cat_id, description="Grocery store run", db_path=TEST_DB)

    # 2. Test text search by description
    res_swiggy = list_transactions(search_query="Swiggy", db_path=TEST_DB)
    assert len(res_swiggy) == 1, f"Expected 1 Swiggy txn, got {len(res_swiggy)}"
    assert res_swiggy[0]["description"] == "Swiggy dinner order"

    res_amazon = list_transactions(search_query="amazon", db_path=TEST_DB)  # case-insensitive search
    assert len(res_amazon) == 1, f"Expected 1 Amazon txn, got {len(res_amazon)}"

    # 3. Test text search by amount
    res_amt = list_transactions(search_query="649", db_path=TEST_DB)
    assert len(res_amt) == 1, f"Expected 1 txn matching 649, got {len(res_amt)}"
    assert res_amt[0]["description"] == "Netflix subscription"

    # 4. Test nonexistent search
    res_none = list_transactions(search_query="Unicorn", db_path=TEST_DB)
    assert len(res_none) == 0, f"Expected 0 results, got {len(res_none)}"

    # 5. Test date ranges
    res_sept = list_transactions(start_date="2026-09-01", end_date="2026-09-30", db_path=TEST_DB)
    assert len(res_sept) == 2, f"Expected 2 September txns, got {len(res_sept)}"

    res_aug = list_transactions(start_date="2026-08-01", end_date="2026-08-31", db_path=TEST_DB)
    assert len(res_aug) == 2, f"Expected 2 August txns, got {len(res_aug)}"

    # 6. Combined filter (date range + search)
    res_comb = list_transactions(start_date="2026-09-01", end_date="2026-09-30", search_query="Grocery", db_path=TEST_DB)
    assert len(res_comb) == 1, f"Expected 1 combined result, got {len(res_comb)}"
    assert res_comb[0]["description"] == "Grocery store run"

    print("✅ Feature 4 tests passed successfully!")

    if TEST_DB.exists():
        TEST_DB.unlink()

if __name__ == "__main__":
    run_tests()
