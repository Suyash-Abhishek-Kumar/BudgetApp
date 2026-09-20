# UI Module Specification (`ui/`)

The `ui/` package provides the entire graphical user interface for **BudgetApp v2.0**. Built using CustomTkinter and embedded Matplotlib backends, the interface delivers a desktop-native, responsive experience featuring dark/light appearance modes, interactive data visualizations, and contextual modal dialogs.

---

## Directory Overview

```
ui/
├── __init__.py                  # Package marker and component exports
├── theme.py                     # Theme tokens, palettes, typography, and styling constants
├── dashboard_screen.py          # Overview metrics, interactive charts, and envelope reallocation
├── add_transaction_screen.py    # Transaction entry, NLP quick-fill, and multi-category splits
├── transaction_list_screen.py   # Transaction ledger, in-place edit, live search, CSV import/export
├── savings_goals_screen.py      # Dedicated named savings goals grid, progress, deposit/withdraw
├── settings_screen.py           # Multi-tab settings: preferences, archives, EF ledger, backups, AI
└── chat_screen.py               # Streaming AI Assistant chat window with quick prompt chips
```

---

## File Specifications & Implemented Features

### 1. [`ui/theme.py`](file:///Users/suyash/Downloads/budgetapp/ui/theme.py)
- **Job**: Central design system token repository for colors, fonts, margins, and component dimensions.
- **Implemented Features**:
  - **Color Tokens**: Defines dark/light tuple colors for primary accents, surface backgrounds, borders, cards, income green, expense red, warning yellow, and neutral grays.
  - **Typography**: Configures consistent font families, weights, and sizes for headings, subheadings, body text, badges, and monetary values.
  - **UI Constants**: Sets standardized corner radiuses, button heights, padding, and layout margins across all application views.

---

### 2. [`ui/dashboard_screen.py`](file:///Users/suyash/Downloads/budgetapp/ui/dashboard_screen.py)
- **Job**: Serves as the primary operational command center of the application.
- **Implemented Features**:
  - **Top Metric Cards**: Displays live balances for Available to Spend, Monthly Income, Total Spent, Total Saved, and Emergency Fund. Supports privacy masking (replacing numbers with `••••••`).
  - **Time Machine Mode & Past Month Dropdown**: Allows instant switching between the current month and historical months. Automatically activates a prominent yellow Read-Only warning banner when inspecting past months.
  - **Category Spending Progress Bars**: Renders visual spending bars for each envelope, turning yellow upon reaching the soft limit and red upon exceeding the hard limit.
  - **Envelope Budget Reallocation Dialog (`[🔄 Transfer Budget]`)**: Modal allowing users to transfer budget amounts between categories with live validation.
  - **Interactive Spending Pace Chart (`_draw_pace_chart`)**:
    - Embedded Matplotlib canvas with custom dark/light background styling.
    - Real-time mouse hover tracking with snapping vertical crosshairs.
    - Floating tooltip displaying the day (`Day X, YYYY-MM-DD`) and cumulative expenses (`₹...`).
    - Compares actual cumulative spending against projected monthly pace and budget limits.
  - **Spending Breakdown Pie Chart (`_draw_pie_chart`)**:
    - Visualizes proportional category expenditures.
    - Implements polar coordinate click detection (`_on_pie_tk_click`) allowing users to click a slice to filter the 6-month historical trend chart.
  - **6-Month Historical Spending Trend Chart (`_draw_trend_chart`)**:
    - Displays monthly spending history for all categories or isolated to a selected category.
    - Includes an interactive reset button (`[↺ All Categories]`) and `<Escape>` key binding to return to overall spending.

---

### 3. [`ui/add_transaction_screen.py`](file:///Users/suyash/Downloads/budgetapp/ui/add_transaction_screen.py)
- **Job**: Transaction creation interface supporting single entries, AI natural language parsing, and multi-category splits.
- **Implemented Features**:
  - **Single Transaction Form**: Inputs for amount, transaction type (income/expense), category selection, date picker, description note, and funding source (`regular`, `savings`, `emergency_fund`).
  - **AI Natural Language Quick-Add**: Input field where users type freeform descriptions (e.g. *"Spent 650 on dinner with friends"*), clicking `[✨ Auto-Fill]` to parse and populate the form fields using Gemini.
  - **Multi-Category Split Transactions**:
    - Checkbox toggle `[ Split across categories ]` reveals a dynamic itemized split row builder.
    - Allows adding/removing individual category rows with custom sub-amounts.
    - Live unallocated balance badge shows remaining amount to be matched before allowing submission.

