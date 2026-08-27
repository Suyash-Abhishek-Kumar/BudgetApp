# Personal Budget Tracker - Milestone 1

SQLite schema + core Python data-access layer, matching
`Budget_App_Project_Spec.docx`.

## Structure

```
budgetapp/
  app/
    schema.sql           7-table schema (Section 5 of the spec)
    db.py                connection handling + init_db() / reset_db()
    settings.py          dynamic key/value settings, with defaults
    categories.py        CRUD for budget categories
    transactions.py      CRUD + soft/hard-limit status logic (Section 6.1)
    emergency_fund.py     balance, audit log, manual transfers (Section 6.4)
    budget_logic.py       month-end rollover + EF split, dashboard
                           summary, month-end spending projection
  test_milestone1.py      end-to-end sanity script (run this first)
  requirements.txt
```

## Try it

```bash
cd budgetapp
python3 test_milestone1.py
```

This creates a throwaway `test_budget.db`, runs through every rule in
the spec (soft/hard limits, overflow messaging, pending-approval
exclusion, month-end rollover + emergency-fund split, the spending
projection) and asserts the results, printing each step so you can
see exactly what's happening.

## Using it in Python

```python
from app.db import init_db
from app import categories, transactions, budget_logic

init_db()  # creates budget.db next to app/ on first run

food_id = categories.create_category("Food", soft_limit=200, hard_limit=250)
transactions.add_transaction(amount=45.50, type="expense", category_id=food_id,
                              description="Groceries")

print(transactions.category_status(food_id))
print(budget_logic.dashboard_summary())
```

## What's next (Milestone 2)

CustomTkinter shell: navigation, Add Transaction screen, Transaction
List — calling only the functions in `app/`, never touching SQL
directly, per the architecture in Section 4 of the spec.
