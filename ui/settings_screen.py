"""
settings_screen.py — spec Section 7.4.

Implements the multi-tab Settings screen in CustomTkinter, allowing the user to:
- Manage categories (CRUD with modals).
- Perform manual emergency fund transfers and view deposit/withdrawal logs.
- Configure and manage recurring transaction rules (CRUD with modals).
- Edit global app settings (defaults, warn threshold, EF targets, rollover controls).
"""

from datetime import date
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from app import categories as categories_api
from app import settings as settings_api
from app import emergency_fund as ef_api
from app import recurring as recurring_api
from app import budget_logic
from app.db import get_connection
from app.ai_chat import (
    save_api_key, load_api_key, save_model, load_model,
    has_api_key, AVAILABLE_MODELS, DEFAULT_MODEL
)
from ui import theme



class CategoryDialog(ctk.CTkToplevel):
    """Modal dialog for creating or editing budget categories."""
    def __init__(self, parent, db_path, category=None, on_success=None):
        super().__init__(parent)
        self.db_path = db_path
        self.category = category  # None for create, dict for edit
        self.on_success = on_success
        
        self.title("Edit Category" if category else "New Category")
        self.geometry("400x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # Modal lock
        
        # Center popup relative to parent
        self.update_idletasks()
        p_width = parent.winfo_width()
        p_height = parent.winfo_height()
        p_x = parent.winfo_rootx()
        p_y = parent.winfo_rooty()
        x = p_x + (p_width // 2) - 200
        y = p_y + (p_height // 2) - 160
        self.geometry(f"+{x}+{y}")
        
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        
        # Header
        title_text = "Modify Category" if self.category else "Add Budget Category"
        ctk.CTkLabel(self, text=title_text, font=theme.FONT_SUBTITLE).grid(row=0, column=0, columnspan=2, pady=(20, 15))
        
        # Form Fields
        ctk.CTkLabel(self, text="Category Name", font=theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", padx=20, pady=6)
        self.name_entry = ctk.CTkEntry(self, width=220)
        self.name_entry.grid(row=1, column=1, sticky="w", padx=20, pady=6)
        
        # Set values
        default_soft = settings_api.get_setting("default_soft_limit", self.db_path)
        default_hard = settings_api.get_setting("default_hard_limit", self.db_path)
        
        currency = settings_api.get_setting("currency_symbol", self.db_path) or "₹"
        ctk.CTkLabel(self, text=f"Soft Limit ({currency})", font=theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", padx=20, pady=6)
        self.soft_entry = ctk.CTkEntry(self, width=220, placeholder_text=default_soft)
        self.soft_entry.grid(row=2, column=1, sticky="w", padx=20, pady=6)
        
        ctk.CTkLabel(self, text=f"Hard Limit ({currency})", font=theme.FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", padx=20, pady=6)

        self.hard_entry = ctk.CTkEntry(self, width=220, placeholder_text=default_hard)
        self.hard_entry.grid(row=3, column=1, sticky="w", padx=20, pady=6)
        
        if self.category:
            self.name_entry.insert(0, self.category["name"])
            self.soft_entry.insert(0, str(self.category["soft_limit"]))
            self.hard_entry.insert(0, str(self.category["hard_limit"]))

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(25, 10))
        
        ctk.CTkButton(btn_frame, text="Save", fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER, width=100, command=self._save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, border_color=theme.COLOR_MUTED, text_color=("black", "white"), width=100, command=self.destroy).pack(side="left", padx=10)
        
        self.error_label = ctk.CTkLabel(self, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.error_label.grid(row=5, column=0, columnspan=2, pady=5)

    def _save(self):
        name = self.name_entry.get().strip()
        soft_str = self.soft_entry.get().strip()
        hard_str = self.hard_entry.get().strip()
        
        if not name:
            self.error_label.configure(text="Category name is required.")
            return

        # Parse Soft limit
        try:
            soft = float(soft_str) if soft_str else None
            if soft is not None and soft < 0:
                self.error_label.configure(text="Soft limit must be positive.")
                return
        except ValueError:
            self.error_label.configure(text="Soft limit must be a valid number.")
            return

        # Parse Hard limit
        try:
            hard = float(hard_str) if hard_str else None
            if hard is not None and hard < 0:
                self.error_label.configure(text="Hard limit must be positive.")
                return
        except ValueError:
            self.error_label.configure(text="Hard limit must be a valid number.")
            return

        if soft is not None and hard is not None and hard < soft:
            self.error_label.configure(text="Hard limit must be >= soft limit.")
            return

        try:
            if self.category:
                categories_api.update_category(self.category["id"], name=name, soft_limit=soft, hard_limit=hard, db_path=self.db_path)
            else:
                categories_api.create_category(name, soft_limit=soft, hard_limit=hard, db_path=self.db_path)
            
            if self.on_success:
                self.on_success()
            self.destroy()
        except Exception as e:
            self.error_label.configure(text=f"Failed: {e}")


class RecurringRuleDialog(ctk.CTkToplevel):
    """Modal dialog for creating or editing recurring transaction rules."""
    def __init__(self, parent, db_path, rule=None, on_success=None):
        super().__init__(parent)
        self.db_path = db_path
        self.rule = rule  # None for create, dict for edit
        self.on_success = on_success
        
        self.title("Edit Recurring Rule" if rule else "New Recurring Rule")
        self.geometry("450x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()  # Modal lock
        
        self.update_idletasks()
        p_width = parent.winfo_width()
        p_height = parent.winfo_height()
        p_x = parent.winfo_rootx()
        p_y = parent.winfo_rooty()
        x = p_x + (p_width // 2) - 225
        y = p_y + (p_height // 2) - 220
        self.geometry(f"+{x}+{y}")
        
        self._category_map = {}
        self._build()

    def _build(self):
        # Header
        title_text = "Modify Recurring Rule" if self.rule else "Add Recurring Rule"
        ctk.CTkLabel(self, text=title_text, font=theme.FONT_SUBTITLE).grid(row=0, column=0, columnspan=2, pady=(20, 15))
        
        # Grid settings
        self.grid_columnconfigure(0, weight=0, minsize=140)
        self.grid_columnconfigure(1, weight=1)
        
        row_idx = 0
        def next_row():
            nonlocal row_idx
            row_idx += 1
            return row_idx

        # Variables
        self.type_var = ctk.StringVar(value="expense")
        self.category_var = ctk.StringVar(value="")
        self.amount_var = ctk.StringVar(value="")
        self.desc_var = ctk.StringVar(value="")
        self.freq_var = ctk.StringVar(value="monthly")
        self.interval_var = ctk.StringVar(value="1")
        self.due_var = ctk.StringVar(value=date.today().isoformat())

        self.type_var.trace_add("write", self._on_type_change)
        self.freq_var.trace_add("write", self._on_freq_change)

        # 1. Type
        next_row()
        ctk.CTkLabel(self, text="Rule Type", font=theme.FONT_BODY_BOLD).grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.type_menu = ctk.CTkOptionMenu(self, variable=self.type_var, values=["expense", "income"], width=180)
        self.type_menu.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)

        # 2. Category
        next_row()
        self.cat_label = ctk.CTkLabel(self, text="Category", font=theme.FONT_BODY_BOLD)
        self.cat_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.cat_menu = ctk.CTkOptionMenu(self, variable=self.category_var, values=[], width=180)
        self.cat_menu.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)

        # Populate categories dropdown
        try:
            cats = categories_api.list_categories(self.db_path)
            self._category_map = {c["name"]: c["id"] for c in cats}
            cat_values = list(self._category_map.keys())
            if cat_values:
                self.cat_menu.configure(values=cat_values)
                self.category_var.set(cat_values[0])
        except Exception:
            pass

        currency = settings_api.get_setting("currency_symbol", self.db_path) or "₹"
        ctk.CTkLabel(self, text=f"Amount ({currency})", font=theme.FONT_BODY_BOLD).grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.amount_entry = ctk.CTkEntry(self, textvariable=self.amount_var, width=180)
        self.amount_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)


        # 4. Description
        next_row()
        ctk.CTkLabel(self, text="Description", font=theme.FONT_BODY_BOLD).grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.desc_entry = ctk.CTkEntry(self, textvariable=self.desc_var, width=220, placeholder_text="e.g. Rent, Subscription")
        self.desc_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)

        # 5. Frequency
        next_row()
        ctk.CTkLabel(self, text="Frequency", font=theme.FONT_BODY_BOLD).grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.freq_menu = ctk.CTkOptionMenu(self, variable=self.freq_var, values=["daily", "monthly", "yearly", "custom"], width=180)
        self.freq_menu.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)

        # 6. Custom Interval (custom days)
        next_row()
        self.interval_label = ctk.CTkLabel(self, text="Interval Days", font=theme.FONT_BODY_BOLD)
        self.interval_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.interval_entry = ctk.CTkEntry(self, textvariable=self.interval_var, width=100)
        self.interval_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)
        self.interval_label.grid_remove()
        self.interval_entry.grid_remove()

        # 7. Next Due Date
        next_row()
        ctk.CTkLabel(self, text="Next Due Date", font=theme.FONT_BODY_BOLD).grid(row=row_idx, column=0, sticky="w", padx=20, pady=5)
        self.due_entry = ctk.CTkEntry(self, textvariable=self.due_var, width=180)
        self.due_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=5)

        # Set editing values
        if self.rule:
            self.type_var.set(self.rule["type"])
            self.amount_var.set(str(self.rule["amount"]))
            self.desc_var.set(self.rule["description"] or "")
            self.freq_var.set(self.rule["frequency"])
            self.interval_var.set(str(self.rule["interval_days"] or 1))
            self.due_var.set(self.rule["next_due_date"])
            
            # Map category name
            try:
                if self.rule["category_id"]:
                    cat = categories_api.get_category(self.rule["category_id"], self.db_path)
                    if cat:
                        self.category_var.set(cat["name"])
            except Exception:
                pass

        # Action Buttons
        next_row()
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=(20, 5))
        
        ctk.CTkButton(btn_frame, text="Save", fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER, width=100, command=self._save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="transparent", border_width=1, border_color=theme.COLOR_MUTED, text_color=("black", "white"), width=100, command=self.destroy).pack(side="left", padx=10)
        
        next_row()
        self.error_label = ctk.CTkLabel(self, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.error_label.grid(row=row_idx, column=0, columnspan=2, pady=5)

    def _on_type_change(self, *args):
        if self.type_var.get() == "income":
            self.cat_label.grid_remove()
            self.cat_menu.grid_remove()
        else:
            self.cat_label.grid()
            self.cat_menu.grid()

    def _on_freq_change(self, *args):
        if self.freq_var.get() == "custom":
            self.interval_label.grid()
            self.interval_entry.grid()
        else:
            self.interval_label.grid_remove()
            self.interval_entry.grid_remove()

    def _save(self):
        t = self.type_var.get()
        amount_str = self.amount_var.get().strip()
        desc = self.desc_var.get().strip()
        freq = self.freq_var.get()
        interval_str = self.interval_var.get().strip()
        due = self.due_var.get().strip()

        if not amount_str:
            self.error_label.configure(text="Amount is required.")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                self.error_label.configure(text="Amount must be positive.")
                return
        except ValueError:
            self.error_label.configure(text="Amount must be a number.")
            return

        if not due:
            self.error_label.configure(text="Next due date is required.")
            return
        try:
            date.fromisoformat(due)
        except ValueError:
            self.error_label.configure(text="Date must be YYYY-MM-DD.")
            return

        cat_id = None
        if t == "expense":
            cat_name = self.category_var.get()
            cat_id = self._category_map.get(cat_name)
            if not cat_id:
                self.error_label.configure(text="Select a category.")
                return

        interval_days = None
        if freq == "custom":
            try:
                interval_days = int(interval_str)
                if interval_days <= 0:
                    self.error_label.configure(text="Interval days must be positive.")
                    return
            except ValueError:
                self.error_label.configure(text="Interval days must be an integer.")
                return

        try:
            if self.rule:
                # Update
                recurring_api.update_rule(
                    self.rule["id"],
                    category_id=cat_id,
                    amount=amount,
                    description=desc,
                    rule_type=t,
                    frequency=freq,
                    interval_days=interval_days,
                    next_due_date=due,
                    db_path=self.db_path
                )
            else:
                # Create
                recurring_api.create_rule(
                    category_id=cat_id,
                    amount=amount,
                    description=desc,
                    rule_type=t,
                    frequency=freq,
                    interval_days=interval_days,
                    next_due_date=due,
                    db_path=self.db_path
                )
            if self.on_success:
                self.on_success()
            self.destroy()
        except Exception as e:
            self.error_label.configure(text=f"Failed: {e}")


class SettingsScreen(ctk.CTkFrame):
    def __init__(self, master, db_path):
        super().__init__(master, fg_color="transparent")
        self.db_path = db_path
        self._build()
        self.refresh()

    def _build(self):
        # Header Title
        ctk.CTkLabel(self, text="Settings & Management", font=theme.FONT_TITLE).pack(anchor="w", padx=24, pady=(20, 10))

        # Main Tabview container
        self.tabview = ctk.CTkTabview(self, segmented_button_selected_color=theme.COLOR_PRIMARY)
        self.tabview.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # Add tab panels
        self.tabview.add("Categories")
        self.tabview.add("Emergency Fund")
        self.tabview.add("Recurring Rules")
        self.tabview.add("App Settings")
        self.tabview.add("AI Assistant")

        self._build_categories_tab(self.tabview.tab("Categories"))
        self._build_ef_tab(self.tabview.tab("Emergency Fund"))
        self._build_recurring_tab(self.tabview.tab("Recurring Rules"))
        self._build_global_tab(self.tabview.tab("App Settings"))
        self._build_ai_tab(self.tabview.tab("AI Assistant"))


    # ------------------------------------------------------------ Tab 1: Categories
    def _build_categories_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Header Row
        act_row = ctk.CTkFrame(parent, fg_color="transparent")
        act_row.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(act_row, text="Modify category budgets and soft/hard limits.", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(side="left")
        ctk.CTkButton(
            act_row, 
            text="+ Add Category", 
            fg_color=theme.COLOR_PRIMARY, 
            hover_color=theme.COLOR_PRIMARY_HOVER,
            width=120,
            command=self._add_category
        ).pack(side="right")

        # Scrollable categories list
        self.cat_list_frame = ctk.CTkScrollableFrame(
            parent, 
            fg_color=theme.COLOR_CARD_BG, 
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1, 
            corner_radius=12
        )
        self.cat_list_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

    def _refresh_categories(self):
        for widget in self.cat_list_frame.winfo_children():
            widget.destroy()

        try:
            cats = categories_api.list_categories(self.db_path)
            
            # Draw Table Header
            hdr = ctk.CTkFrame(self.cat_list_frame, fg_color="transparent")
            hdr.pack(fill="x", pady=4, padx=10)
            ctk.CTkLabel(hdr, text="Name", font=theme.FONT_BODY_BOLD, width=150, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Soft Limit", font=theme.FONT_BODY_BOLD, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Hard Limit", font=theme.FONT_BODY_BOLD, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Actions", font=theme.FONT_BODY_BOLD, width=160, anchor="e").pack(side="right")

            # Separator line
            ctk.CTkFrame(self.cat_list_frame, height=2, fg_color=theme.COLOR_CARD_BORDER).pack(fill="x", pady=2, padx=10)

            if not cats:
                ctk.CTkLabel(self.cat_list_frame, text="No categories set up yet.", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(pady=30)
                return

            for c in cats:
                row = ctk.CTkFrame(self.cat_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=6, padx=10)

                ctk.CTkLabel(row, text=c["name"], font=theme.FONT_BODY_BOLD, width=150, anchor="w").pack(side="left")
                currency = settings_api.get_setting("currency_symbol", self.db_path) or "₹"
                ctk.CTkLabel(row, text=f"{currency}{c['soft_limit']:.2f}", font=theme.FONT_BODY, width=120, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=f"{currency}{c['hard_limit']:.2f}", font=theme.FONT_BODY, width=120, anchor="w").pack(side="left")


                # Action buttons
                act_frame = ctk.CTkFrame(row, fg_color="transparent")
                act_frame.pack(side="right")
                
                ctk.CTkButton(
                    act_frame, 
                    text="Edit", 
                    fg_color=theme.COLOR_PRIMARY,
                    hover_color=theme.COLOR_PRIMARY_HOVER,
                    width=70, 
                    command=lambda cat=c: self._edit_category(cat)
                ).pack(side="left", padx=4)
                
                ctk.CTkButton(
                    act_frame, 
                    text="Delete", 
                    fg_color=theme.COLOR_DANGER,
                    hover_color="#922B21", 
                    width=70, 
                    command=lambda cat_id=c["id"]: self._delete_category(cat_id)
                ).pack(side="left", padx=4)

        except Exception as e:
            ctk.CTkLabel(self.cat_list_frame, text=f"Failed to fetch: {e}", font=theme.FONT_BODY, text_color=theme.COLOR_DANGER).pack(pady=30)

    def _add_category(self):
        CategoryDialog(self.winfo_toplevel(), self.db_path, on_success=self.refresh)

    def _edit_category(self, cat):
        CategoryDialog(self.winfo_toplevel(), self.db_path, category=cat, on_success=self.refresh)

    def _delete_category(self, cat_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this category? This cannot be undone."):
            try:
                categories_api.delete_category(cat_id, self.db_path)
                self.refresh()
            except ValueError as e:
                # Pop detailed error message if transactions still exist
                messagebox.showerror("Cannot Delete", str(e))

    # ------------------------------------------------------------ Tab 2: Emergency Fund
    def _build_ef_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # Left: Balance and Transfer
        left_side = ctk.CTkFrame(parent, fg_color="transparent")
        left_side.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Large Balance Indicator card
        bal_card = ctk.CTkFrame(left_side, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        bal_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(bal_card, text="Emergency Fund Balance", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(anchor="w", padx=15, pady=(10, 0))
        self.ef_balance_lbl = ctk.CTkLabel(bal_card, text="₹0.00", font=("Helvetica", 32, "bold"), text_color=theme.COLOR_SUCCESS)
        self.ef_balance_lbl.pack(anchor="w", padx=15, pady=(5, 10))

        # Transfer Form Card
        transfer_card = ctk.CTkFrame(left_side, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        transfer_card.pack(fill="x", pady=0)
        
        ctk.CTkLabel(transfer_card, text="Manual Transfer / Move Money", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 10))
        
        # Form values
        self.ef_amount_var = ctk.StringVar()
        self.ef_dir_var = ctk.StringVar(value="Deposit (from Available)")
        self.ef_note_var = ctk.StringVar()

        # Amount
        f_row1 = ctk.CTkFrame(transfer_card, fg_color="transparent")
        f_row1.pack(fill="x", padx=15, pady=4)
        self.ef_amount_lbl = ctk.CTkLabel(f_row1, text="Amount (₹)", font=theme.FONT_SMALL, width=100, anchor="w")
        self.ef_amount_lbl.pack(side="left")
        ctk.CTkEntry(f_row1, textvariable=self.ef_amount_var, width=160).pack(side="left")

        # Direction Option
        f_row2 = ctk.CTkFrame(transfer_card, fg_color="transparent")
        f_row2.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_row2, text="Direction", font=theme.FONT_SMALL, width=100, anchor="w").pack(side="left")
        self.ef_dir_menu = ctk.CTkOptionMenu(
            f_row2, 
            variable=self.ef_dir_var, 
            values=["Deposit (from Available)", "Withdraw (to Available)"],
            width=190
        )
        self.ef_dir_menu.configure(values=["Deposit (from Available)", "Withdraw (to Available)"])
        self.ef_dir_menu.set("Deposit (from Available)")
        self.ef_dir_menu.pack(side="left")

        # Note
        f_row3 = ctk.CTkFrame(transfer_card, fg_color="transparent")
        f_row3.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_row3, text="Note", font=theme.FONT_SMALL, width=100, anchor="w").pack(side="left")
        ctk.CTkEntry(f_row3, textvariable=self.ef_note_var, width=220, placeholder_text="e.g. initial seed, withdrawal").pack(side="left")

        # Action Trigger
        self.ef_submit_btn = ctk.CTkButton(
            transfer_card, 
            text="Execute Transfer", 
            fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._execute_ef_transfer
        )
        self.ef_submit_btn.pack(anchor="w", padx=15, pady=(15, 10))
        
        self.ef_error_lbl = ctk.CTkLabel(transfer_card, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.ef_error_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        # Right: Logs Panel
        right_side = ctk.CTkFrame(parent, fg_color="transparent")
        right_side.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(right_side, text="Emergency Fund Audit Log (click row for details)", font=theme.FONT_BODY_BOLD).pack(anchor="w", pady=(0, 5))
        
        self.ef_log_container = ctk.CTkScrollableFrame(
            right_side, 
            fg_color=theme.COLOR_CARD_BG, 
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1, 
            corner_radius=12
        )
        self.ef_log_container.pack(fill="both", expand=True)

    def _execute_ef_transfer(self):
        self.ef_error_lbl.configure(text="")
        amt_str = self.ef_amount_var.get().strip()
        dir_input = self.ef_dir_var.get()
        direction = "to_emergency_fund" if "Deposit" in dir_input else "to_savings"
        note = self.ef_note_var.get().strip()

        if not amt_str:
            self.ef_error_lbl.configure(text="Amount is required.", text_color=theme.COLOR_DANGER)
            return

        try:
            amount = float(amt_str)
            if amount <= 0:
                self.ef_error_lbl.configure(text="Amount must be positive.", text_color=theme.COLOR_DANGER)
                return
        except ValueError:
            self.ef_error_lbl.configure(text="Amount must be a number.", text_color=theme.COLOR_DANGER)
            return

        try:
            ef_api.manual_transfer(amount, direction, note=note, db_path=self.db_path)
            self.ef_amount_var.set("")
            self.ef_note_var.set("")
            self.ef_error_lbl.configure(text="Transfer completed successfully! ✅", text_color=theme.COLOR_SUCCESS)
            self.refresh()
        except Exception as e:
            self.ef_error_lbl.configure(text=f"Failed: {e}", text_color=theme.COLOR_DANGER)

    def _show_ef_log_details(self, item):
        currency = settings_api.get_setting("currency_symbol", self.db_path) or "₹"
        val = item["amount"]
        amount_display = f"{'+' if val >= 0 else ''}{currency}{val:.2f}"
        msg = (
            f"Date: {item['date']}\n"
            f"Source: {item['source']}\n"
            f"Amount: {amount_display}\n\n"
            f"Note:\n{item['note'] or '—'}"
        )
        messagebox.showinfo("Log Entry Details", msg)

    def _refresh_ef(self):
        try:
            # Refresh Balance
            currency = settings_api.get_setting("currency_symbol", self.db_path) or "₹"
            self.ef_amount_lbl.configure(text=f"Amount ({currency})")
            bal = ef_api.get_balance(self.db_path)
            self.ef_balance_lbl.configure(text=f"{currency}{bal:.2f}")

            # Refresh log items
            for widget in self.ef_log_container.winfo_children():
                widget.destroy()

            log = ef_api.get_log(limit=50, db_path=self.db_path)
            
            # Log header
            hdr = ctk.CTkFrame(self.ef_log_container, fg_color="transparent")
            hdr.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(hdr, text="Date", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Source", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Amount", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, width=80, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Note", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, anchor="w").pack(side="left")
            
            ctk.CTkFrame(self.ef_log_container, height=1, fg_color=theme.COLOR_CARD_BORDER).pack(fill="x", pady=2)

            if not log:
                ctk.CTkLabel(self.ef_log_container, text="No transfers recorded yet.", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(pady=20)
                return

            for item in log:
                row = ctk.CTkFrame(self.ef_log_container, fg_color="transparent", cursor="hand2")
                row.pack(fill="x", pady=4, padx=5)

                lbl1 = ctk.CTkLabel(row, text=item["date"], font=theme.FONT_SMALL, width=80, anchor="w")
                lbl1.pack(side="left")
                lbl2 = ctk.CTkLabel(row, text=item["source"], font=theme.FONT_SMALL, width=120, anchor="w")
                lbl2.pack(side="left")
                
                # Format positive as deposit and negative as withdrawal
                val = item["amount"]
                display_val = f"{'+' if val >= 0 else ''}{currency}{val:.2f}"
                lbl_color = theme.COLOR_SUCCESS if val >= 0 else theme.COLOR_DANGER
                
                lbl3 = ctk.CTkLabel(row, text=display_val, font=theme.FONT_SMALL, text_color=lbl_color, width=80, anchor="w")
                lbl3.pack(side="left")
                
                raw_note = item["note"] or "—"
                note_display = raw_note[:20] + "…" if len(raw_note) > 20 else raw_note
                lbl4 = ctk.CTkLabel(row, text=note_display, font=theme.FONT_SMALL, anchor="w")
                lbl4.pack(side="left")

                for w in (row, lbl1, lbl2, lbl3, lbl4):
                    w.bind("<Button-1>", lambda e, itm=item: self._show_ef_log_details(itm))
        except Exception as e:
            ctk.CTkLabel(self.ef_log_container, text=f"Failed to refresh EF: {e}", font=theme.FONT_BODY).pack()

    # ------------------------------------------------------------ Tab 3: Recurring Rules
    def _build_recurring_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Header Row
        act_row = ctk.CTkFrame(parent, fg_color="transparent")
        act_row.grid(row=0, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(act_row, text="Create and toggle automated recurring rule logs.", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(side="left")
        ctk.CTkButton(
            act_row, 
            text="+ Add Rule", 
            fg_color=theme.COLOR_PRIMARY, 
            hover_color=theme.COLOR_PRIMARY_HOVER,
            width=120,
            command=self._add_recurring_rule
        ).pack(side="right")

        # Scrollable list
        self.rules_container = ctk.CTkScrollableFrame(
            parent, 
            fg_color=theme.COLOR_CARD_BG, 
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1, 
            corner_radius=12
        )
        self.rules_container.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

    def _refresh_recurring(self):
        for widget in self.rules_container.winfo_children():
            widget.destroy()

        try:
            rules = recurring_api.list_rules(self.db_path)
            cats = categories_api.list_categories(self.db_path)
            cat_name_by_id = {c["id"]: c["name"] for c in cats}

            # Header row
            hdr = ctk.CTkFrame(self.rules_container, fg_color="transparent")
            hdr.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(hdr, text="Description", font=theme.FONT_BODY_BOLD, width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Category", font=theme.FONT_BODY_BOLD, width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Amount", font=theme.FONT_BODY_BOLD, width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Frequency", font=theme.FONT_BODY_BOLD, width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Next Due", font=theme.FONT_BODY_BOLD, width=90, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Status", font=theme.FONT_BODY_BOLD, width=70, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Actions", font=theme.FONT_BODY_BOLD, width=200, anchor="e").pack(side="right")

            ctk.CTkFrame(self.rules_container, height=2, fg_color=theme.COLOR_CARD_BORDER).pack(fill="x", pady=2, padx=10)

            if not rules:
                ctk.CTkLabel(self.rules_container, text="No recurring rules set up yet.", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(pady=35)
                return

            for rule in rules:
                row = ctk.CTkFrame(self.rules_container, fg_color="transparent")
                row.pack(fill="x", pady=6, padx=10)

                desc_text = (rule["description"] or "—")[:14]
                if len(rule["description"] or "") > 14:
                    desc_text += "…"
                ctk.CTkLabel(row, text=desc_text, font=theme.FONT_BODY_BOLD, width=140, anchor="w").pack(side="left")

                
                cat_name = cat_name_by_id.get(rule["category_id"], "— (income)")
                cat_text = cat_name[:13] + "…" if len(cat_name) > 13 else cat_name
                ctk.CTkLabel(row, text=cat_text, font=theme.FONT_BODY, width=110, anchor="w").pack(side="left")

                
                amount_display = f"${rule['amount']:.2f}"
                ctk.CTkLabel(row, text=amount_display, font=theme.FONT_BODY, width=90, anchor="w").pack(side="left")
                
                freq_display = f"{rule['frequency']}"
                if rule['frequency'] == 'custom':
                    freq_display = f"custom ({rule['interval_days']}d)"
                ctk.CTkLabel(row, text=freq_display, font=theme.FONT_BODY, width=100, anchor="w").pack(side="left")

                
                ctk.CTkLabel(row, text=rule["next_due_date"], font=theme.FONT_BODY, width=90, anchor="w").pack(side="left")

                active_text = "Active" if rule["active"] == 1 else "Paused"
                active_color = theme.COLOR_SUCCESS if rule["active"] == 1 else theme.COLOR_MUTED
                ctk.CTkLabel(row, text=active_text, font=theme.FONT_BODY_BOLD, text_color=active_color, width=70, anchor="w").pack(side="left")

                # Action buttons
                act_frame = ctk.CTkFrame(row, fg_color="transparent")
                act_frame.pack(side="right")

                toggle_text = "Pause" if rule["active"] == 1 else "Resume"
                toggle_color = "transparent"
                ctk.CTkButton(
                    act_frame, 
                    text=toggle_text, 
                    fg_color=toggle_color,
                    border_width=1,
                    border_color=theme.COLOR_MUTED,
                    text_color=("black", "white"),
                    width=70, 
                    command=lambda r=rule: self._toggle_recurring_rule(r)
                ).pack(side="left", padx=4)

                ctk.CTkButton(
                    act_frame, 
                    text="Edit", 
                    fg_color=theme.COLOR_PRIMARY,
                    hover_color=theme.COLOR_PRIMARY_HOVER,
                    width=60, 
                    command=lambda r=rule: self._edit_recurring_rule(r)
                ).pack(side="left", padx=4)

                ctk.CTkButton(
                    act_frame, 
                    text="Delete", 
                    fg_color=theme.COLOR_DANGER,
                    hover_color="#922B21", 
                    width=60, 
                    command=lambda rule_id=rule["id"]: self._delete_recurring_rule(rule_id)
                ).pack(side="left", padx=4)

        except Exception as e:
            ctk.CTkLabel(self.rules_container, text=f"Failed to fetch: {e}", font=theme.FONT_BODY, text_color=theme.COLOR_DANGER).pack(pady=35)

    def _add_recurring_rule(self):
        RecurringRuleDialog(self.winfo_toplevel(), self.db_path, on_success=self.refresh)

    def _edit_recurring_rule(self, rule):
        RecurringRuleDialog(self.winfo_toplevel(), self.db_path, rule=rule, on_success=self.refresh)

    def _toggle_recurring_rule(self, rule):
        try:
            new_active = 0 if rule["active"] == 1 else 1
            recurring_api.update_rule(rule["id"], active=new_active, db_path=self.db_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle rule: {e}")

    def _delete_recurring_rule(self, rule_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this recurring rule?"):
            try:
                recurring_api.delete_rule(rule_id, self.db_path)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete rule: {e}")

    # ------------------------------------------------------------ Tab 4: App Settings
    def _build_global_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # Left column: Settings Forms
        left_side = ctk.CTkFrame(parent, fg_color="transparent")
        left_side.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # 1. Config Form Card
        cfg_card = ctk.CTkFrame(left_side, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        cfg_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(cfg_card, text="Thresholds & Settings", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 10))

        # Fields
        self.threshold_category_var = ctk.StringVar()
        self.threshold_soft_var = ctk.StringVar()
        self.threshold_hard_var = ctk.StringVar()
        self.warn_threshold_var = ctk.StringVar()
        self.currency_var = ctk.StringVar()

        rcat = ctk.CTkFrame(cfg_card, fg_color="transparent")
        rcat.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(rcat, text="Category Selection", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        self.threshold_category_menu = ctk.CTkOptionMenu(
            rcat, 
            variable=self.threshold_category_var, 
            values=[], 
            width=120,
            command=self._on_threshold_category_change
        )
        self.threshold_category_menu.pack(side="left")

        r2 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        r2.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(r2, text="Category Soft Limit ($)", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(r2, textvariable=self.threshold_soft_var, width=120).pack(side="left")

        r3 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        r3.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(r3, text="Category Hard Limit ($)", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(r3, textvariable=self.threshold_hard_var, width=120).pack(side="left")

        r1 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        r1.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(r1, text="Warn Threshold ($)", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(r1, textvariable=self.warn_threshold_var, width=120).pack(side="left")

        r4 = ctk.CTkFrame(cfg_card, fg_color="transparent")
        r4.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(r4, text="Currency Symbol", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(r4, textvariable=self.currency_var, width=120).pack(side="left")

        ctk.CTkButton(cfg_card, text="Save Config", fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER, command=self._save_globals).pack(anchor="w", padx=15, pady=(15, 10))


        # 2. Emergency Fund automation configurations
        ef_cfg_card = ctk.CTkFrame(left_side, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        ef_cfg_card.pack(fill="x", pady=0)
        ctk.CTkLabel(ef_cfg_card, text="Emergency Fund Automation Config", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 10))

        self.ef_target_var = ctk.StringVar()
        self.ef_contribution_var = ctk.StringVar()
        self.ef_contrib_type_var = ctk.StringVar(value="fixed")

        er1 = ctk.CTkFrame(ef_cfg_card, fg_color="transparent")
        er1.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(er1, text="Target Amount ($)", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(er1, textvariable=self.ef_target_var, width=120).pack(side="left")

        er2 = ctk.CTkFrame(ef_cfg_card, fg_color="transparent")
        er2.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(er2, text="Monthly Contribution", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkEntry(er2, textvariable=self.ef_contribution_var, width=120).pack(side="left")

        er3 = ctk.CTkFrame(ef_cfg_card, fg_color="transparent")
        er3.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(er3, text="Contribution Type", font=theme.FONT_SMALL, width=160, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(er3, variable=self.ef_contrib_type_var, values=["fixed", "percent"], width=120).pack(side="left")

        ctk.CTkButton(ef_cfg_card, text="Save EF Config", fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER, command=self._save_ef_config).pack(anchor="w", padx=15, pady=(15, 10))

        # Right column: Rollovers & History
        right_side = ctk.CTkFrame(parent, fg_color="transparent")
        right_side.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Trigger button
        roll_card = ctk.CTkFrame(right_side, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        roll_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(roll_card, text="Savings Closeout & Rollover", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 5))
        ctk.CTkLabel(roll_card, text="Process month-end savings rollover jobs.", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED).pack(anchor="w", padx=15, pady=(0, 10))
        
        ctk.CTkButton(
            roll_card, 
            text="Process Past Rollovers", 
            fg_color=theme.COLOR_SUCCESS, 
            hover_color="#449D44",
            command=self._manual_rollover_trigger
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # Savings Balance Adjustment card
        adj_card = ctk.CTkFrame(right_side, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        adj_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(adj_card, text="Adjust Savings Balance", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 2))
        ctk.CTkLabel(
            adj_card,
            text="Manually correct savings (e.g. to reverse a rolled-over transaction you deleted).",
            font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, wraplength=320, justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 8))

        self.savings_adj_amount_var = tk.StringVar()
        self.savings_adj_dir_var = tk.StringVar(value="withdraw")

        adj_row1 = ctk.CTkFrame(adj_card, fg_color="transparent")
        adj_row1.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(adj_row1, text="Amount ($)", font=theme.FONT_SMALL, width=120, anchor="w").pack(side="left")
        ctk.CTkEntry(adj_row1, textvariable=self.savings_adj_amount_var, width=100, placeholder_text="0.00").pack(side="left")

        adj_row2 = ctk.CTkFrame(adj_card, fg_color="transparent")
        adj_row2.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(adj_row2, text="Direction", font=theme.FONT_SMALL, width=120, anchor="w").pack(side="left")
        ctk.CTkOptionMenu(adj_row2, variable=self.savings_adj_dir_var, values=["withdraw", "deposit"], width=100).pack(side="left")

        ctk.CTkButton(
            adj_card, text="Apply Adjustment",
            fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._execute_savings_adjust
        ).pack(anchor="w", padx=15, pady=(10, 4))

        self.savings_adj_status = ctk.CTkLabel(adj_card, text="", font=theme.FONT_SMALL)
        self.savings_adj_status.pack(anchor="w", padx=15, pady=(0, 10))

        # Savings Rollover table list
        ctk.CTkLabel(right_side, text="Savings History", font=theme.FONT_BODY_BOLD).pack(anchor="w", pady=(5, 5))
        self.savings_history_container = ctk.CTkScrollableFrame(
            right_side,
            fg_color=theme.COLOR_CARD_BG,
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12
        )
        self.savings_history_container.pack(fill="both", expand=True)


    def _execute_savings_adjust(self):
        self.savings_adj_status.configure(text="")
        amt_str = self.savings_adj_amount_var.get().strip()
        direction = self.savings_adj_dir_var.get()
        if not amt_str:
            self.savings_adj_status.configure(text="Amount is required.", text_color=theme.COLOR_DANGER)
            return
        try:
            amount = float(amt_str)
            if amount <= 0:
                self.savings_adj_status.configure(text="Amount must be positive.", text_color=theme.COLOR_DANGER)
                return
        except ValueError:
            self.savings_adj_status.configure(text="Amount must be a number.", text_color=theme.COLOR_DANGER)
            return
        try:
            signed = -amount if direction == "withdraw" else amount
            budget_logic.adjust_savings_balance(signed, db_path=self.db_path)
            self.savings_adj_amount_var.set("")
            self.savings_adj_status.configure(
                text=f"✅ {'Withdrew' if direction == 'withdraw' else 'Deposited'} ${amount:.2f} {'from' if direction == 'withdraw' else 'to'} savings.",
                text_color=theme.COLOR_SUCCESS
            )
            self.refresh()
        except Exception as e:
            self.savings_adj_status.configure(text=f"Failed: {e}", text_color=theme.COLOR_DANGER)

    def _on_threshold_category_change(self, selected_name):

        cat = self._threshold_categories.get(selected_name)
        if cat:
            self.threshold_soft_var.set(f"{cat['soft_limit']:.2f}")
            self.threshold_hard_var.set(f"{cat['hard_limit']:.2f}")
        else:
            self.threshold_soft_var.set("")
            self.threshold_hard_var.set("")

    def _save_globals(self):
        try:
            # 1. Update selected category limits
            selected_name = self.threshold_category_var.get()
            cat = self._threshold_categories.get(selected_name)
            if cat:
                soft = float(self.threshold_soft_var.get())
                hard = float(self.threshold_hard_var.get())
                if soft < 0 or hard < 0 or hard < soft:
                    messagebox.showerror("Error", "Verify category limits are positive and Hard Limit >= Soft Limit.")
                    return
                categories_api.update_category(cat["id"], name=cat["name"], soft_limit=soft, hard_limit=hard, db_path=self.db_path)
            
            # 2. Update global settings
            settings_api.set_setting("hard_limit_warn_threshold", float(self.warn_threshold_var.get()), self.db_path)
            settings_api.set_setting("currency_symbol", self.currency_var.get().strip(), self.db_path)
            messagebox.showinfo("Success", "Settings & Category Limits updated successfully! ✅")
            self.refresh()
        except ValueError:
            messagebox.showerror("Error", "Verify limit/threshold values are numeric.")


    def _save_ef_config(self):
        try:
            settings_api.set_setting("ef_target_amount", float(self.ef_target_var.get()), self.db_path)
            settings_api.set_setting("ef_monthly_contribution", float(self.ef_contribution_var.get()), self.db_path)
            settings_api.set_setting("ef_monthly_contribution_type", self.ef_contrib_type_var.get(), self.db_path)
            messagebox.showinfo("Success", "Emergency fund automation saved successfully! ✅")
            self.refresh()
        except ValueError:
            messagebox.showerror("Error", "Verify target/monthly values are numeric.")

    def _manual_rollover_trigger(self):
        try:
            rolled = budget_logic.auto_run_all_past_rollovers(self.db_path)
            if rolled:
                messagebox.showinfo("Rollover Processed", f"Successfully rolled over months: {', '.join(rolled)} ✅")
            else:
                messagebox.showinfo("Rollover Up-to-Date", "All past months are already rolled over and closed out. No actions required.")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Rollover Failed", f"Rollover error: {e}")

    def _refresh_globals(self):
        # Fetch configurations
        cfg = settings_api.all_settings(self.db_path)
        self.warn_threshold_var.set(cfg.get("hard_limit_warn_threshold", "50"))
        self.currency_var.set(cfg.get("currency_symbol", "$"))

        self.ef_target_var.set(cfg.get("ef_target_amount", "1000"))
        self.ef_contribution_var.set(cfg.get("ef_monthly_contribution", "50"))
        self.ef_contrib_type_var.set(cfg.get("ef_monthly_contribution_type", "fixed"))

        # Populate category dropdown
        try:
            cats = categories_api.list_categories(self.db_path)
            self._threshold_categories = {c["name"]: c for c in cats}
            cat_names = list(self._threshold_categories.keys())
            
            if cat_names:
                self.threshold_category_menu.configure(values=cat_names)
                # If currently selected category name is no longer valid, default to first
                current_selected = self.threshold_category_var.get()
                if not current_selected or current_selected not in self._threshold_categories:
                    current_selected = cat_names[0]
                    self.threshold_category_var.set(current_selected)
                
                # Update limits entries
                self._on_threshold_category_change(current_selected)
            else:
                self.threshold_category_menu.configure(values=["No categories created"])
                self.threshold_category_var.set("No categories created")
                self.threshold_soft_var.set("")
                self.threshold_hard_var.set("")
        except Exception:
            pass


        # Fetch savings log
        for widget in self.savings_history_container.winfo_children():
            widget.destroy()

        try:
            # Query savings database
            conn = get_connection(self.db_path)
            try:
                rows = conn.execute("SELECT * FROM savings ORDER BY month DESC").fetchall()
            finally:
                conn.close()

            hdr = ctk.CTkFrame(self.savings_history_container, fg_color="transparent")
            hdr.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(hdr, text="Month", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="Saved Rollover", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(hdr, text="EF Diverted", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED, anchor="w").pack(side="left")

            ctk.CTkFrame(self.savings_history_container, height=1, fg_color=theme.COLOR_CARD_BORDER).pack(fill="x", pady=2)

            if not rows:
                ctk.CTkLabel(self.savings_history_container, text="No savings logs recorded yet.", font=theme.FONT_BODY, text_color=theme.COLOR_MUTED).pack(pady=20)
                return

            for r in rows:
                row = ctk.CTkFrame(self.savings_history_container, fg_color="transparent")
                row.pack(fill="x", pady=4, padx=5)

                ctk.CTkLabel(row, text=r["month"], font=theme.FONT_SMALL, width=120, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=f"${r['rollover_amount']:.2f}", font=theme.FONT_SMALL, text_color=theme.COLOR_SUCCESS, width=120, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=f"${r['emergency_fund_delta']:.2f}", font=theme.FONT_SMALL, text_color=theme.COLOR_PRIMARY, anchor="w").pack(side="left")

        except Exception as e:
            ctk.CTkLabel(self.savings_history_container, text=f"Failed to fetch savings logs: {e}", font=theme.FONT_SMALL).pack()

    # ------------------------------------------------------------ Tab 5: AI Assistant
    def _build_ai_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        scroll.columnconfigure(0, weight=1)

        # ── API Key section ──────────────────────────────────────────────────
        key_card = ctk.CTkFrame(scroll, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        key_card.pack(fill="x", pady=(10, 6), padx=4)
        key_card.columnconfigure(1, weight=1)

        ctk.CTkLabel(key_card, text="Gemini API Key", font=theme.FONT_SUBTITLE).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 4)
        )
        ctk.CTkLabel(
            key_card,
            text="Your key is encrypted using AES-128 before being stored locally on this machine.",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_MUTED,
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(key_card, text="API Key", font=theme.FONT_BODY_BOLD).grid(
            row=2, column=0, sticky="w", padx=20, pady=8
        )
        self._ai_key_var = tk.StringVar()
        self._ai_key_entry = ctk.CTkEntry(
            key_card,
            textvariable=self._ai_key_var,
            placeholder_text="AIza…",
            show="•",
            width=340,
        )
        self._ai_key_entry.grid(row=2, column=1, sticky="w", padx=20, pady=8)

        key_btn_row = ctk.CTkFrame(key_card, fg_color="transparent")
        key_btn_row.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(4, 16))

        ctk.CTkButton(
            key_btn_row,
            text="Save API Key",
            fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._save_ai_key,
        ).pack(side="left")

        ctk.CTkButton(
            key_btn_row,
            text="Show / Hide",
            fg_color="transparent",
            border_color=theme.COLOR_MUTED,
            border_width=1,
            text_color=("black", "white"),
            command=self._toggle_key_visibility,
        ).pack(side="left", padx=10)

        self._ai_key_status = ctk.CTkLabel(key_card, text="", font=theme.FONT_SMALL)
        self._ai_key_status.grid(row=4, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))

        # ── Model selection ──────────────────────────────────────────────────
        model_card = ctk.CTkFrame(scroll, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=12)
        model_card.pack(fill="x", pady=6, padx=4)
        model_card.columnconfigure(1, weight=1)

        ctk.CTkLabel(model_card, text="Model", font=theme.FONT_SUBTITLE).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 4)
        )

        ctk.CTkLabel(model_card, text="Gemini Model", font=theme.FONT_BODY_BOLD).grid(
            row=1, column=0, sticky="w", padx=20, pady=8
        )
        self._ai_model_var = tk.StringVar(value=DEFAULT_MODEL)
        self._ai_model_menu = ctk.CTkOptionMenu(
            model_card,
            variable=self._ai_model_var,
            values=AVAILABLE_MODELS,
            width=240,
        )
        self._ai_model_menu.grid(row=1, column=1, sticky="w", padx=20, pady=8)

        ctk.CTkButton(
            model_card,
            text="Save Model",
            fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._save_ai_model,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(4, 16))

        self._ai_model_status = ctk.CTkLabel(model_card, text="", font=theme.FONT_SMALL)
        self._ai_model_status.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))

    def _toggle_key_visibility(self):
        current = self._ai_key_entry.cget("show")
        self._ai_key_entry.configure(show="" if current == "•" else "•")

    def _save_ai_key(self):
        key = self._ai_key_var.get().strip()
        if not key:
            self._ai_key_status.configure(text="Please enter an API key.", text_color=theme.COLOR_DANGER)
            return
        try:
            save_api_key(key, self.db_path)
            self._ai_key_var.set("")  # Clear field after saving for security
            self._ai_key_entry.configure(show="•")
            self._ai_key_status.configure(text="✅ API key saved and encrypted.", text_color=theme.COLOR_SUCCESS)
        except Exception as e:
            self._ai_key_status.configure(text=f"Error: {e}", text_color=theme.COLOR_DANGER)

    def _save_ai_model(self):
        model = self._ai_model_var.get()
        try:
            save_model(model, self.db_path)
            self._ai_model_status.configure(text=f"✅ Model set to {model}.", text_color=theme.COLOR_SUCCESS)
        except Exception as e:
            self._ai_model_status.configure(text=f"Error: {e}", text_color=theme.COLOR_DANGER)

    def _refresh_ai(self):
        """Load current AI settings into the tab fields."""
        try:
            current_model = load_model(self.db_path)
            self._ai_model_var.set(current_model)
            if has_api_key(self.db_path):
                self._ai_key_status.configure(
                    text="🔐 An encrypted API key is stored on this device.",
                    text_color=theme.COLOR_MUTED,
                )
            else:
                self._ai_key_status.configure(
                    text="No API key configured yet.",
                    text_color=theme.COLOR_WARNING,
                )
        except Exception:
            pass

    # ------------------------------------------------------------ Main Coordinator
    def refresh(self):
        """Public refresher coordinate to reload databases across panels."""
        self._refresh_categories()
        self._refresh_ef()
        self._refresh_recurring()
        self._refresh_globals()
        self._refresh_ai()
