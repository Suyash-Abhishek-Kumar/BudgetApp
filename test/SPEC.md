# Test Suite Specification (`test/`)

The `test/` directory contains the automated test suites for **BudgetApp v2.0**. Each test file runs against an isolated, in-memory or throwaway SQLite database (`test_budget.db`) to ensure zero pollution of real user data.

---

## Directory Overview

```
test/
├── test_interactive_chart.py      # Spending pace line chart & hover tooltip unit tests
├── test_past_months_archive.py    # Historical archives, Time Machine mode, auto-rollovers
├── test_transaction_edit.py       # In-place transaction editing & limit recalculations
├── test_transaction_search.py     # Full-text search & date range preset filter tests
├── test_csv_export_import.py      # Bank statement CSV import & Excel CSV export tests
├── test_budget_reallocation.py    # Category envelope budget transfer tests
├── test_split_transactions.py     # Multi-category split transaction engine tests
├── test_savings_goals.py          # Named savings goals, deposits, withdrawals, and logs
├── test_ai_features.py            # Model discovery, financial context, audit, NLP parser
├── test_desktop_polish.py         # Daily backups, 7-day retention, privacy mode, shortcuts
└── test_user_reported_fixes.py    # Regression verification for interactive UI and data fixes
```

---

## File Specifications & Implemented Test Coverage

### 1. [`test/test_interactive_chart.py`](file:///Users/suyash/Downloads/budgetapp/test/test_interactive_chart.py)
- **Job**: Verifies the rendering math and event handling of the interactive spending pace line chart.
- **Tested Features**:
  - Daily cumulative spend calculation and projection curve generation.
  - Coordinate interpolation for snapping the vertical crosshair guide to the nearest calendar day.
  - Formatted tooltip text generation displaying day numbers, dates, and amounts without Matplotlib color tuple type errors.

---

### 2. [`test/test_past_months_archive.py`](file:///Users/suyash/Downloads/budgetapp/test/test_past_months_archive.py)
- **Job**: Validates historical financial review and Time Machine functionality.
- **Tested Features**:
  - Historical month discovery across transactions and closed month rollover records.
  - Metric isolation ensuring past months reflect accurate historical data rather than current balances.
  - Read-Only mode validation preventing transaction additions or edits while in Time Machine mode.
  - Startup silent auto-rollover processing for unclosed past months.

---

### 3. [`test/test_transaction_edit.py`](file:///Users/suyash/Downloads/budgetapp/test/test_transaction_edit.py)
- **Job**: Tests in-place modification of existing income and expense transactions.
- **Tested Features**:
  - Modifying transaction amounts, categories, descriptions, dates, and funding sources.
  - Verification that modifying amounts properly recalculates category spent amounts and envelope limit thresholds.
  - Validation that invalid inputs (e.g. negative amounts) are safely rejected.

---

### 4. [`test/test_transaction_search.py`](file:///Users/suyash/Downloads/budgetapp/test/test_transaction_search.py)
- **Job**: Validates full-text search and date range filtering capabilities.
- **Tested Features**:
  - Case-insensitive keyword matching across transaction descriptions and category names.
  - Date preset filtering ("This Month", "Last Month", "Last 30 Days", "Last 90 Days", "Custom Range").
  - Combined multi-criteria querying (e.g. search keyword + date range + transaction type).

---

### 5. [`test/test_csv_export_import.py`](file:///Users/suyash/Downloads/budgetapp/test/test_csv_export_import.py)
- **Job**: Verifies universal bank statement CSV importing and transaction CSV exporting.
- **Tested Features**:
  - Universal CSV import parsing for Google Pay, Paytm, HDFC, ICICI, SBI, and generic bank statements.
  - Flexible column detection for combined signed amounts versus separate `Debit`/`Credit` columns.
  - Multi-format date parsing (`DD-MM-YYYY`, `YYYY-MM-DD`, `DD/MM/YYYY`).
  - Automatic category keyword tagging based on description text.
  - CSV export generation verifying UTF-8 BOM encoding for Excel/Google Sheets compatibility.

---

### 6. [`test/test_budget_reallocation.py`](file:///Users/suyash/Downloads/budgetapp/test/test_budget_reallocation.py)
- **Job**: Validates category budget envelope transfers.
- **Tested Features**:
  - Zero-sum budget conservation: verifies source category limits decrease by the exact amount destination limits increase.
  - Validation checks preventing transfers that exceed available envelope limits or transfer negative amounts.
  - Atomic database commit ensuring partial updates never occur.

---

### 7. [`test/test_split_transactions.py`](file:///Users/suyash/Downloads/budgetapp/test/test_split_transactions.py)
- **Job**: Tests multi-category split transaction creation and line item grouping.
- **Tested Features**:
  - Creating multiple line item allocations linked under a shared UUID `split_group_id`.
  - Retrieving full split breakdowns by group ID.
  - Validating that the sum of line item amounts equals the parent transaction receipt total.

---

### 8. [`test/test_savings_goals.py`](file:///Users/suyash/Downloads/budgetapp/test/test_savings_goals.py)
- **Job**: Tests the dedicated named savings goals subsystem.
- **Tested Features**:
  - Goal lifecycle: creation, target configuration, emoji assignment, updates, and deletion.
  - Fund deposits into goals from Available Cash or General Savings.
  - Fund withdrawals from goals back to Available Cash.
  - Automatic status transition to `completed` when current balance reaches the target amount.
  - Audit logging verification in `savings_goal_logs`.

---

### 9. [`test/test_ai_features.py`](file:///Users/suyash/Downloads/budgetapp/test/test_ai_features.py)
- **Job**: Tests AI Assistant backend helpers, prompt construction, and key encryption.
- **Tested Features**:
  - Machine-tied Fernet encryption and decryption of user API keys.
  - Dynamic Gemini model discovery fallback to curated lists when offline or with unauthenticated keys.
  - Structured financial context serialization containing live balances, envelope states, and runway.
  - 1-click Financial Health Audit prompt generation.
  - Natural language parsing transforming text statements into structured transaction dictionaries.

---

### 10. [`test/test_desktop_polish.py`](file:///Users/suyash/Downloads/budgetapp/test/test_desktop_polish.py)
- **Job**: Tests automated backups, retention rules, privacy masking, and shortcuts.
- **Tested Features**:
  - SQLite backup snapshot creation in `backups/`.
  - Daily automatic backup logic ensuring only one snapshot is created per day.
  - 7-day retention policy deleting older backups while preserving the last 7 daily files.
  - Database restoration from backup files.
  - Privacy masking state toggling (masking monetary labels to `••••••`).
  - Keyboard shortcut dispatch verification.

---

### 11. [`test/test_user_reported_fixes.py`](file:///Users/suyash/Downloads/budgetapp/test/test_user_reported_fixes.py)
- **Job**: Regression test suite covering all interactive and data bug fixes reported during user acceptance testing.
- **Tested Features**:
  - Hover tooltips and crosshairs rendering on the pace line chart without color tuple type errors.
  - Polar coordinates wedge detection on the category pie chart updating the 6-month historical trend chart.
  - Automatic recurring transaction evaluator advancing due dates and creating `pending_approval` transactions.
  - In-place transaction approval action confirming pending recurring transactions into the ledger.
  - Historical line chart spending curve rendering properly when viewing past months.

---

## How to Execute the Test Suites

Run individual test suites:
```bash
.venv/bin/python3 test/test_interactive_chart.py
.venv/bin/python3 test/test_csv_export_import.py
```

Run the complete test suite across all 11 modules:
```bash
for t in test/test_*.py; do .venv/bin/python3 "$t"; done
```
