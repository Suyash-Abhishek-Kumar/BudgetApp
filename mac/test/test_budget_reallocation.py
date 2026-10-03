"""
test/test_budget_reallocation.py

Validates Feature 6: Category Budget Reallocation ("Envelope Transfer").
- Tests backend transfer_category_budget: valid transfers, soft limit proportional scaling,
  and error handling for invalid amounts, same category, and overdrawn limits.
- Tests BudgetTransferDialog headless UI initialization and interaction.
"""

import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import init_db
from app import categories as categories_api
from app import transactions as transactions_api


def run_test():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_budget.db"
        init_db(db_path)

        # 1. Setup categories
        # Groceries: Soft 4000, Hard 5000
        # Dining Out: Soft 2000, Hard 2500
        cat_groceries = categories_api.create_category("Groceries", soft_limit=4000.0, hard_limit=5000.0, db_path=db_path)
        cat_dining = categories_api.create_category("Dining Out", soft_limit=2000.0, hard_limit=2500.0, db_path=db_path)

        # 2. Test successful transfer of 1000 from Groceries to Dining Out
        res = categories_api.transfer_category_budget(cat_groceries, cat_dining, 1000.0, adjust_soft=True, db_path=db_path)
        assert res["amount"] == 1000.0
        assert res["from_cat"]["new_hard"] == 4000.0
        assert res["from_cat"]["new_soft"] == 3200.0  # 4000 * (4000/5000)
        assert res["to_cat"]["new_hard"] == 3500.0
        assert res["to_cat"]["new_soft"] == 2800.0  # 3500 * (2000/2500)

        # Verify in DB
        g_data = categories_api.get_category(cat_groceries, db_path=db_path)
        d_data = categories_api.get_category(cat_dining, db_path=db_path)
        assert g_data["hard_limit"] == 4000.0
        assert g_data["soft_limit"] == 3200.0
        assert d_data["hard_limit"] == 3500.0
        assert d_data["soft_limit"] == 2800.0
        print("✓ Category envelope transfer backend logic passed.")

        # 3. Test Error Handling
        # Transfer to self
        try:
            categories_api.transfer_category_budget(cat_groceries, cat_groceries, 500.0, db_path=db_path)
            assert False, "Should fail when source and destination are the same"
        except ValueError as e:
            assert "different" in str(e).lower()

        # Negative amount
        try:
            categories_api.transfer_category_budget(cat_groceries, cat_dining, -100.0, db_path=db_path)
            assert False, "Should fail when amount <= 0"
        except ValueError as e:
            assert "positive" in str(e).lower()

        # Exceeding source hard limit (current Groceries hard limit is 4000, attempt 5000)
        try:
            categories_api.transfer_category_budget(cat_groceries, cat_dining, 5000.0, db_path=db_path)
            assert False, "Should fail when amount exceeds source limit"
        except ValueError as e:
            assert "insufficient" in str(e).lower()
        print("✓ Category transfer error validations passed.")

        # 4. Test UI Component
        try:
            import customtkinter as ctk
            from ui.dashboard_screen import DashboardScreen, BudgetTransferDialog

            root = ctk.CTk()
            root.withdraw()

            # Test dialog initialization
            transferred_flag = []
            dialog = BudgetTransferDialog(
                root, db_path=db_path,
                on_transferred=lambda: transferred_flag.append(True)
            )
            assert len(dialog.categories) == 2

            # Explicitly select Groceries as from and Dining Out as to
            g_lbl = [lbl for lbl, c in dialog.cat_by_label.items() if c["id"] == cat_groceries][0]
            d_lbl = [lbl for lbl, c in dialog.cat_by_label.items() if c["id"] == cat_dining][0]
            dialog.from_var.set(g_lbl)
            dialog.to_var.set(d_lbl)

            # Test quick amount buttons
            dialog.amount_var.set("300")
            dialog._add_quick_amount(200)
            assert dialog.amount_var.get() == "500"

            from unittest.mock import patch
            with patch("tkinter.messagebox.showinfo"):
                dialog._do_transfer()
            assert len(transferred_flag) == 1, "Callback should have been triggered"

            # Check updated limits
            g_after = categories_api.get_category(cat_groceries, db_path=db_path)
            d_after = categories_api.get_category(cat_dining, db_path=db_path)
            assert g_after["hard_limit"] == 3500.0
            assert d_after["hard_limit"] == 4000.0

            # Test DashboardScreen initialization and transfer_btn existence
            dash = DashboardScreen(root, db_path=db_path)
            assert hasattr(dash, "transfer_btn")
            assert dash.transfer_btn.cget("state") == "normal"

            root.destroy()
            print("✓ Headless UI BudgetTransferDialog & DashboardScreen validated successfully.")
        except Exception as e:
            if "no display name" in str(e).lower() or "display" in str(e).lower():
                print("Skipping GUI render due to headless environment:", e)
            else:
                raise e

    print("ALL CATEGORY BUDGET REALLOCATION TESTS PASSED!")


if __name__ == "__main__":
    run_test()
