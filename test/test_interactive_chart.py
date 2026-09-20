"""
test/test_interactive_chart.py

Validates the data structures and calculations required for the interactive
month expenses line graph and trend chart hover features.
"""

import sys
import os
from pathlib import Path
from datetime import date

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db import init_db, get_connection
from app.categories import create_category
from app.transactions import add_transaction
from app import budget_logic

TEST_DB = PROJECT_ROOT / "test" / "test_chart.db"

def setup_test_environment():
    if TEST_DB.exists():
        TEST_DB.unlink()
    TEST_DB.parent.mkdir(parents=True, exist_ok=True)
    init_db(TEST_DB)

def run_tests():
    setup_test_environment()
    print("Testing Feature 1: Interactive Line Charts Data Structures...")

    # 1. Create test categories
    cat_food_id = create_category("Food", 5000.0, 8000.0, db_path=TEST_DB)
    cat_tech_id = create_category("Electronics", 10000.0, 15000.0, db_path=TEST_DB)

    # 2. Add transactions across days in September 2026
    add_transaction(txn_date="2026-09-02", amount=450.0, type="expense", category_id=cat_food_id, description="Groceries", db_path=TEST_DB)
    add_transaction(txn_date="2026-09-02", amount=150.0, type="expense", category_id=cat_food_id, description="Snacks", db_path=TEST_DB)
    add_transaction(txn_date="2026-09-05", amount=2500.0, type="expense", category_id=cat_tech_id, description="Headphones", db_path=TEST_DB)
    add_transaction(txn_date="2026-09-10", amount=800.0, type="expense", category_id=cat_food_id, description="Dinner", db_path=TEST_DB)

    # 3. Test month_end_projection
    proj_data = budget_logic.month_end_projection(month="2026-09", db_path=TEST_DB)
    
    assert "actual" in proj_data, "Missing 'actual' data in projection"
    assert "projection" in proj_data, "Missing 'projection' data in projection"
    assert proj_data["month"] == "2026-09"
    assert proj_data["days_in_month"] == 30

    actual = proj_data["actual"]
    assert len(actual) > 0, "Actual data should not be empty"

    # Check Day 2 data
    day2_items = [d for d in actual if d["day"] == 2]
    assert len(day2_items) == 1, "Day 2 should exist in actual data"
    day2 = day2_items[0]
    assert day2["daily_spent"] == 600.0, f"Expected 600.0 on Day 2, got {day2['daily_spent']}"
    assert day2["cumulative_spent"] == 600.0, f"Expected cumulative 600.0 on Day 2, got {day2['cumulative_spent']}"
    assert day2["date"] == "2026-09-02", f"Expected date 2026-09-02, got {day2['date']}"

    # Check Day 5 data
    day5_items = [d for d in actual if d["day"] == 5]
    assert len(day5_items) == 1, "Day 5 should exist in actual data"
    day5 = day5_items[0]
    assert day5["daily_spent"] == 2500.0, f"Expected 2500.0 on Day 5, got {day5['daily_spent']}"
    assert day5["cumulative_spent"] == 3100.0, f"Expected cumulative 3100.0 on Day 5, got {day5['cumulative_spent']}"
    assert day5["date"] == "2026-09-05", f"Expected date 2026-09-05, got {day5['date']}"

    # Check Day 10 data
    day10_items = [d for d in actual if d["day"] == 10]
    assert len(day10_items) == 1, "Day 10 should exist in actual data"
    day10 = day10_items[0]
    assert day10["daily_spent"] == 800.0, f"Expected 800.0 on Day 10, got {day10['daily_spent']}"
    assert day10["cumulative_spent"] == 3900.0, f"Expected cumulative 3900.0 on Day 10, got {day10['cumulative_spent']}"

    # Check date formatting capability
    test_d = date(2026, 9, 2).strftime("%a, %d %b %Y")
    assert test_d == "Wed, 02 Sep 2026", f"Unexpected formatted date: {test_d}"

    # 4. Check projection points
    projection = proj_data["projection"]
    assert len(projection) > 0, "Projection points should exist"
    for p in projection:
        assert "day" in p
        assert "date" in p
        assert "projected_cumulative" in p

    # 5. Check historical trend data
    trend = budget_logic.get_historical_trend(months_count=6, db_path=TEST_DB)
    assert len(trend) == 6, f"Expected 6 trend points, got {len(trend)}"
    sep_trend = [t for t in trend if t["month"] == "2026-09"]
    assert len(sep_trend) == 1
    assert sep_trend[0]["spent"] == 3900.0, f"Expected September spent 3900.0, got {sep_trend[0]['spent']}"

    print("✅ Feature 1 tests passed successfully!")

    # Clean up test db
    if TEST_DB.exists():
        TEST_DB.unlink()

if __name__ == "__main__":
    run_tests()
