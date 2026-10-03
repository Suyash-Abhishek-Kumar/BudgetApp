# BudgetApp

BudgetApp is a local-first, privacy-focused personal finance tracking system designed to give you complete visibility and control over your budget without relying on third-party cloud servers or subscriptions.

This repository contains both the desktop (macOS) and native mobile (Android) implementations sharing the same underlying data models and core financial principles.

---

## Platforms

### 1. [macOS Desktop (`mac/`)](mac/README.md)
The original desktop application built with Python, CustomTkinter, Matplotlib, and SQLite.
- **Key Tech**: Python 3.10+, CustomTkinter, Matplotlib, PyInstaller, `google-genai`.
- **Packaging**: Standalone macOS application bundle (`BudgetApp.app`).
- **Features**: Multi-tab desktop navigation, interactive pace charts, split transactions, keyboard shortcuts, automated SQLite snapshots, and Gemini AI assistant.
- Read more: [mac/README.md](mac/README.md) and [mac/SPEC.md](mac/SPEC.md).

### 2. [Android Mobile (`android/`)](android/README.md)
The native mobile implementation tailored for Android devices.
- **Key Tech**: Kotlin, Jetpack Compose (Material 3), Room (SQLite), Coroutines/Flow, Android WorkManager.
- **Features**: Bottom navigation, quick-entry FAB, touch-friendly charts, biometric security, background workers for recurring bills and backups, and offline-first Room persistence.
- Read more: [android/README.md](android/README.md).

---

## Core Capabilities Across Both Platforms

- **Local-First & Private**: Data stays strictly on your device inside an offline SQLite database.
- **Category Budgets**: Set soft and hard spending limits with visual alert states.
- **Dynamic Rollover**: Unspent funds roll over into savings goals or emergency funds at month-end.
- **Recurring Transactions**: Automated staging and approval workflows for recurring bills and income.
- **Emergency Fund & Savings Goals**: Dedicated tracking and transfer history.
- **AI Assistant**: Optional Google Gemini integration providing conversational insights into your spending without exposing your private database to external servers.

---

## Repository Structure

```text
budgetapp/
├── README.md               # Main project overview (this file)
├── mac/                    # macOS desktop application (Python/CustomTkinter)
│   ├── main.py             # Entry point
│   ├── app/                # Data access, business logic, AI
│   ├── ui/                 # CustomTkinter interface
│   ├── test/               # Test suites
│   ├── BudgetApp.spec      # PyInstaller spec
│   ├── requirements.txt    # Python dependencies
│   ├── SPEC.md             # Architecture spec
│   └── README.md           # Desktop documentation
└── android/                # Native Android application (Kotlin/Jetpack Compose)
    └── README.md           # Android documentation & architecture guide
```