---

### 4. [`ui/transaction_list_screen.py`](file:///Users/suyash/Downloads/budgetapp/ui/transaction_list_screen.py)
- **Job**: Interactive financial ledger with filtering, in-place editing, pending approvals, and CSV processing.
- **Implemented Features**:
  - **Live Search & Filter Toolbar**:
    - Debounced full-text search input filtering across descriptions and categories.
    - Date range presets ("All Time", "This Month", "Last Month", "Last 30 Days", "Last 90 Days", "Custom Range").
    - Type filters (All, Expenses, Income) and status toggles.
  - **Pending Recurring Transactions Queue**: Displays due recurring items with an inline `[✅ Approve]` action to instantly confirm them into the ledger.
  - **In-Place Transaction Editor Modal (`EditTransactionDialog`)**: Double-clicking any row or clicking `[✏️ Edit]` opens an in-place modal to modify amounts, dates, categories, descriptions, and funding sources with live limit validation.
  - **Universal CSV Statement Import (`ImportCsvDialog`)**:
    - File dialog to select statements from Google Pay, Paytm, HDFC, ICICI, SBI, or generic banks.
    - Displays detected columns, preview rows, and categorization rules before importing.
  - **Filtered CSV Export**: Exports current search results to an Excel-friendly CSV with UTF-8 BOM encoding.

---

### 5. [`ui/savings_goals_screen.py`](file:///Users/suyash/Downloads/budgetapp/ui/savings_goals_screen.py)
- **Job**: Dedicated visual management of target savings goals.
- **Implemented Features**:
  - **Savings Goals Grid**: Card-based overview of active and completed goals showing titles, target amounts, current progress, target completion dates, and custom emoji icons.
  - **Visual Progress Indicators**: Displays progress bars, percentage completion badges, and days remaining.
  - **Goal Creation Modal**: Dialog to configure title, target amount, target date, category link, and emoji icon.
  - **Deposit & Withdraw Modals**: Allows transferring funds between Available Cash / General Savings and the selected goal.
  - **Goal History Ledger**: Expandable drawer showing all past deposits and withdrawals for each goal.

---

### 6. [`ui/settings_screen.py`](file:///Users/suyash/Downloads/budgetapp/ui/settings_screen.py)
- **Job**: Multi-tab management hub for application configuration, historical records, backups, and AI settings.
- **Implemented Features**:
  - **Tab 1 — General Settings**: Currency symbol selector (`₹`, `$`, `€`, `£`, `¥`) and Dark/Light appearance mode switch.
  - **Tab 2 — Month Rollover & Archives**:
    - Configurable sliders for month-end surplus allocation (% to Savings vs % to Emergency Fund).
    - Manual rollover execution trigger.
    - Historical Month Archives table with financial breakdown and a `[👁️ View on Dashboard]` button to launch Time Machine mode.
  - **Tab 3 — Emergency Fund**:
    - Deposit and Withdraw controls connected to available money.
    - Complete transfer history table with full-text inspectable notes.
  - **Tab 4 — Recurring Transactions**: Management console to create, toggle active/paused status, edit, or delete recurring rules.
  - **Tab 5 — AI Assistant Configuration**:
    - Gemini API key input with show/hide toggle and local encryption.
    - Dynamic model selector with live `[🔄 Discover Models]` button to query available models on the key.
    - One-click `[🩺 Run Financial Health Audit]` button to generate an instant analysis of spending and runway.
  - **Tab 6 — Data & Backups**:
    - Manual backup generator (`[💾 Create Backup Now]`).
    - List of timestamped backups with file sizes and creation dates.
    - One-click backup restoration.

---

### 7. [`ui/chat_screen.py`](file:///Users/suyash/Downloads/budgetapp/ui/chat_screen.py)
- **Job**: Conversational AI assistant interface.
- **Implemented Features**:
  - **Streaming Conversation Thread**: Renders user messages and streaming Gemini responses in real-time.
  - **Financial Context Injection**: Automatically enriches prompts with real-time budget figures and category statuses.
  - **Quick Action Suggestion Chips**: Clickable prompt chips (*"How much can I spend today?"*, *"Where is my money going?"*, *"Check emergency runway"*) for instant answers.
  - **Clear History & Status Indicators**: Visual status flags showing connection state, current model, and thread clearing.
