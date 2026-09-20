"""
test/test_savings_goals.py

Validates Feature 8: Dedicated Named Savings Goals.
- Tests backend CRUD: create_goal, update_goal, delete_goal, adjust_goal_saved, goals_summary.
- Tests progress % calculation, days_left estimation, and auto-completion flag.
- Tests error handling: empty name, negative target, overdraw withdrawal.
- Tests headless UI: SavingsGoalsScreen, GoalFormDialog, GoalDepositWithdrawDialog.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db
from app import savings_goals as goals_api


def run_test():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_budget.db"
        init_db(db_path)

        # 1. Create a goal: "MacBook Pro M3", target 150000, initial 30000
        gid1 = goals_api.create_goal(
            name="MacBook Pro M3",
            target_amount=150000.0,
            target_date="2026-12-31",
            initial_saved=30000.0,
            db_path=db_path
        )
        assert gid1 is not None and gid1 > 0

        g1 = goals_api.get_goal(gid1, db_path=db_path)
        assert g1["name"] == "MacBook Pro M3"
        assert g1["target_amount"] == 150000.0
        assert g1["saved_amount"] == 30000.0
        assert g1["pct"] == 20.0
        assert g1["remaining"] == 120000.0
        assert g1["is_completed"] == 0
        assert g1["days_left"] is not None
        print("✓ Savings goal creation and enrichment passed.")

        # 2. Deposit 50,000 into goal
        new_bal = goals_api.adjust_goal_saved(gid1, 50000.0, db_path=db_path)
        assert new_bal == 80000.0
        g1_updated = goals_api.get_goal(gid1, db_path=db_path)
        assert g1_updated["saved_amount"] == 80000.0
        assert round(g1_updated["pct"], 1) == 53.3

        # 3. Withdraw 10,000
        new_bal = goals_api.adjust_goal_saved(gid1, -10000.0, db_path=db_path)
        assert new_bal == 70000.0

        # 4. Deposit enough to complete the goal
        new_bal = goals_api.adjust_goal_saved(gid1, 90000.0, db_path=db_path)
        assert new_bal == 160000.0
        g1_done = goals_api.get_goal(gid1, db_path=db_path)
        assert g1_done["is_completed"] == 1
        assert g1_done["pct"] == 100.0
        assert g1_done["remaining"] == 0.0
        print("✓ Goal deposits, withdrawals, and completion trigger passed.")

        # 5. Test error validations
        # Overdrawn withdrawal (saved is 160000, try to withdraw 200000)
        try:
            goals_api.adjust_goal_saved(gid1, -200000.0, db_path=db_path)
            assert False, "Should fail on overdrawn withdrawal"
        except ValueError as e:
            assert "cannot withdraw" in str(e).lower()

        # Empty name
        try:
            goals_api.create_goal("", 1000.0, db_path=db_path)
            assert False, "Should fail on empty name"
        except ValueError as e:
            assert "empty" in str(e).lower()

        # Negative target
        try:
            goals_api.create_goal("Test", -500.0, db_path=db_path)
            assert False, "Should fail on negative target"
        except ValueError as e:
            assert "positive" in str(e).lower()
        print("✓ Goal error handling passed.")

        # 6. Test goals_summary
        gid2 = goals_api.create_goal("Emergency Fund Boost", 50000.0, initial_saved=10000.0, db_path=db_path)
        summary = goals_api.goals_summary(db_path=db_path)
        assert summary["total_target"] == 200000.0  # 150000 + 50000
        assert summary["total_saved"] == 170000.0   # 160000 + 10000
        assert summary["active_count"] == 1
        assert summary["completed_count"] == 1
        print("✓ Goals summary calculation passed.")

        # 7. Test Headless UI Screen and Dialogs
        try:
            import customtkinter as ctk
            from unittest.mock import patch
            from ui.savings_goals_screen import SavingsGoalsScreen, GoalFormDialog, GoalDepositWithdrawDialog
            from main import BudgetApp

            root = ctk.CTk()
            root.withdraw()

            # Test SavingsGoalsScreen
            screen = SavingsGoalsScreen(root, db_path=db_path)
            screen.refresh()
            assert len(screen.goals_scroll.winfo_children()) == 2, "Should render 2 goal cards"

            # Test GoalFormDialog
            form = GoalFormDialog(root, db_path=db_path)
            form.name_var.set("Trip to Goa")
            form.target_var.set("25000")
            form.saved_var.set("5000")
            form._save()

            assert len(goals_api.list_goals(db_path=db_path)) == 3

            # Test GoalDepositWithdrawDialog
            g_goa = [g for g in goals_api.list_goals(db_path=db_path) if g["name"] == "Trip to Goa"][0]
            dep_dialog = GoalDepositWithdrawDialog(root, goal=g_goa, db_path=db_path)
            dep_dialog.amount_var.set("10000")
            with patch("tkinter.messagebox.showinfo"):
                dep_dialog._confirm()

            g_goa_after = goals_api.get_goal(g_goa["id"], db_path=db_path)
            assert g_goa_after["saved_amount"] == 15000.0

            root.destroy()
            print("✓ Headless UI SavingsGoalsScreen & dialogs validated successfully.")
        except Exception as e:
            if "no display name" in str(e).lower() or "display" in str(e).lower():
                print("Skipping GUI render due to headless environment:", e)
            else:
                raise e

    print("ALL SAVINGS GOALS TESTS PASSED!")


if __name__ == "__main__":
    run_test()
