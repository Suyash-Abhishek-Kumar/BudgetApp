# App Module Specification (`app/`)

The `app/` package houses the entire backend core, data persistence layer, business logic rules, scheduled task automations, and AI service integrations for **BudgetApp v2.0**. All backend operations are local-first, privacy-respecting, and designed around an SQLite database.

---

## Directory Overview

```
app/
├── __init__.py           # Package marker and public module exports
├── schema.sql            # Relational database DDL schema definitions
├── db.py                 # SQLite connection manager and database bootstrapper
├── categories.py         # Category CRUD, spending limits, and envelope reallocation
├── transactions.py       # Single, split, search, edit, CSV import/export engines
├── budget_logic.py       # Financial summaries, pace/trend math, rollover jobs
├── emergency_fund.py     # Emergency fund reserves and transfer audit logging
├── recurring.py          # Recurring transaction rule scheduler and processor
├── savings_goals.py      # Dedicated named savings goals subsystem
├── settings.py           # Persistent key-value application settings store
├── ai_chat.py            # Gemini API client, dynamic model discovery, key encryption
├── ai_context.py         # Budget context generator, 1-click audit, NLP quick-add
└── backup.py             # Automated daily SQLite snapshots and restore manager
```

---

## File Specifications & Implemented Features

### 1. [`app/schema.sql`](file:///Users/suyash/Downloads/budgetapp/app/schema.sql)
- **Job**: Defines the complete relational database schema for SQLite, establishing table constraints, foreign keys, default values, and column data types.
- **Implemented Tables**:
  - `categories`: Stores budget envelopes (`id`, `name` UNIQUE, `soft_limit`, `hard_limit`, `created_at`).
  - `transactions`: Core ledger storing income and expenses (`id`, `date`, `amount`, `type`, `category_id`, `description`, `funding_source`, `recurring_id`, `status`, `split_group_id`, `created_at`).
  - `savings`: General savings fund history (`id`, `date`, `amount`, `description`, `created_at`).
  - `emergency_fund`: Emergency fund ledger (`id`, `date`, `amount`, `type`, `note`, `created_at`).
  - `month_rollover`: Records closed month financial surpluses and allocations (`id`, `month`, `total_income`, `total_spent`, `surplus`, `savings_allocated`, `emergency_allocated`, `unallocated`, `rolled_over_at`).
  - `settings`: Persistent configuration key-value pairs (`key` PRIMARY KEY, `value`, `updated_at`).
  - `recurring_transactions`: Automated subscription rules (`id`, `name`, `amount`, `type`, `category_id`, `frequency`, `interval_days`, `next_due_date`, `auto_approve`, `is_active`, `last_generated_date`).
  - `savings_goals`: Named target savings accounts (`id`, `title`, `target_amount`, `current_amount`, `target_date`, `category_id`, `icon`, `status`, `created_at`, `updated_at`).
  - `savings_goal_logs`: Detailed contribution and withdrawal logs for each savings goal (`id`, `goal_id`, `date`, `amount`, `type`, `note`, `created_at`).

---

### 2. [`app/db.py`](file:///Users/suyash/Downloads/budgetapp/app/db.py)
- **Job**: Manages database connection lifecycle and bootstrap execution.
- **Implemented Features**:
  - `get_connection(db_path)`: Opens an SQLite connection with `sqlite3.Row` dictionary-like column access and strictly enforces relational foreign key integrity via `PRAGMA foreign_keys = ON`.
  - `init_db(db_path)`: Idempotently executes `app/schema.sql` on the target database, creating any non-existent tables.
  - `reset_db(db_path)`: Test/dev utility that wipes an existing SQLite database and recreates a fresh schema.

---

### 3. [`app/categories.py`](file:///Users/suyash/Downloads/budgetapp/app/categories.py)
- **Job**: Manages category budget envelope definitions, limits, and envelope balance transfers.
- **Implemented Features**:
  - **Category Management**: `list_categories()`, `get_category()`, `get_category_by_name()`, `create_category()`, `update_category()`, and `delete_category()`.
  - **Budget Envelope Transfers (`transfer_category_budget`)**: Allows users to reallocate spending power directly between envelopes (e.g. moving ₹1,000 from Entertainment to Groceries) within a single atomic database transaction, reducing the source envelope's soft/hard limits and increasing the target envelope's limits without modifying monthly income.

