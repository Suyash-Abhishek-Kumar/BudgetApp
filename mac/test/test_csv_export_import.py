import os
import sys
import tempfile
import csv
from datetime import date
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

        # 1. Create categories
        groceries_id = categories_api.create_category("Groceries", soft_limit=4000.0, hard_limit=5000.0, db_path=db_path)
        salary_id = categories_api.create_category("Salary", db_path=db_path)

        # 2. Add some initial transactions
        t1 = transactions_api.add_transaction(
            amount=450.0,
            type="expense",
            category_id=groceries_id,
            txn_date="2026-09-10",
            description="Supermarket veggies",
            funding_source="regular",
            db_path=db_path
        )
        t2 = transactions_api.add_transaction(
            amount=30000.0,
            type="income",
            category_id=salary_id,
            txn_date="2026-09-01",
            description="Monthly stipend",
            funding_source="regular",
            db_path=db_path
        )

        # 3. Test CSV Export
        export_file = Path(tmpdir) / "exported.csv"
        count = transactions_api.export_transactions_csv(str(export_file), db_path=db_path)
        assert count == 2, f"Expected 2 exported transactions, got {count}"
        assert export_file.exists(), "Export file should exist"

        with open(export_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            exported_rows = list(reader)
        assert len(exported_rows) == 2, f"Expected 2 rows in exported CSV, got {len(exported_rows)}"
        assert "Date" in exported_rows[0]
        assert "Amount" in exported_rows[0]
        assert "Category" in exported_rows[0]
        print("✓ CSV Export passed successfully.")

        # 4. Test Bank Statement / Google Pay CSV Import
        # Simulate a Google Pay / UPI statement CSV
        gpay_csv = Path(tmpdir) / "gpay_statement.csv"
        with open(gpay_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Transaction Date", "Narration / Note", "Debit Amount", "Credit Amount", "Status"])
            writer.writerow(["12/09/2026", "Paid to Fresh Mart Groceries", "₹ 820.50", "", "SUCCESS"])
            writer.writerow(["13-Sep-2026", "Received from Client Freelance", "", "₹ 15,000.00", "SUCCESS"])
            writer.writerow(["14/09/2026", "Metro card recharge", "100.00", "", "SUCCESS"])
            writer.writerow(["", "", "", "", ""]) # empty row to test skipping

        # Test parse_csv_file
        parsed = transactions_api.parse_csv_file(str(gpay_csv), db_path=db_path)
        assert parsed["total_rows"] >= 3, f"Total rows expected >= 3, got {parsed['total_rows']}"
        assert parsed["valid_rows"] == 3, f"Valid rows expected 3, got {parsed['valid_rows']}"
        assert len(parsed["rows"]) == 3, f"Parsed rows expected 3, got {len(parsed['rows'])}"

        # Check column auto detection
        mapping = parsed["mapping"]
        assert mapping["date"].lower() == "transaction date", f"Detected date column: {mapping.get('date')}"
        assert mapping["description"].lower() == "narration / note", f"Detected desc column: {mapping.get('description')}"
        assert mapping["debit"].lower() == "debit amount", f"Detected debit column: {mapping.get('debit')}"
        assert mapping["credit"].lower() == "credit amount", f"Detected credit column: {mapping.get('credit')}"

        rows = parsed["rows"]
        # Row 0: Debit 820.50 on 2026-09-12
        assert rows[0]["type"] == "expense"
        assert abs(rows[0]["amount"] - 820.50) < 0.001
        assert rows[0]["date"] == "2026-09-12"
        assert "Groceries" in rows[0]["description"]
        # Category auto-mapping should match "Groceries"
        assert rows[0]["category_id"] == groceries_id

        # Row 1: Credit 15000.00 on 2026-09-13
        assert rows[1]["type"] == "income"
        assert abs(rows[1]["amount"] - 15000.00) < 0.001
        assert rows[1]["date"] == "2026-09-13"

        # 5. Import rows into DB
        imported_count = transactions_api.import_transactions_from_rows(rows, db_path=db_path)
        assert imported_count == 3, f"Expected 3 rows imported, got {imported_count}"

        # 6. Verify transactions in DB
        all_txns = transactions_api.list_transactions(db_path=db_path)
        assert len(all_txns) == 5, f"Total transactions should now be 5, got {len(all_txns)}"
        print("✓ Bank Statement / GPay Import parsed & committed successfully.")

        # 7. Test headless UI component construction
        try:
            import tkinter as tk
            import customtkinter as ctk
            from ui.transaction_list_screen import TransactionListScreen, CSVImportDialog

            root = ctk.CTk()
            root.withdraw()
            screen = TransactionListScreen(root, db_path=db_path)
            screen.refresh()
            assert len(screen.tree.get_children()) == 5, "UI treeview should show 5 transactions"

            dialog = CSVImportDialog(root, file_path=str(gpay_csv), db_path=db_path)
            assert dialog.parsed_data["valid_rows"] == 3
            dialog.destroy()
            root.destroy()
            print("✓ Headless UI components constructed and validated successfully.")
        except Exception as e:
            if "no display name" in str(e).lower() or "display" in str(e).lower():
                print("Skipping GUI render due to headless environment:", e)
            else:
                raise e

    print("ALL CSV EXPORT & IMPORT TESTS PASSED!")

if __name__ == "__main__":
    run_test()
