"""
test/test_desktop_polish.py — Automated test suite for Feature 10:
Desktop Polish (Automated Backups, Privacy Mode Masking, and Keyboard Shortcuts).
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import backup as backup_api
from app.db import init_db
from app import categories, transactions, savings_goals


class TestDesktopPolish(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_budget.db"
        self.backup_dir = Path(self.temp_dir.name) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        init_db(self.db_path)
        # Populate initial test data
        self.cat_id = categories.create_category("Groceries", 2000, 3000, db_path=self.db_path)
        transactions.add_transaction(
            amount=450.0,
            type="expense",
            category_id=self.cat_id,
            description="Weekly veggies",
            db_path=self.db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    # -------------------------------------------------------------
    # 1. Backups Engine Tests
    # -------------------------------------------------------------
    def test_backup_create_list_restore_delete(self):
        """Test full backup lifecycle: creation, listing, restore, and deletion."""
        # 1. Create backup
        backup_file = backup_api.create_backup(db_path=self.db_path, backup_dir=self.backup_dir)
        self.assertTrue(backup_file.exists())
        self.assertTrue(backup_file.name.startswith("budget_backup_"))
        self.assertTrue(backup_file.name.endswith(".db"))

        # 2. List backups
        backups = backup_api.list_backups(backup_dir=self.backup_dir)
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["filename"], backup_file.name)
        self.assertGreater(backups[0]["size_kb"], 0)

        # 3. Mutate live database
        transactions.add_transaction(
            amount=999.0,
            type="expense",
            category_id=self.cat_id,
            description="Accidental purchase to revert",
            db_path=self.db_path
        )
        txs_after_mutation = transactions.list_transactions(db_path=self.db_path)
        self.assertEqual(len(txs_after_mutation), 2)

        # 4. Restore backup
        backup_api.restore_backup(backup_file, target_db_path=self.db_path)
        txs_after_restore = transactions.list_transactions(db_path=self.db_path)
        self.assertEqual(len(txs_after_restore), 1)
        self.assertEqual(txs_after_restore[0]["amount"], 450.0)

        # 5. Delete backup
        backup_api.delete_backup(backup_file)
        backups_remaining = backup_api.list_backups(backup_dir=self.backup_dir)
        self.assertEqual(len(backups_remaining), 0)

    def test_auto_backup_on_startup(self):
        """Test daily automated backup logic does not redundantly duplicate."""
        # First call creates a backup
        first_backup = backup_api.auto_backup_on_startup(db_path=self.db_path)
        # Note: default backup dir will be used; check that a backup was returned or exists
        if first_backup:
            self.assertTrue(Path(first_backup).exists())
            # Second call on same day should be skipped
            second_call = backup_api.auto_backup_on_startup(db_path=self.db_path)
            self.assertIsNone(second_call)
            # Clean up the test backup file
            backup_api.delete_backup(first_backup)

    # -------------------------------------------------------------
    # 2. Privacy Mode UI Masking Tests
    # -------------------------------------------------------------
    def test_privacy_mode_masking(self):
        """Test that setting privacy mode masks sensitive monetary amounts across UI screens."""
        import customtkinter as ctk
        from ui.dashboard_screen import DashboardScreen
        from ui.transaction_list_screen import TransactionListScreen
        from ui.savings_goals_screen import SavingsGoalsScreen

        root = ctk.CTk()
        root.withdraw()  # Headless

        try:
            # 1. Dashboard Screen Privacy Masking
            dash = DashboardScreen(root, self.db_path)
            # By default privacy is OFF
            self.assertFalse(dash.is_privacy_mode)
            dash.set_privacy_mode(True)
            self.assertTrue(dash.is_privacy_mode)
            # Summary stat cards should show masked text
            for card in (dash.available_card, dash.income_card, dash.spent_card, dash.savings_card, dash.ef_card):
                val_text = card.value_label.cget("text")
                self.assertIn("••••••", val_text)

            dash.set_privacy_mode(False)
            self.assertFalse(dash.is_privacy_mode)
            for card in (dash.available_card, dash.income_card, dash.spent_card, dash.savings_card, dash.ef_card):
                val_text = card.value_label.cget("text")
                self.assertNotIn("••••••", val_text)

            # 2. Transaction List Screen Privacy Masking
            tx_screen = TransactionListScreen(root, self.db_path)
            tx_screen.set_privacy_mode(True)
            self.assertTrue(tx_screen.is_privacy_mode)
            children = tx_screen.tree.get_children()
            self.assertGreater(len(children), 0)
            for item in children:
                row_vals = tx_screen.tree.item(item)["values"]
                self.assertEqual(row_vals[3], "••••••")

            # 3. Savings Goals Screen Privacy Masking
            goals_screen = SavingsGoalsScreen(root, self.db_path)
            savings_goals.create_goal(
                name="New Laptop",
                target_amount=80000,
                initial_saved=15000,
                db_path=self.db_path
            )
            goals_screen.set_privacy_mode(True)
            self.assertTrue(goals_screen.is_privacy_mode)
            self.assertEqual(goals_screen.card_total_saved.val_lbl.cget("text"), "₹ ••••••")
            self.assertEqual(goals_screen.card_total_target.val_lbl.cget("text"), "₹ ••••••")

        finally:
            root.destroy()

    # -------------------------------------------------------------
    # 3. Keyboard Shortcuts & Main Navigation Tests
    # -------------------------------------------------------------
    def test_main_app_shortcuts_and_privacy_toggle(self):
        """Test BudgetApp shortcuts dispatch and privacy mode toggling."""
        from main import BudgetApp

        with patch("main.DB_PATH", self.db_path):
            app = BudgetApp()
            app.withdraw()

            try:
                self.assertFalse(app.is_privacy_mode)
                self.assertEqual(app.privacy_btn.cget("text"), "👁️ Hide Amounts")

                # Toggle privacy mode
                app.toggle_privacy_mode()
                self.assertTrue(app.is_privacy_mode)
                self.assertEqual(app.privacy_btn.cget("text"), "🔒 Privacy: ON")

                # Verify screens received the privacy update
                self.assertTrue(app.screens["Dashboard"].is_privacy_mode)
                self.assertTrue(app.screens["Transactions"].is_privacy_mode)
                self.assertTrue(app.screens["Savings Goals"].is_privacy_mode)

                # Toggle back
                app.toggle_privacy_mode()
                self.assertFalse(app.is_privacy_mode)
                self.assertEqual(app.privacy_btn.cget("text"), "👁️ Hide Amounts")

                # Test screen navigation via shortcut callback
                app._on_switch_screen("Add Transaction")
                self.assertEqual(app.nav_buttons["Add Transaction"].cget("text_color"), "white")

                app._on_switch_screen("Savings Goals")
                self.assertEqual(app.nav_buttons["Savings Goals"].cget("text_color"), "white")

                # Test shortcut helper actions
                app._on_shortcut_new_transaction()
                # Should have switched to Add Transaction
                self.assertEqual(app.nav_buttons["Add Transaction"].cget("text_color"), "white")

                app._on_shortcut_find_transactions()
                # Should have switched to Transactions
                self.assertEqual(app.nav_buttons["Transactions"].cget("text_color"), "white")

            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