---

### 4. [`app/transactions.py`](file:///Users/suyash/Downloads/budgetapp/app/transactions.py)
- **Job**: Handles transaction creation, multi-category splits, in-place editing, querying, live search, and universal CSV import/export.
- **Implemented Features**:
  - **Single Transactions (`create_transaction`)**: Creates confirmed or `pending_approval` transactions with assigned funding sources (`regular`, `savings`, `emergency_fund`).
  - **Multi-Category Splits (`create_split_transaction`, `get_split_breakdown`)**: Groups multiple category allocations from a single receipt under a shared UUID `split_group_id`.
  - **In-Place Editing (`update_transaction`)**: Modifies amounts, categories, descriptions, dates, and funding sources while ensuring category budget limit checks remain consistent.
  - **Live Search & Filtering (`search_transactions`, `list_transactions`)**: Performs full-text searches across descriptions and category names with date range filters ("This Month", "Last 30 Days", "Custom Range") and transaction type toggles.
  - **Universal CSV Statement Import (`import_transactions_from_csv`)**: Auto-detects columns from Google Pay, Paytm, HDFC, ICICI, SBI, and generic bank CSVs. Maps `Debit`/`Credit` or signed `Amount` fields, parses multi-format dates (`DD-MM-YYYY`, `YYYY-MM-DD`), and automatically assigns categories based on transaction keywords.
  - **CSV Export (`export_transactions_csv`)**: Generates Excel-friendly CSVs encoded with UTF-8 BOM matching user-selected filters.

---

### 5. [`app/budget_logic.py`](file:///Users/suyash/Downloads/budgetapp/app/budget_logic.py)
- **Job**: Core mathematical engine for monthly totals, spending velocity, pace projections, historical trends, and month-end rollover.
- **Implemented Features**:
  - **Dashboard Financial Summary (`get_dashboard_summary`)**: Calculates monthly income, total expenses, available-to-spend balance, cumulative savings, and emergency fund balance.
  - **Category Spending Progress (`get_category_spending`)**: Aggregates spent amounts against soft and hard limits for each category to drive visual progress bars and warning states.
  - **Pace Projection Math (`month_end_projection`)**: Computes daily cumulative spending curves, daily spending velocity, and projected month-end expenditure.
  - **Historical Spending Trends (`get_six_month_spending_trend`)**: Computes a 6-month historical spending profile for the entire budget or filtered by a specific category.
  - **Time Machine Historical Discovery (`get_past_months_list`)**: Scans historical transactions and rollovers to identify all months recorded in the system.
  - **Month-End Rollover Engine (`run_month_end_rollover`, `auto_run_all_past_rollovers`)**: Computes monthly surplus or deficit, allocates funds to savings and emergency reserves according to user percentages, records rollover snapshots, and automatically rolls over unclosed past months upon app launch.

---

### 6. [`app/emergency_fund.py`](file:///Users/suyash/Downloads/budgetapp/app/emergency_fund.py)
- **Job**: Manages emergency fund balances, deposit/withdrawal accounting, and transfer audit trails.
- **Implemented Features**:
  - **Balance Calculation (`get_emergency_fund_balance`)**: Sums all deposits, rollover allocations, and withdrawals to compute the current liquid emergency reserve.
  - **Deposit & Withdrawal (`deposit_emergency_fund`, `withdraw_emergency_fund`)**: Atomically updates the emergency ledger with mandatory notes and timestamps.
  - **Audit History (`get_emergency_fund_history`)**: Returns a chronological list of transfers with timestamps, types, amounts, and notes.

---

