# BudgetApp

BudgetApp is a local-first, privacy-focused personal finance tracking system designed to give you complete visibility and control over your budget without relying on third-party cloud servers, subscriptions, or telemetry.

This repository contains both the desktop (**macOS**) and native mobile (**Android**) implementations sharing identical data models, accounting principles, and core feature parity.

---

## Platforms

### 1. [Android Mobile (`android/`)](android/README.md)
The native mobile application built with **Kotlin**, **Jetpack Compose (Material 3)**, and **Room (SQLite)**.
- **Key Tech**: Kotlin, Jetpack Compose, Room (SQLite), Coroutines/Flow, Android WorkManager, Google Gemini AI.
- **UI & UX**: Responsive layout adapted for edge-to-edge mobile screens, modern FinTech surface hierarchy (Cobalt, Sapphire, Slate, Emerald), custom adaptive vector launcher icon, and privacy mode.
- **Analytics & Visualizations**:
  - Interactive Spending Pace & Forecast canvas chart with numeric X & Y coordinate axes, grid guidelines, and daily touch inspection.
  - Interactive filled Donut/Pie chart with percentage wedges and category filtering.
  - 6-Month historical spending trend grouped bar chart (Spend vs. Rollover).
- **Core Workflows**: Time-Machine month switcher, closed-month Archives with financial metric breakdown, multi-category split transactions, recurring bills staging & approval, emergency fund logs, savings goal milestones, and CSV import/export.
- Read more: [android/README.md](android/README.md).

### 2. [macOS Desktop (`mac/`)](mac/README.md)
The desktop application built with **Python**, **CustomTkinter**, **Matplotlib**, and **SQLite**.
- **Key Tech**: Python 3.10+, CustomTkinter, Matplotlib, PyInstaller, `google-genai`.
- **Packaging**: Standalone macOS application bundle (`BudgetApp.app`).
- **Features**: Multi-tab desktop navigation, Matplotlib pace & distribution charts, split transactions, keyboard shortcuts (`Cmd+P` privacy mode), automated SQLite snapshots, and Gemini AI assistant.
- Read more: [mac/README.md](mac/README.md) and [mac/SPEC.md](mac/SPEC.md).

---

## Core Capabilities Across Both Platforms

- **Local-First & Private**: Data stays strictly on your device inside an offline SQLite database.
- **Category Budgets**: Set soft and hard spending limits with clear visual alert states.
- **Dynamic Rollover Engine**: Month-end surplus automatically closes and rolls into savings goals and emergency funds.
- **Time Machine & Closed Archives**: Seamlessly switch between active and past finalized months with full historical ledger inspection.
- **Recurring Transactions**: Automated staging and approval workflows for recurring bills and income.
- **Emergency Fund & Savings Goals**: Dedicated tracking with transfer history logs.
- **AI Financial Assistant**: Optional Google Gemini integration providing contextual financial audits and insights using local summaries.
- **Data Portability**: Full CSV transaction export and import across both platforms.

---

## Repository Structure

```text
budgetapp/
├── README.md               # Main project overview (this file)
├── android/                # Native Android application (Kotlin/Jetpack Compose)
│   ├── app/                # Android app module (Room, Compose UI, Domain logic)
│   ├── gradle/             # Gradle wrapper & version catalogs
│   ├── build.gradle.kts    # Root Android build configuration
│   └── README.md           # Android documentation & architecture guide
└── mac/                    # macOS desktop application (Python/CustomTkinter)
    ├── main.py             # Entry point
    ├── app/                # Data access, business logic, AI assistant
    ├── ui/                 # CustomTkinter interface
    ├── test/               # Test suites
    ├── BudgetApp.spec      # PyInstaller packaging spec
    ├── requirements.txt    # Python dependencies
    ├── SPEC.md             # Functional specification
    └── README.md           # Desktop documentation
```

---

## Getting Started

### Running Android
```bash
cd android
./gradlew assembleDebug
```
*Requires JDK 17+ and Android SDK 34.*

### Running macOS Desktop
```bash
cd mac
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```
*Requires Python 3.10+.*
