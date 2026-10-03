# BudgetApp (Android)

BudgetApp for Android is the native mobile implementation of BudgetApp, built with **Kotlin**, **Jetpack Compose**, and **Room (SQLite)**. It brings the full local-first, privacy-focused personal finance workflow from the desktop app to mobile devices.

## Architectural Highlights

- **Local-First & Privacy-Focused**: Single-device storage using Android Room (backed by SQLite). No third-party servers or telemetry.
- **UI Toolkit**: 100% Jetpack Compose using Material 3 design principles, dynamic color theming, and dark/light mode support.
- **Reactive Architecture**: MVVM (Model-View-ViewModel) + Clean Architecture using Kotlin Coroutines and `Flow`.
- **Background Processing**: Android `WorkManager` for daily automated database backups, recurring transaction staging, and month-end rollover checks.
- **Hardware-Backed Security**: EncryptedSharedPreferences backed by Android Keystore for secure Gemini API key storage.
- **AI Assistant**: Conversational financial assistant powered by Google Gemini SDK for Kotlin/Android.

## Features

- **Dashboard**:
  - Key financial metric cards: Available to Spend, Total Spent, Income, Savings, and Emergency Fund.
  - Interactive touch charts (spending pace, category distribution).
  - Category budget bars with soft & hard limit indicators and overflow warnings.
- **Transactions**:
  - Quick-entry floating action button (FAB) or bottom sheet.
  - Split transactions across multiple categories.
  - Pending approval queue for recurring bills.
  - Search, filter by date/category, and CSV export/import via Storage Access Framework (SAF).
- **Savings Goals & Emergency Fund**:
  - Track target dates, savings progress, and transfer logs.
- **Security & Privacy Mode**:
  - Privacy toggle to obscure balances in public.
  - Optional biometric authentication (Fingerprint / Face Unlock).

## Project Structure (Target Layout)

```text
android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/budgetapp/
│   │   │   │   ├── data/             # Room Entities, DAOs, Database, Repositories
│   │   │   │   ├── domain/           # Use cases, budget calculations, recurring engine
│   │   │   │   ├── ui/               # Jetpack Compose screens, ViewModels, theme
│   │   │   │   │   ├── dashboard/
│   │   │   │   │   ├── transactions/
│   │   │   │   │   ├── goals/
│   │   │   │   │   ├── chat/
│   │   │   │   │   └── settings/
│   │   │   │   ├── workers/          # WorkManager background jobs (recurring, backup)
│   │   │   │   └── BudgetApp.kt      # Application class
│   │   │   └── res/                  # Drawables, mipmaps, strings, XML configs
│   │   └── test/                     # Unit and instrumented tests
│   └── build.gradle.kts
├── gradle/
├── build.gradle.kts
└── settings.gradle.kts
```

## Requirements & Building

- Android Studio Ladybug / Meerkat or newer
- Android SDK 34+ (Minimum SDK: 26 / Android 8.0 Oreo)
- JDK 17 or newer

Build via Gradle command line:
```bash
./gradlew assembleDebug
```
