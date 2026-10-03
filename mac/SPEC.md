# BudgetApp v2.0 — System Architecture & Root Specification

**BudgetApp** is a local-first, privacy-focused desktop personal finance application built with Python 3, CustomTkinter, Matplotlib, SQLite, and Google Gemini.

---

## Root Project Layout

```
.
├── main.py                  # Application entry point, window management, startup jobs
├── BudgetApp.spec           # PyInstaller standalone macOS application build specification
├── requirements.txt         # Project dependencies and minimum versions
├── README.md                # General project overview, setup, and usage guide
├── SPEC.md                  # Root architectural specification (this file)
├── app/                     # Backend data models, SQLite persistence, business logic, AI
│   └── SPEC.md              # Detailed App specification (app/SPEC.md)
├── ui/                      # CustomTkinter GUI screens, interactive charts, and dialogs
│   └── SPEC.md              # Detailed UI specification (ui/SPEC.md)
├── test/                    # Automated unit, integration, and regression test suites
│   └── SPEC.md              # Detailed Test specification (test/SPEC.md)
├── backups/                 # Automated daily SQLite snapshots
├── dist/                    # PyInstaller build artifacts & standalone BudgetApp.app bundle
└── build/                   # PyInstaller intermediate compilation cache
```

---

## Root Files & Responsibilities

### 1. [`main.py`](file:///Users/suyash/Downloads/budgetapp/main.py)
- **Job**: Application entry point. Initializes the database, constructs the CustomTkinter root window (`BudgetApp`), manages the navigation sidebar, coordinates view switching, and orchestrates startup lifecycle jobs.
- **Implemented Features**:
  - **Dynamic Database Path Resolution**: Detects whether running as an unpacked script (`./budget.db`) or as a frozen macOS application bundle (`~/Library/Application Support/BudgetApp/budget.db`), preserving user data across updates.
  - **Database Initialization (`init_db`)**: Ensures all relational tables and schemas exist upon launch.
  - **Automated Startup Tasks**:
    - `budget_logic.auto_run_all_past_rollovers(DB_PATH)`: Silently closes and rolls over any unclosed past months.
    - `recurring_api.process_due_recurring_transactions(db_path=DB_PATH)`: Evaluates active recurring rules and stages due transactions into the `pending_approval` queue.
    - `backup_api.auto_backup_on_startup(DB_PATH)`: Generates daily automated backups with 7-day retention cleanup.
  - **Global Keyboard Shortcuts**:
    - `Cmd/Ctrl + P`: Toggles privacy mode across all metric cards.
    - `Cmd/Ctrl + 1 to 6`: Fast tab switching between Dashboard, Add Transaction, Transactions, Savings Goals, Settings, and AI Assistant.
  - **Responsive Layout**: Sidebar with brand title, version badge, navigation buttons, and responsive main view container.

---

### 2. [`BudgetApp.spec`](file:///Users/suyash/Downloads/budgetapp/BudgetApp.spec)
- **Job**: PyInstaller packaging configuration for standalone macOS compilation.
- **Implemented Features**:
  - Automatically bundles the SQLite DDL schema: `datas=[('app/schema.sql', 'app')]`.
  - Collects all necessary runtime assets and binaries for `customtkinter` and `google.genai`.
  - Configures the `Analysis`, `PYZ`, `EXE`, `COLLECT`, and `BUNDLE` targets producing `BudgetApp.app`.
  - Configured for windowed execution (`console=False`) on Apple Silicon (`arm64`).

---

### 3. [`requirements.txt`](file:///Users/suyash/Downloads/budgetapp/requirements.txt)
- **Job**: Declares python dependencies required for running and packaging BudgetApp.
- **Dependencies**:
  - `customtkinter>=5.2.0`: Modern desktop UI widget toolkit.
  - `matplotlib>=3.8.0`: Plotting engine for interactive spending pace and category trends.
  - `pyinstaller>=6.0.0`: Packaging standalone macOS application bundles.
  - `google-genai>=2.0.0`: Next-generation Google Gemini AI SDK.
  - `cryptography>=42.0.0`: Machine-tied Fernet encryption for local API key storage.

---

### 4. [`README.md`](file:///Users/suyash/Downloads/budgetapp/README.md)
- **Job**: Public user guide, feature checklist, installation instructions, and development overview.

---

## Directory Specifications

For in-depth specifications of each submodule, refer to the individual specification files:

1. [**`app/SPEC.md`**](file:///Users/suyash/Downloads/budgetapp/app/SPEC.md): Database schemas, transaction handling, budget calculations, emergency funds, recurring engines, savings goals, AI services, and backup systems.
2. [**`ui/SPEC.md`**](file:///Users/suyash/Downloads/budgetapp/ui/SPEC.md): Design tokens, Dashboard, Add Transaction, Transaction List, Savings Goals, Settings, and AI Chat screens.
3. [**`test/SPEC.md`**](file:///Users/suyash/Downloads/budgetapp/test/SPEC.md): Complete automated test suite coverage, testing methodologies, and validation commands.
