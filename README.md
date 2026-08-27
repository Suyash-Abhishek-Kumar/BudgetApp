# BudgetApp

BudgetApp is a local-first desktop personal budget tracker built with
Python, CustomTkinter, and SQLite. It helps you record income and expenses,
set category spending limits, monitor your month, and understand where your
money is going without relying on a hosted budgeting service.

## Features

- Dashboard with available-to-spend, income, spending, savings, and emergency-fund summaries
- Category budgets with soft and hard limits, progress indicators, and overflow warnings
- Add, review, approve, and manage income and expense transactions
- Interactive spending charts, including category breakdowns and monthly trends
- Month-end rollover with configurable savings and emergency-fund allocation
- Emergency-fund balance and transfer history
- Configurable application settings and light/dark appearance modes
- Optional Gemini-powered AI Assistant that can answer questions using live budget data

## Requirements

- Python 3.10 or newer
- Tk support for your Python installation
- A macOS, Windows, or Linux desktop environment

Install the project dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run the application

```bash
python3 main.py
```

The application creates its SQLite database automatically. During local
development it uses `budget.db` in the project directory. When packaged as
the macOS application, it stores data in:

```text
~/Library/Application Support/BudgetApp/budget.db
```

To enable the AI Assistant, open **Settings**, choose **AI Assistant**, enter
a Gemini API key, and select a model. The key is encrypted before it is
stored locally. The assistant is optional; the rest of the budget tracker
works without it.

## Test the core logic

```bash
python3 test_milestone1.py
```

The end-to-end sanity script uses a throwaway `test_budget.db` and checks
category limits, transaction approval, emergency-fund transfers, month-end
rollover, savings allocation, projections, and dashboard summaries.

## Project layout

```text
app/
  schema.sql             SQLite schema
  db.py                  Database connections and initialization
  categories.py          Category CRUD and limits
  transactions.py        Income and expense transactions
  budget_logic.py        Dashboard, rollover, savings, and projections
  emergency_fund.py      Emergency-fund balance and transfer history
  settings.py            Persistent application settings
  ai_chat.py             Gemini chat integration and key encryption
  ai_context.py          Budget context supplied to the assistant
ui/
  dashboard_screen.py    Dashboard and charts
  add_transaction_screen.py
  transaction_list_screen.py
  settings_screen.py
  chat_screen.py         AI Assistant interface
main.py                  Desktop application entry point
BudgetApp.spec           PyInstaller packaging configuration
```

The application is single-user and local-first. SQLite files, virtual
environments, caches, and packaged build output are excluded from Git by
[`.gitignore`](.gitignore).
