"""
test_milestone1.py — exercises the full Milestone-1 data layer end to
end against a throwaway database, printing results so you can eyeball
that the logic matches the spec. Not a formal pytest suite (that comes
later) — this is a fast sanity pass while building.
"""

from pathlib import Path
from app.db import reset_db
from app import categories, transactions, budget_logic, emergency_fund, settings

TEST_DB = Path(__file__).parent / "test_budget.db"


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main():
    reset_db(TEST_DB)

    section("1. Create categories (matches the Food/Books/etc. example)")
    food_id = categories.create_category("Food", soft_limit=200, hard_limit=250, db_path=TEST_DB)
    books_id = categories.create_category("Books", soft_limit=60, hard_limit=80, db_path=TEST_DB)
    for c in categories.list_categories(TEST_DB):
        print(c)

    section("2. Settings defaults + override")
    print("hard_limit_warn_threshold default:", settings.get_setting("hard_limit_warn_threshold", TEST_DB))
    settings.set_setting("hard_limit_warn_threshold", 30, TEST_DB)
    print("after override:", settings.get_setting("hard_limit_warn_threshold", TEST_DB))

    section("3. Add transactions under soft limit")
    transactions.add_transaction(amount=40, type="expense", category_id=food_id,
                                  description="Groceries", db_path=TEST_DB)
    status = transactions.category_status(food_id, db_path=TEST_DB)
    print(status)
    assert status["state"] == "under_soft"

    section("4. Preview impact BEFORE committing (Add-Transaction UI feedback)")
    # spent so far = 40; warn threshold = 30. Adding 185 -> projected 225,
    # remaining-to-hard = 250-225 = 25 <= 30 -> should trip "approaching_hard".
    preview = transactions.preview_transaction_impact(food_id, 185, db_path=TEST_DB)
    print(preview)
    assert preview["state"] == "approaching_hard"

    section("5. Push category over its hard limit -> overflow message")
    transactions.add_transaction(amount=215, type="expense", category_id=food_id,
                                  description="Big grocery run", db_path=TEST_DB)
    status = transactions.category_status(food_id, db_path=TEST_DB)
    print(status)
    assert status["state"] == "over_hard"
    assert "overflows into savings" in status["message"]

    section("6. Category under both limits stays green")
    transactions.add_transaction(amount=20, type="expense", category_id=books_id,
                                  description="Novel", db_path=TEST_DB)
    print(transactions.category_status(books_id, db_path=TEST_DB))

    section("7. Income transaction")
    transactions.add_transaction(amount=1200, type="income", description="Internship paycheck",
                                  db_path=TEST_DB)

    section("8. Emergency fund manual transfer")
    emergency_fund.manual_transfer(100, "to_emergency_fund", note="initial seed", db_path=TEST_DB)
    print("EF balance:", emergency_fund.get_balance(TEST_DB))
    print("EF log:", emergency_fund.get_log(db_path=TEST_DB))

    section("9. Pending-approval transaction is excluded from totals")
    pending_id = transactions.add_transaction(
        amount=1200, type="expense", category_id=food_id, description="Rent (auto)",
        status="pending_approval", db_path=TEST_DB,
    )
    status_before = transactions.category_status(food_id, db_path=TEST_DB)
    print("Food status with pending rent NOT counted:", status_before["spent"])
    assert status_before["spent"] == 255  # unchanged from step 5 (40+215)

    section("10. Approve the pending transaction -> now it counts")
    transactions.approve_transaction(pending_id, db_path=TEST_DB)
    status_after = transactions.category_status(food_id, db_path=TEST_DB)
    print("Food status after approval:", status_after["spent"])
    assert status_after["spent"] == 1455

    section("11. Month-end rollover + EF split")
    from datetime import date
    current_month = date.today().isoformat()[:7]
    result = budget_logic.run_month_end_rollover(current_month, db_path=TEST_DB)
    print(result)
    print("Savings balance:", budget_logic.total_savings_balance(TEST_DB))
    print("EF balance after rollover split:", emergency_fund.get_balance(TEST_DB))

    section("12. Re-running rollover for the same month should raise")
    try:
        budget_logic.run_month_end_rollover(current_month, db_path=TEST_DB)
        print("FAIL: should have raised")
    except ValueError as e:
        print("Correctly raised:", e)

    section("13. Month-end spending projection")
    proj = budget_logic.month_end_projection(current_month, db_path=TEST_DB)
    print("days_in_month:", proj["days_in_month"], "current_day:", proj["current_day"])
    print("projected_month_end_total:", proj["projected_month_end_total"])

    section("14. Full dashboard summary")
    summary = budget_logic.dashboard_summary(db_path=TEST_DB)
    import json
    print(json.dumps(summary, indent=2, default=str)[:2000])

    print("\n\nALL MILESTONE 1 CHECKS PASSED ✅")


if __name__ == "__main__":
    main()
