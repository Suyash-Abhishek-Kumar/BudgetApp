# BudgetApp (Android)

BudgetApp for Android is the native mobile implementation of BudgetApp, built with **Kotlin**, **Jetpack Compose (Material 3)**, and **Room (SQLite)**. It delivers full feature parity with the macOS desktop application while taking full advantage of modern Android mobile design patterns.

---

## Architectural Highlights

- **Local-First & Privacy-Focused**: Single-device storage using Android Room (backed by SQLite). No third-party servers, telemetry, or external trackers.
- **UI Toolkit**: 100% Jetpack Compose using Material 3 design principles with density-independent, adaptive layouts tailored for all screen ratios (including tall 19:9/20:9 displays).
- **FinTech Aesthetic**: Cobalt and Sapphire primary palette (`#2563EB` / `#1D4ED8` / `#60A5FA`), deep Slate surface hierarchies (`#0F172A`, `#1E293B`, `#F8FAFC`), and custom adaptive vector launcher icons.
- **Reactive Architecture**: MVVM (Model-View-ViewModel) + Clean Architecture powered by Kotlin Coroutines and Kotlin `Flow`.
- **Background Processing**: Android `WorkManager` for daily automated database backups, recurring transaction staging, and month-end rollover checks.
- **Hardware-Backed Security**: Encrypted SharedPreferences with Android Keystore for secure Gemini API key storage.
- **AI Financial Assistant**: Conversational assistant powered by Google Gemini SDK for Kotlin, operating on locally computed financial context.

---

## Key Features

### 1. Dashboard & Analytics
- **Executive KPI Cards**: Available to Spend, Total Spent, Monthly Income, Emergency Fund, and Savings balance.
- **Spending Pace & Forecast Chart**:
  - Native Canvas line chart with explicit X and Y coordinate axes, gridlines, and numeric ticks.
  - Interactive touch scrubbing to inspect cumulative spending by day.
  - Visual baseline comparisons against linear daily pace and monthly hard limits.
- **Spending Breakdown Donut / Pie Chart**:
  - Canvas-drawn slices with percentage callouts and centered total spent indicator.
  - Interactive slice tapping to filter trends and ledger items by category.
- **6-Month Historical Spending Trend Chart**:
  - Grouped bar chart comparing total spending against rollover to savings over the preceding 6 months.
- **Time Machine Month Switcher**:
  - Jump back to view past closed months or the current active month directly from the top bar.
  - Clear read-only warning banners when inspecting past archived months.

### 2. Transaction Management & Ledger
- **Quick-Entry FAB**: Fast bottom-sheet dialog for recording income, expenses, and split transactions.
- **Income Source Support**: Select dedicated income categories or general income sources with funding source assignment.
- **Recurring Transactions**: Rule-based scheduling with pending approval queues.
- **Search & Filter**: Filter by keyword, month, last 30 days, income, or expenses.
- **CSV Data Portability**: Import and export transactions via Android Storage Access Framework (SAF).

### 3. Settings & Archives
- **General Tab**: Currency symbol switcher (`$`, `₹`, `€`, `£`, `¥`), Privacy Mode toggle (masks amounts with bullets), and manual rollover engine trigger.
- **Categories Tab**: Create and edit categories with soft budget limits and hard overflow limits.
- **Emergency Fund Tab**: Balance tracking, quick deposit/withdrawal dialogs, and comprehensive activity history logs.
- **Recurring Tab**: Manage recurring rule schedules (frequency, next due date, category, funding source).
- **Archives Tab**: Ledger of all closed past months displaying income, expense, savings rollover, and emergency fund delta pills, with a direct **View in Dashboard ↗** shortcut.
- **Backups Tab**: Snapshot creation and restoration of SQLite databases directly from device storage.

---

## Project Structure

```text
android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/budgetapp/
│   │   │   │   ├── data/
│   │   │   │   │   ├── local/          # Room Database, DAOs, and Entities
│   │   │   │   │   └── repository/     # BudgetRepository & data layer coordination
│   │   │   │   ├── domain/             # BudgetCalculator, CsvEngine, GeminiAssistant, Models
│   │   │   │   ├── ui/
│   │   │   │   │   ├── dashboard/      # DashboardScreen, Charts (Pace, Pie, Trend)
│   │   │   │   │   ├── transactions/   # TransactionListScreen, Add/Edit dialogs
│   │   │   │   │   ├── goals/          # SavingsGoalsScreen, contribution dialogs
│   │   │   │   │   ├── chat/           # ChatScreen, API key dialog
│   │   │   │   │   ├── settings/       # SettingsScreen (General, Categories, EF, Recurring, Archives, Backups)
│   │   │   │   │   └── theme/          # Color, Theme, Type
│   │   │   │   ├── workers/            # WorkManager workers (RecurringWorker, BackupWorker)
│   │   │   │   ├── MainActivity.kt     # Main entry point & scaffold
│   │   │   │   └── BudgetApplication.kt# Application lifecycle initialization
│   │   │   ├── res/
│   │   │   │   ├── drawable/           # Vector assets & adaptive icon components
│   │   │   │   ├── mipmap-anydpi-v26/  # Adaptive launcher icon XML definitions
│   │   │   │   └── values/             # App name, theme XMLs
│   │   │   └── AndroidManifest.xml     # App permissions, icon, and Activity declarations
│   │   └── test/
│   └── build.gradle.kts                # App module build configuration
├── gradle/
│   ├── wrapper/                        # Gradle wrapper binaries
│   └── libs.versions.toml              # Version catalog
├── build.gradle.kts                    # Root build configuration
└── settings.gradle.kts                 # Project settings & repositories
```

---

## Requirements & Building

- **Android Studio**: Android Studio Ladybug / Meerkat (or newer)
- **Android SDK**: API 34+ (Target SDK: 34, Minimum SDK: 26 / Android 8.0 Oreo)
- **JDK**: Java 17 or Java 21 LTS

### Build Debug APK
```bash
./gradlew assembleDebug
```
The output APK is generated at `app/build/outputs/apk/debug/app-debug.apk`.

### Run Unit Tests
```bash
./gradlew test
```
