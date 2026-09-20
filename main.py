"""
main.py — Main application entrypoint.
Initializes the database, constructs the CustomTkinter navigation shell,
and orchestrates page-to-page refresh flows.
"""

import sys
import os
from pathlib import Path
import customtkinter as ctk
from app.db import init_db
from app import budget_logic, backup as backup_api, recurring as recurring_api
from ui import theme
from ui.dashboard_screen import DashboardScreen
from ui.transaction_list_screen import TransactionListScreen
from ui.add_transaction_screen import AddTransactionScreen
from ui.settings_screen import SettingsScreen
from ui.chat_screen import ChatScreen
from ui.savings_goals_screen import SavingsGoalsScreen

# Resolve the database path dynamically:
# - If packaged as a standalone app, save to the standard macOS Application Support folder.
# - Otherwise, use the local development database in the project directory.
if getattr(sys, 'frozen', False):
    app_support = Path(os.path.expanduser("~/Library/Application Support/BudgetApp"))
    app_support.mkdir(parents=True, exist_ok=True)
    DB_PATH = app_support / "budget.db"
else:
    DB_PATH = Path(__file__).parent / "budget.db"


class BudgetApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Personal Budget Tracker")
        self.geometry("1280x720")

        # Configure grid layout: Left Sidebar (width 220), Right Content (expandable)
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.is_privacy_mode = False

        # Initialize database
        init_db(DB_PATH)

        # Auto-close any un-rolled-over past months silently on startup
        try:
            budget_logic.auto_run_all_past_rollovers(DB_PATH)
        except Exception:
            pass  # Never block startup due to rollover errors

        # Process any due recurring transactions into pending_approval on startup
        try:
            recurring_api.process_due_recurring_transactions(db_path=DB_PATH)
        except Exception:
            pass

        # Automated daily backup on startup
        try:
            backup_api.auto_backup_on_startup(DB_PATH)
        except Exception:
            pass

        self._build_sidebar()
        self._build_content_area()
        self._bind_shortcuts()

        # Show Dashboard by default
        self.show_screen("Dashboard")

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=("#ECECEC", "#1E1E1E"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        # Configure row 6 as a stretchable spacer to push Settings & Privacy button down
        sidebar.grid_rowconfigure(6, weight=1)

        # App Logo Title
        logo = ctk.CTkLabel(sidebar, text="💰 BudgetApp", font=theme.FONT_TITLE)
        logo.grid(row=0, column=0, padx=20, pady=(30, 40))

        # Navigation Buttons
        self.nav_buttons = {}
        
        screens = [
            ("Dashboard", "Dashboard"),
            ("Add Transaction", "Add Transaction"),
            ("Transactions", "Transaction List"),
            ("Savings Goals", "🎯 Savings Goals"),
            ("AI Assistant", "🤖 AI Assistant"),
            ("Settings", "Settings")
        ]

        for idx, (key, display_name) in enumerate(screens):
            row_num = idx + 1
            pady_val = 8
            sticky_val = "ew"
            if key == "Settings":
                row_num = 8
                pady_val = (0, 20)  # Extra spacing at the bottom
                sticky_val = "sew"  # Align to the bottom

            btn = ctk.CTkButton(
                sidebar,
                text=display_name,
                font=theme.FONT_BODY_BOLD,
                fg_color="transparent",
                text_color=("black", "white"),
                hover_color=("#D4D4D4", "#2E2E2E"),
                anchor="w",
                height=40,
                command=lambda k=key: self.show_screen(k)
            )
            btn.grid(row=row_num, column=0, sticky=sticky_val, padx=15, pady=pady_val)
            self.nav_buttons[key] = btn

        # Privacy Mode Toggle Button (above Settings)
        self.privacy_btn = ctk.CTkButton(
            sidebar,
            text="👁️ Hide Amounts",
            font=theme.FONT_SMALL,
            fg_color="transparent",
            border_width=1,
            border_color=("#CCCCCC", "#3E3E3E"),
            text_color=("black", "white"),
            hover_color=("#D4D4D4", "#2E2E2E"),
            height=32,
            command=self.toggle_privacy_mode
        )
        self.privacy_btn.grid(row=7, column=0, sticky="ew", padx=15, pady=(0, 10))

    def _build_content_area(self):
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Pre-instantiate screens
        self.screens = {
            "Dashboard": DashboardScreen(self.content_frame, DB_PATH),
            "Add Transaction": AddTransactionScreen(self.content_frame, DB_PATH, on_change=self.refresh_all),
            "Transactions": TransactionListScreen(self.content_frame, DB_PATH, on_change=self.refresh_all),
            "Savings Goals": SavingsGoalsScreen(self.content_frame, DB_PATH, on_change=self.refresh_all),
            "AI Assistant": ChatScreen(self.content_frame, DB_PATH, on_change=self.refresh_all),
            "Settings": SettingsScreen(self.content_frame, DB_PATH, on_view_archive=self.view_archived_month)
        }

        # Pack all screens invisibly using grid (they'll stack, and we will lift the active one)
        for screen in self.screens.values():
            screen.grid(row=0, column=0, sticky="nsew")
            self.content_frame.grid_columnconfigure(0, weight=1)
            self.content_frame.grid_rowconfigure(0, weight=1)

    def _bind_shortcuts(self):
        """Binds universal desktop keyboard shortcuts across macOS and Windows/Linux."""
        # Screen switching shortcuts: Cmd+1..6 / Ctrl+1..6
        screen_keys = [
            ("1", "Dashboard"),
            ("2", "Add Transaction"),
            ("3", "Transactions"),
            ("4", "Savings Goals"),
            ("5", "AI Assistant"),
            ("6", "Settings"),
        ]
        for num, key in screen_keys:
            self.bind_all(f"<Command-Key-{num}>", lambda e, k=key: self._on_switch_screen(k))
            self.bind_all(f"<Control-Key-{num}>", lambda e, k=key: self._on_switch_screen(k))

        # Quick action shortcuts:
        # Cmd/Ctrl + N: New Transaction & focus amount
        for mod in ("Command", "Control"):
            self.bind_all(f"<{mod}-n>", self._on_shortcut_new_transaction)
            self.bind_all(f"<{mod}-N>", self._on_shortcut_new_transaction)
            # Cmd/Ctrl + F: Find / Search Transactions & focus search
            self.bind_all(f"<{mod}-f>", self._on_shortcut_find_transactions)
            self.bind_all(f"<{mod}-F>", self._on_shortcut_find_transactions)
            # Cmd/Ctrl + R: Refresh All
            self.bind_all(f"<{mod}-r>", self._on_shortcut_refresh)
            self.bind_all(f"<{mod}-R>", self._on_shortcut_refresh)
            # Cmd/Ctrl + P: Toggle Privacy Mode
            self.bind_all(f"<{mod}-p>", self._on_shortcut_privacy)
            self.bind_all(f"<{mod}-P>", self._on_shortcut_privacy)

    def _on_switch_screen(self, screen_key: str):
        self.show_screen(screen_key)
        return "break"

    def _on_shortcut_new_transaction(self, event=None):
        self.show_screen("Add Transaction")
        add_screen = self.screens.get("Add Transaction")
        if hasattr(add_screen, "amount_entry"):
            add_screen.amount_entry.focus_set()
        return "break"

    def _on_shortcut_find_transactions(self, event=None):
        self.show_screen("Transactions")
        tx_screen = self.screens.get("Transactions")
        if hasattr(tx_screen, "search_entry"):
            tx_screen.search_entry.focus_set()
        return "break"

    def _on_shortcut_refresh(self, event=None):
        self.refresh_all()
        return "break"

    def _on_shortcut_privacy(self, event=None):
        self.toggle_privacy_mode()
        return "break"

    def toggle_privacy_mode(self, event=None):
        """Toggles masking of financial balances and amounts across all views."""
        self.is_privacy_mode = not self.is_privacy_mode
        if self.is_privacy_mode:
            self.privacy_btn.configure(text="🔒 Privacy: ON", fg_color=("#E0E0E0", "#2E2E2E"))
        else:
            self.privacy_btn.configure(text="👁️ Hide Amounts", fg_color="transparent")

        for screen in self.screens.values():
            if hasattr(screen, "set_privacy_mode"):
                screen.set_privacy_mode(self.is_privacy_mode)

        self.refresh_all()
        return "break"

    def show_screen(self, key):
        """Displays the selected screen and highlights the navigation button."""
        # Highlight active button, dim others
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=theme.COLOR_PRIMARY, text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color=("black", "white"))

        # Lift the selected screen to the top
        selected_screen = self.screens.get(key)
        if selected_screen:
            selected_screen.lift()
            # Refresh screen contents when it becomes visible
            selected_screen.refresh()

    def view_archived_month(self, month):
        """Switches to Dashboard and selects the specified archived month."""
        self.show_screen("Dashboard")
        dashboard = self.screens.get("Dashboard")
        if dashboard and hasattr(dashboard, "set_active_month"):
            dashboard.set_active_month(month)

    def refresh_all(self):
        """Refreshes the state across all screens (useful after mutation)."""
        try:
            recurring_api.process_due_recurring_transactions(db_path=DB_PATH)
        except Exception:
            pass
        for screen in self.screens.values():
            screen.refresh()


if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
    ctk.set_default_color_theme("blue")
    
    app = BudgetApp()
    app.mainloop()