### 7. [`app/recurring.py`](file:///Users/suyash/Downloads/budgetapp/app/recurring.py)
- **Job**: Schedules and processes recurring subscriptions, bills, and scheduled income.
- **Implemented Features**:
  - **Rule Configuration**: `create_recurring_transaction()`, `update_recurring_transaction()`, `delete_recurring_transaction()`, `toggle_recurring_transaction()`, and `list_recurring_transactions()`.
  - **Automated Due Date Processor (`process_due_recurring_transactions`)**: Scans all active rules, checks if `next_due_date <= target_date`, generates idempotent `pending_approval` transaction records, and advances `next_due_date` across `daily`, `monthly`, `yearly`, or custom intervals.

---

### 8. [`app/savings_goals.py`](file:///Users/suyash/Downloads/budgetapp/app/savings_goals.py)
- **Job**: Implements dedicated named savings goals with target dates, visual progress metrics, and contribution logs.
- **Implemented Features**:
  - **Goal CRUD**: `create_savings_goal()`, `update_savings_goal()`, `delete_savings_goal()`, `list_savings_goals()`, and `get_savings_goal()`.
  - **Goal Fund Transfers (`deposit_to_goal`, `withdraw_from_goal`)**: Manages deposits into goals and withdrawals back to available cash or general savings, updating the goal's `current_amount` and logging each action.
  - **Audit Logging (`get_goal_logs`)**: Provides historical records of all deposits, withdrawals, and milestones reached.

---

### 9. [`app/settings.py`](file:///Users/suyash/Downloads/budgetapp/app/settings.py)
- **Job**: Persistent storage and retrieval of application-level configurations.
- **Implemented Features**:
  - `get_setting(key, default, db_path)` & `set_setting(key, value, db_path)`: Reads and writes persistent key-value configuration pairs.
  - `get_all_settings(db_path)`: Fetches all stored settings in a single dictionary.
  - **Supported Preferences**: Default currency symbol (defaults to `₹`), appearance theme (`dark` / `light`), rollover allocation percentages, selected Gemini model, and encrypted API key.

---

### 10. [`app/ai_chat.py`](file:///Users/suyash/Downloads/budgetapp/app/ai_chat.py)
- **Job**: Bridges BudgetApp with Google Gemini generative models.
- **Implemented Features**:
  - **Hardware-Tied API Key Encryption (`save_api_key`, `load_api_key`)**: Uses Python's `cryptography.fernet` with a key derived from local machine hardware attributes to protect user API keys on disk.
  - **Dynamic Model Auto-Discovery (`fetch_available_models`)**: Queries Google's `genai.Client.models.list()` live to discover active Gemini models supported by the user's specific API key, filtering out non-generative endpoints.
  - **Streaming Chat (`send_chat_message`)**: Runs asynchronous background generation threads, streaming response tokens to the UI while injecting live financial context.

---

### 11. [`app/ai_context.py`](file:///Users/suyash/Downloads/budgetapp/app/ai_context.py)
- **Job**: Contextual prompt generator for AI financial intelligence.
- **Implemented Features**:
  - **Live Financial Context (`build_financial_context`)**: Serializes current month balances, envelope limits, emergency runway, savings goals, and recent transactions into structured context for Gemini prompts.
  - **1-Click Financial Health Audit (`generate_financial_audit`)**: Generates an actionable financial report evaluating spending velocity, emergency runway adequacy, and envelope budget health.
  - **Natural Language Quick-Add Parsing (`parse_transaction_from_nlp`)**: Converts freeform text (e.g. *"Spent 450 on groceries yesterday"*) into structured JSON containing date, amount, category, and description.

---

### 12. [`app/backup.py`](file:///Users/suyash/Downloads/budgetapp/app/backup.py)
- **Job**: Automated and manual SQLite database backup and recovery.
- **Implemented Features**:
  - **Snapshot Creation (`create_backup`)**: Generates timestamped SQLite snapshots inside `backups/`.
  - **Automated Startup Backup (`auto_backup_on_startup`)**: Checks if a backup exists for the current calendar day upon launch; if not, triggers an automatic backup and enforces a 7-day retention policy.
  - **Backup Management (`list_backups`, `restore_backup`)**: Lists existing backups with file sizes and dates, and provides 1-click database restoration.
