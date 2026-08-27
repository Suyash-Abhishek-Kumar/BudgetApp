"""
main.py — Main application entrypoint.
Initializes the database, constructs the CustomTkinter navigation shell,
and orchestrates page-to-page refresh flows.
"""

from pathlib import Path
import customtkinter as ctk
from app.db import init_db
from app import budget_logic
from ui import theme
from ui.dashboard_screen import DashboardScreen
from ui.transaction_list_screen import TransactionListScreen
from ui.add_transaction_screen import AddTransactionScreen
from ui.settings_screen import SettingsScreen
from ui.chat_screen import ChatScreen


import sys
import os

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

        # Initialize database
        init_db(DB_PATH)

        # Auto-close any un-rolled-over past months silently on startup
        try:
            budget_logic.auto_run_all_past_rollovers(DB_PATH)
        except Exception:
            pass  # Never block startup due to rollover errors

        self._build_sidebar()
        self._build_content_area()

        # Show Dashboard by default
        self.show_screen("Dashboard")


    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=("#ECECEC", "#1E1E1E"))
        sidebar.grid(row=0, column=0, sticky="nsew")
        # Configure row 5 as a stretchable spacer to push Settings down
        sidebar.grid_rowconfigure(5, weight=1)

        # App Logo Title
        logo = ctk.CTkLabel(sidebar, text="💰 BudgetApp", font=theme.FONT_TITLE)
        logo.grid(row=0, column=0, padx=20, pady=(30, 40))

        # Navigation Buttons
        self.nav_buttons = {}
        
        screens = [
            ("Dashboard", "Dashboard"),
            ("Add Transaction", "Add Transaction"),
            ("Transactions", "Transaction List"),
            ("AI Assistant", "🤖 AI Assistant"),
            ("Settings", "Settings")
        ]

        
        for idx, (key, display_name) in enumerate(screens):
            row_num = idx + 1
            pady_val = 8
            sticky_val = "ew"
            if key == "Settings":
                row_num = 6
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

    def _build_content_area(self):
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # Pre-instantiate screens
        self.screens = {
            "Dashboard": DashboardScreen(self.content_frame, DB_PATH),
            "Add Transaction": AddTransactionScreen(self.content_frame, DB_PATH, on_change=self.refresh_all),
            "Transactions": TransactionListScreen(self.content_frame, DB_PATH, on_change=self.refresh_all),
            "AI Assistant": ChatScreen(self.content_frame, DB_PATH),
            "Settings": SettingsScreen(self.content_frame, DB_PATH)
        }


        # Pack all screens invisibly using grid (they'll stack, and we will lift the active one)
        for screen in self.screens.values():
            screen.grid(row=0, column=0, sticky="nsew")
            self.content_frame.grid_columnconfigure(0, weight=1)
            self.content_frame.grid_rowconfigure(0, weight=1)

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

    def refresh_all(self):
        """Refreshes the state across all screens (useful after mutation)."""
        for screen in self.screens.values():
            screen.refresh()


if __name__ == "__main__":
    ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
    ctk.set_default_color_theme("blue")
    
    app = BudgetApp()
    app.mainloop()
