"""
test/test_user_reported_fixes.py — Automated verification test for the 4 issues reported by user:
1. Pace & projection line chart hover tooltip visibility and formatting.
2. 6-month historical trend chart category filtering from pie slice clicks.
3. Recurring expenses spawning pending_approval transactions when due, and approving them.
4. Past month's expenses line chart updating properly with historical actuals instead of staying flat at 0.
"""

import sys
import unittest
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date
from unittest.mock import patch

from app.db import init_db
from app import categories, transactions, recurring, budget_logic
import customtkinter as ctk
from ui.dashboard_screen import DashboardScreen
from ui.transaction_list_screen import TransactionListScreen


class TestUserReportedFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Disable CTk scaling tracker background polling to avoid Tk destruction collisions
        cls._dpi_patch = patch.object(ctk.ScalingTracker, "check_dpi_scaling", lambda *args, **kwargs: None)
        cls._dpi_patch.start()
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        finally:
            cls._dpi_patch.stop()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_budget.db"
        init_db(self.db_path)

        # Create categories
        self.cat_food = categories.create_category("Food", 2000, 3000, db_path=self.db_path)
        self.cat_rent = categories.create_category("Rent", 15000, 15000, db_path=self.db_path)

        # Add income and expenses in a past month (e.g. 2026-08)
        transactions.add_transaction(
            amount=30000.0,
            type="income",
            txn_date="2026-08-01",
            db_path=self.db_path
        )
        transactions.add_transaction(
            amount=15000.0,
            type="expense",
            category_id=self.cat_rent,
            description="August Rent",
            txn_date="2026-08-05",
            db_path=self.db_path
        )
        transactions.add_transaction(
            amount=1200.0,
            type="expense",
            category_id=self.cat_food,
            description="August Groceries",
            txn_date="2026-08-20",
            db_path=self.db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_past_month_chart_updates_with_actual_expenses(self):
        """Issue 4: Viewing past month updates pace chart with actual spending, not staying flat at 0."""
        dash = DashboardScreen(self.root, self.db_path)
        dash.pack(fill="both", expand=True)
        self.root.update()

        try:
            # Switch to past month 2026-08
            dash.set_active_month("2026-08")
            self.root.update()

            lines = dash.pace_ax.get_lines()
            actual_lines = [l for l in lines if l.get_label() == "Actual"]
            self.assertEqual(len(actual_lines), 1, "Pace chart must have an 'Actual' line plotted")

            actual_line = actual_lines[0]
            y_data = list(actual_line.get_ydata())
            # Cumulative total by end of month must reach 16200.0 (15000 rent + 1200 food)
            self.assertEqual(max(y_data), 16200.0)
            self.assertEqual(len(y_data), 31)
            print("✓ Issue 4 Verified: Past month line chart properly updates with actual spending curve.")
        finally:
            dash.destroy()

    def test_pace_chart_hover_shows_tooltip(self):
        """Issue 1: Hovering over line chart displays the date and spend tooltip."""
        dash = DashboardScreen(self.root, self.db_path)
        dash.pack(fill="both", expand=True)
        dash.set_active_month("2026-08")
        self.root.update()

        try:
            # Simulate mouse hover over Day 20 (where groceries were bought)
            pt_disp = dash.pace_ax.transData.transform((20, 16200.0))
            widget = dash.pace_canvas.get_tk_widget()
            buf_w, buf_h = dash.pace_fig.canvas.get_width_height()
            win_w = widget.winfo_width() or 250
            win_h = widget.winfo_height() or 200

            tk_x = pt_disp[0] * win_w / buf_w
            tk_y = win_h - (pt_disp[1] * win_h / buf_h)

            class MockEvent:
                x = tk_x
                y = tk_y

            dash._on_pace_hover(MockEvent())

            self.assertTrue(dash.pace_annotation.get_visible(), "Pace annotation should become visible on hover")
            text = dash.pace_annotation.get_text()
            self.assertIn("2026", text)
            self.assertIn("16,200.00", text)
            print("✓ Issue 1 Verified: Hovering over line chart displays accurate tooltip and marker.")
        finally:
            dash.destroy()

    def test_pie_chart_click_filters_trend_chart(self):
        """Issue 2: Selecting a slice from the pie chart updates the 6-month historical trend chart."""
        dash = DashboardScreen(self.root, self.db_path)
        dash.pack(fill="both", expand=True)
        dash.set_active_month("2026-08")
        self.root.update()

        try:
            # Filter by Rent slice
            dash._apply_category_filter("Rent")
            self.assertEqual(dash.selected_category_id, self.cat_rent)
            self.assertEqual(dash.selected_category_name, "Rent")
            self.assertIn("Filtering trend by: Rent", dash.filter_lbl.cget("text"))

            # Check that trend chart now displays Category Spent for Rent
            trend_lines = [l for l in dash.trend_ax.get_lines() if l.get_label() == "Category Spent"]
            self.assertEqual(len(trend_lines), 1)
            y_data = list(trend_lines[0].get_ydata())
            # Month 2026-08 had 15000 rent
            self.assertIn(15000.0, y_data)

            # Test reset
            dash.reset_category_trend()
            self.assertIsNone(dash.selected_category_id)
            print("✓ Issue 2 Verified: Pie slice selection successfully filters 6-month historical chart.")
        finally:
            dash.destroy()

    def test_recurring_expenses_spawn_pending_transactions(self):
        """Issue 3: Due recurring expenses spawn pending_approval transactions, and approve succeeds."""
        # Create recurring rule due in the past
        rule_id = recurring.create_rule(
            category_id=self.cat_food,
            amount=550.0,
            description="Weekly Meal Subscription",
            rule_type="expense",
            frequency="daily",
            next_due_date="2026-09-01",
            db_path=self.db_path
        )

        # Process due recurring transactions up to 2026-09-03
        created = recurring.process_due_recurring_transactions(target_date="2026-09-03", db_path=self.db_path)
        self.assertGreater(len(created), 0, "Recurring rule must create pending transactions")

        # Verify transactions are in pending_approval status
        pending_txs = transactions.list_transactions(status="pending_approval", db_path=self.db_path)
        self.assertEqual(len(pending_txs), len(created))
        first_pending = pending_txs[0]
        self.assertEqual(first_pending["status"], "pending_approval")
        self.assertEqual(first_pending["recurring_id"], rule_id)
        self.assertEqual(first_pending["amount"], 550.0)

        # Test approving transaction in TransactionListScreen
        tx_screen = TransactionListScreen(self.root, self.db_path)
        try:
            tx_screen.refresh()

            # Verify badge in status label
            self.assertIn("pending approval", tx_screen.status_label.cget("text"))

            # Approve the first pending transaction
            transactions.approve_transaction(first_pending["id"], db_path=self.db_path)
            approved = transactions.get_transaction(first_pending["id"], db_path=self.db_path)
            self.assertEqual(approved["status"], "confirmed")
            print("✓ Issue 3 Verified: Due recurring expenses generate pending_approval transactions and can be approved.")
        finally:
            tx_screen.destroy()


if __name__ == "__main__":
    unittest.main()
