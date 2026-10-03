# BudgetApp (macOS Desktop)

BudgetApp for macOS is a local-first desktop personal budget tracker built with Python, CustomTkinter, and SQLite. It helps you record income and expenses, set category spending limits, monitor your month, and understand where your money is going without relying on a hosted budgeting service.

## Features

- **Dashboard**: Available-to-spend, income, spending, savings, and emergency-fund summaries
- **Category Budgets**: Soft and hard limits, progress indicators, and overflow warnings
- **Transaction Management**: Add, review, approve, edit, and split income and expense transactions
- **Interactive Visualizations**: Spending pace vs. month-to-date and category breakdowns powered by Matplotlib
- **Month-End Rollover**: Configurable automatic savings and emergency-fund allocation
- **Recurring Transactions**: Rule-based scheduling with pending approval staging
- **Emergency Fund**: Balance tracking and deposit/withdrawal history log
- **Savings Goals**: Target tracking, saved amounts, and progress indicators
- **CSV Support**: Full import and export of transaction history
- **Privacy Mode**: Keyboard shortcut (`Cmd/Ctrl + P`) to obscure sensitive figures
- **AI Assistant**: Optional Gemini-powered assistant that answers questions using live, local budget data

## Requirements

- Python 3.10 or newer
- Tk support for your Python installation
- macOS (tested on macOS Sonoma / Apple Silicon)

## Setup & Installation

From the `mac/` directory (or workspace root targeting `mac`):

```bash
cd mac
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Running the App

```bash
python3 main.py
```

The application creates its SQLite database automatically:
- During local development: `budget.db` in this folder
- When packaged as a standalone macOS application: `~/Library/Application Support/BudgetApp/budget.db`

## Testing

Run the automated test suite from the `mac/` directory:

```bash
python3 -m unittest discover -s test -p "test_*.py"
```

## Packaging for macOS

To package the standalone `.app` bundle using PyInstaller:

```bash
pyinstaller BudgetApp.spec
```

The output bundle `BudgetApp.app` will be created in `dist/`.
