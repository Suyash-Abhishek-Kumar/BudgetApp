"""
add_transaction_screen.py — spec Section 7.2.

Provides a form to add a new transaction (expense or income), populated with 
categories from the database, and displays live feedback (limit warnings and
translucent savings overflow banner) before committing the transaction.
"""

from datetime import date
import customtkinter as ctk
from app import categories as categories_api
from app import transactions as transactions_api
from ui import theme
from ui.calendar_picker import CalendarPicker


class AddTransactionScreen(ctk.CTkFrame):
    def __init__(self, master, db_path, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.db_path = db_path
        self.on_change = on_change
        
        self._category_map = {}  # name -> id
        self._category_names = []
        
        self._build()
        self.refresh()

    def _build(self):
        # Title
        ctk.CTkLabel(self, text="Add Transaction", font=theme.FONT_TITLE).pack(
            anchor="w", padx=24, pady=(20, 10)
        )

        # Main scrollable container (to fit banner + form comfortably)
        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        # --- Dynamic Warning/Overflow Banner ---
        self.banner_frame = ctk.CTkFrame(
            self.container, 
            fg_color=theme.COLOR_BANNER_BG, 
            border_color=theme.COLOR_BANNER_BORDER,
            border_width=1,
            corner_radius=8
        )
        # We start with banner hidden
        self.banner_label = ctk.CTkLabel(
            self.banner_frame, 
            text="", 
            font=theme.FONT_BODY_BOLD, 
            text_color=theme.COLOR_BANNER_TEXT,
            anchor="w",
            padx=12,
            pady=12
        )
        self.banner_label.pack(fill="x", expand=True)

        # --- Form Card ---
        form_card = ctk.CTkFrame(
            self.container, 
            fg_color=theme.COLOR_CARD_BG, 
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12
        )
        form_card.pack(fill="x", pady=10)

        # Variables
        self.type_var = ctk.StringVar(value="expense")
        self.category_var = ctk.StringVar(value="")
        self.amount_var = ctk.StringVar(value="")
        self.desc_var = ctk.StringVar(value="")
        self.date_var = ctk.StringVar(value=date.today().isoformat())
        self.funding_source_var = ctk.StringVar(value="regular")
        self.currency_symbol = "₹"
        self.is_split_var = ctk.BooleanVar(value=False)
        self._split_rows = []

        # Set up traces for live updates
        self.type_var.trace_add("write", self._on_type_change)
        self.category_var.trace_add("write", self._on_input_change)
        self.amount_var.trace_add("write", self._on_input_change)

        # Row spacing helper
        row_idx = 0
        def next_row():
            nonlocal row_idx
            row_idx += 1
            return row_idx

        form_card.grid_columnconfigure(0, weight=0, minsize=140)
        form_card.grid_columnconfigure(1, weight=1)

        # 1. Type
        ctk.CTkLabel(form_card, text="Transaction Type", font=theme.FONT_BODY_BOLD).grid(
            row=row_idx, column=0, sticky="w", padx=20, pady=(20, 10)
        )
        self.type_menu = ctk.CTkOptionMenu(
            form_card, variable=self.type_var, values=["expense", "income"], width=200
        )
        self.type_menu.grid(row=row_idx, column=1, sticky="w", padx=20, pady=(20, 10))

        # 2. Category
        next_row()
        self.category_label = ctk.CTkLabel(form_card, text="Category", font=theme.FONT_BODY_BOLD)
        self.category_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=10)
        self.category_menu = ctk.CTkOptionMenu(
            form_card, variable=self.category_var, values=[], width=200
        )
        self.category_menu.grid(row=row_idx, column=1, sticky="w", padx=20, pady=10)

        # 3. Amount
        next_row()
        self.amount_lbl = ctk.CTkLabel(form_card, text="Amount (₹)", font=theme.FONT_BODY_BOLD)
        self.amount_lbl.grid(
            row=row_idx, column=0, sticky="w", padx=20, pady=10
        )

        self.amount_entry = ctk.CTkEntry(
            form_card, placeholder_text="0.00", textvariable=self.amount_var, width=200
        )
        self.amount_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=10)

        # 3b. Split across categories toggle
        next_row()
        self.split_cb = ctk.CTkCheckBox(
            form_card, text="✂️ Split across multiple categories",
            variable=self.is_split_var, command=self._toggle_split_mode
        )
        self.split_cb.grid(row=row_idx, column=1, sticky="w", padx=20, pady=(0, 6))

        next_row()
        self.split_frame = ctk.CTkFrame(form_card, fg_color="transparent")
        self.split_frame.grid(row=row_idx, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 10))
        self.split_frame.grid_remove()

        self.split_items_container = ctk.CTkFrame(self.split_frame, fg_color=("gray92", "gray16"), corner_radius=8)
        self.split_items_container.pack(fill="x", pady=(0, 6))

        split_btn_row = ctk.CTkFrame(self.split_frame, fg_color="transparent")
        split_btn_row.pack(fill="x", pady=(2, 4))
        ctk.CTkButton(
            split_btn_row, text="➕ Add Category Split", width=160, height=26,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_CARD_BORDER,
            text_color=("black", "white"), command=self._add_split_row
        ).pack(side="left")

        self.split_summary_label = ctk.CTkLabel(
            self.split_frame, text="", font=theme.FONT_SMALL, justify="left"
        )
        self.split_summary_label.pack(anchor="w", pady=(2, 4))

        # 4. Description
        next_row()
        ctk.CTkLabel(form_card, text="Description", font=theme.FONT_BODY_BOLD).grid(
            row=row_idx, column=0, sticky="w", padx=20, pady=10
        )
        self.desc_entry = ctk.CTkEntry(
            form_card, placeholder_text="e.g. Groceries", textvariable=self.desc_var, width=320
        )
        self.desc_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=10)

        # 5. Date
        next_row()
        ctk.CTkLabel(form_card, text="Date", font=theme.FONT_BODY_BOLD).grid(
            row=row_idx, column=0, sticky="w", padx=20, pady=10
        )
        self.date_entry = CalendarPicker(
            form_card, textvariable=self.date_var, entry_width=170
        )
        self.date_entry.grid(row=row_idx, column=1, sticky="w", padx=20, pady=10)

        # 6. Funding Source (only shown/relevant near limit)
        next_row()
        self.funding_label = ctk.CTkLabel(form_card, text="Funding Source", font=theme.FONT_BODY_BOLD)
        self.funding_label.grid(row=row_idx, column=0, sticky="w", padx=20, pady=(10, 20))
        self.funding_menu = ctk.CTkOptionMenu(
            form_card, variable=self.funding_source_var, values=["regular", "savings", "emergency_fund"], width=200
        )
        self.funding_menu.grid(row=row_idx, column=1, sticky="w", padx=20, pady=(10, 20))

        # Start with funding source grid hidden/collapsed
        self.funding_label.grid_remove()
        self.funding_menu.grid_remove()

        # --- Warning Text Line ---
        self.warning_label = ctk.CTkLabel(self.container, text="", font=theme.FONT_BODY_BOLD, text_color=theme.COLOR_WARNING)
        self.warning_label.pack(fill="x", pady=(5, 10))

        # --- Buttons & Status ---
        actions_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        actions_frame.pack(fill="x", pady=10)

        self.save_btn = ctk.CTkButton(
            actions_frame, 
            text="Save Transaction", 
            fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._save_transaction
        )
        self.save_btn.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            actions_frame, 
            text="Clear", 
            fg_color="transparent",
            border_color=theme.COLOR_MUTED,
            border_width=1,
            text_color=("black", "white"),
            command=self._clear_form
        )
        self.clear_btn.pack(side="left", padx=15)

        self._category_map = {}
        self._expense_category_names = []
        self._income_category_names = []

        self.status_label = ctk.CTkLabel(self.container, text="", font=theme.FONT_BODY)
        self.status_label.pack(anchor="w", pady=(10, 0))


    # ------------------------------------------------------------ Logic / Refreshes
    def refresh(self):
        """Reload categories from the database and split them by limits."""
        try:
            cats = categories_api.list_categories(self.db_path)
            self._category_map = {c["name"]: c["id"] for c in cats}
            
            from app.settings import get_setting
            currency = get_setting("currency_symbol", self.db_path) or "₹"
            self.currency_symbol = currency
            if self.is_split_var.get():
                self.amount_lbl.configure(text=f"Total Amount ({currency})")
            else:
                self.amount_lbl.configure(text=f"Amount ({currency})")

            # Split categories: expense (limits > 0) vs income (limits == 0)
            self._expense_category_names = [c["name"] for c in cats if c["soft_limit"] > 0 or c["hard_limit"] > 0]
            self._income_category_names = [c["name"] for c in cats if c["soft_limit"] == 0 and c["hard_limit"] == 0]

            # Update menus in existing split rows
            for r in self._split_rows:
                r["cat_menu"].configure(values=self._expense_category_names or ["General"])
            
            # Configure options based on currently selected transaction type
            t = self.type_var.get()
            if t == "income":
                opts = ["General Income"] + self._income_category_names
                self.category_menu.configure(values=opts)
                if not self.category_var.get() or (self.category_var.get() not in self._category_map and self.category_var.get() != "General Income"):
                    self.category_var.set("General Income")
            else:
                if self._expense_category_names:
                    self.category_menu.configure(values=self._expense_category_names)
                    if not self.category_var.get() or self.category_var.get() not in self._category_map:
                        self.category_var.set(self._expense_category_names[0])
                else:
                    self.category_menu.configure(values=["No categories created"])
                    self.category_var.set("No categories created")
        except Exception as e:
            self.status_label.configure(text=f"Failed to load categories: {e}", text_color=theme.COLOR_DANGER)

    def _toggle_split_mode(self):
        if self.is_split_var.get():
            self.category_label.grid_remove()
            self.category_menu.grid_remove()
            self.split_frame.grid()
            self.amount_lbl.configure(text=f"Total Amount ({self.currency_symbol})")
            self.banner_frame.pack_forget()
            self.warning_label.configure(text="")
            if not self._split_rows:
                c1 = self._expense_category_names[0] if self._expense_category_names else None
                c2 = self._expense_category_names[1] if len(self._expense_category_names) > 1 else c1
                self._add_split_row(default_cat=c1)
                self._add_split_row(default_cat=c2)
            self._update_split_summary()
        else:
            self.split_frame.grid_remove()
            self.category_label.grid()
            self.category_menu.grid()
            self.amount_lbl.configure(text=f"Amount ({self.currency_symbol})")
            self._on_input_change()

    def _add_split_row(self, default_cat=None, default_amt=""):
        row_frame = ctk.CTkFrame(self.split_items_container, fg_color="transparent")
        row_frame.pack(fill="x", padx=6, pady=3)

        c_val = default_cat or (self._expense_category_names[0] if self._expense_category_names else "")
        cat_var = ctk.StringVar(value=c_val)
        cat_menu = ctk.CTkOptionMenu(row_frame, variable=cat_var, values=self._expense_category_names or ["General"], width=140)
        cat_menu.pack(side="left", padx=(0, 6))

        amt_var = ctk.StringVar(value=str(default_amt))
        amt_var.trace_add("write", lambda *_: self._update_split_summary())
        amt_ent = ctk.CTkEntry(row_frame, textvariable=amt_var, placeholder_text="0.00", width=95)
        amt_ent.pack(side="left", padx=(0, 6))

        note_var = ctk.StringVar(value="")
        note_ent = ctk.CTkEntry(row_frame, textvariable=note_var, placeholder_text="Item / Sub-note", width=170)
        note_ent.pack(side="left", padx=(0, 6))

        remove_btn = ctk.CTkButton(
            row_frame, text="✕", width=28, height=28, fg_color=theme.COLOR_DANGER,
            hover_color="#922B21", command=lambda: self._remove_split_row(row_frame)
        )
        remove_btn.pack(side="left")

        row_data = {
            "frame": row_frame,
            "cat_var": cat_var,
            "amt_var": amt_var,
            "note_var": note_var,
            "cat_menu": cat_menu,
        }
        self._split_rows.append(row_data)
        self._update_split_summary()

    def _remove_split_row(self, row_frame):
        if len(self._split_rows) <= 2:
            return
        self._split_rows = [r for r in self._split_rows if r["frame"] != row_frame]
        row_frame.destroy()
        self._update_split_summary()

    def _update_split_summary(self):
        try:
            total = float(self.amount_var.get() or "0")
        except ValueError:
            total = 0.0

        allocated = 0.0
        for r in self._split_rows:
            try:
                v = float(r["amt_var"].get() or "0")
                if v > 0:
                    allocated += v
            except ValueError:
                pass

        diff = round(total - allocated, 2)
        if total <= 0:
            self.split_summary_label.configure(
                text="Enter a total amount above to allocate among categories.",
                text_color=theme.COLOR_MUTED
            )
        elif abs(diff) < 0.01:
            self.split_summary_label.configure(
                text=f"Total: ₹{total:,.2f}  |  Allocated: ₹{allocated:,.2f}  |  Balanced ✓",
                text_color=theme.COLOR_SUCCESS
            )
        elif diff > 0:
            self.split_summary_label.configure(
                text=f"Total: ₹{total:,.2f}  |  Allocated: ₹{allocated:,.2f}  |  ₹{diff:,.2f} Unallocated",
                text_color=theme.COLOR_WARNING
            )
        else:
            self.split_summary_label.configure(
                text=f"Total: ₹{total:,.2f}  |  Allocated: ₹{allocated:,.2f}  |  Over-allocated by ₹{abs(diff):,.2f} ✗",
                text_color=theme.COLOR_DANGER
            )

    def _on_type_change(self, *args):
        """Toggle category input states based on transaction type."""
        t = self.type_var.get()
        if t == "income":
            # Income cannot be split
            if self.is_split_var.get():
                self.is_split_var.set(False)
                self._toggle_split_mode()
            self.split_cb.grid_remove()

            # Let them select an income category or "General Income"
            self.category_label.grid(row=1, column=0, sticky="w", padx=20, pady=10)
            self.category_menu.grid(row=1, column=1, sticky="w", padx=20, pady=10)
            
            opts = ["General Income"] + self._income_category_names
            self.category_menu.configure(values=opts)
            self.category_var.set("General Income")
            
            # Incomes don't have warnings or special funding sources
            self.banner_frame.pack_forget()
            self.warning_label.configure(text="")
            self.funding_label.grid_remove()
            self.funding_menu.grid_remove()
        else:
            self.split_cb.grid()
            if self.is_split_var.get():
                self._toggle_split_mode()
            else:
                self.category_label.grid(row=1, column=0, sticky="w", padx=20, pady=10)
                self.category_menu.grid(row=1, column=1, sticky="w", padx=20, pady=10)
                
                self.category_menu.configure(values=self._expense_category_names)
                if self._expense_category_names:
                    self.category_var.set(self._expense_category_names[0])
                else:
                    self.category_var.set("No categories created")

                # Recheck live impact
                self._on_input_change()

    def _on_input_change(self, *args):
        """Live feedback logic: preview limit changes and show banners/funding selectors."""
        if self.is_split_var.get():
            self._update_split_summary()
            return

        if self.type_var.get() == "income":
            return

        cat_name = self.category_var.get()
        cat_id = self._category_map.get(cat_name)
        amount_str = self.amount_var.get().strip()

        # Reset states
        self.banner_frame.pack_forget()
        self.warning_label.configure(text="")
        self.funding_label.grid_remove()
        self.funding_menu.grid_remove()

        if not cat_id or not amount_str:
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                return
        except ValueError:
            # Not a valid float yet
            return

        try:
            preview = transactions_api.preview_transaction_impact(cat_id, amount, db_path=self.db_path)
            state = preview.get("state")
            message = preview.get("message", "")

            if state == "approaching_hard":
                self.warning_label.configure(text=message, text_color=theme.COLOR_WARNING)
                # Show funding source since warning is active
                self.funding_label.grid()
                self.funding_menu.grid()
            elif state == "at_hard":
                # Exactly at the limit — show as a warning, not an overflow
                self.warning_label.configure(text=message, text_color="#E8732C")
                self.funding_label.grid()
                self.funding_menu.grid()
            elif state == "over_hard":
                self.banner_label.configure(text=message)
                self.banner_frame.pack(fill="x", before=self.container.winfo_children()[1], pady=(10, 10))
                # Show funding source since overflow is active
                self.funding_label.grid()
                self.funding_menu.grid()
        except Exception:
            pass # Suppress db/logic errors during live typing

    def _save_transaction(self):
        self.status_label.configure(text="")
        t = self.type_var.get()
        amount_str = self.amount_var.get().strip()
        desc = self.desc_var.get().strip()
        date_str = self.date_var.get().strip()
        funding = self.funding_source_var.get()

        # Validations
        if not amount_str:
            self.status_label.configure(text="Error: Amount is required.", text_color=theme.COLOR_DANGER)
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.status_label.configure(text="Error: Amount must be greater than zero.", text_color=theme.COLOR_DANGER)
                return
        except ValueError:
            self.status_label.configure(text="Error: Amount must be a valid number.", text_color=theme.COLOR_DANGER)
            return

        if not date_str:
            self.status_label.configure(text="Error: Date is required.", text_color=theme.COLOR_DANGER)
            return
        
        # Simple date format validation
        try:
            date.fromisoformat(date_str)
        except ValueError:
            self.status_label.configure(text="Error: Date must be in YYYY-MM-DD format.", text_color=theme.COLOR_DANGER)
            return

        # Handle Split Mode
        if self.is_split_var.get():
            splits = []
            for r in self._split_rows:
                c_name = r["cat_var"].get()
                c_id = self._category_map.get(c_name)
                amt_txt = r["amt_var"].get().strip()
                if not c_id:
                    self.status_label.configure(text=f"Error: Category '{c_name}' is invalid.", text_color=theme.COLOR_DANGER)
                    return
                try:
                    s_amt = float(amt_txt)
                    if s_amt <= 0:
                        self.status_label.configure(text="Error: Split amounts must be greater than zero.", text_color=theme.COLOR_DANGER)
                        return
                except ValueError:
                    self.status_label.configure(text="Error: All split amounts must be valid numbers.", text_color=theme.COLOR_DANGER)
                    return
                splits.append({
                    "category_id": c_id,
                    "amount": s_amt,
                    "description": r["note_var"].get().strip()
                })

            if len(splits) < 2:
                self.status_label.configure(text="Error: Please add at least 2 split categories.", text_color=theme.COLOR_DANGER)
                return

            alloc_total = sum(s["amount"] for s in splits)
            if abs(alloc_total - amount) > 0.01:
                diff = round(amount - alloc_total, 2)
                self.status_label.configure(
                    text=f"Error: Splits total (₹{alloc_total:,.2f}) does not match Total Amount (₹{amount:,.2f}). Difference: ₹{diff:,.2f}",
                    text_color=theme.COLOR_DANGER
                )
                return

            try:
                txn_ids = transactions_api.add_split_transaction(
                    splits=splits,
                    total_amount=amount,
                    type=t,
                    txn_date=date_str,
                    description=desc,
                    funding_source=funding,
                    db_path=self.db_path
                )
                self.status_label.configure(
                    text=f"Split transaction ({len(txn_ids)} parts) saved successfully! ✅",
                    text_color=theme.COLOR_SUCCESS
                )
                self._clear_form(preserve_status=True)
                if self.on_change:
                    self.on_change()
            except Exception as e:
                self.status_label.configure(text=f"Failed to save split transaction: {e}", text_color=theme.COLOR_DANGER)
            return

        # Normal single transaction mode
        cat_id = None
        cat_name = self.category_var.get()
        if t == "expense":
            cat_id = self._category_map.get(cat_name)
            if not cat_id:
                self.status_label.configure(text="Error: Valid category is required for expenses.", text_color=theme.COLOR_DANGER)
                return
        else:
            if cat_name != "General Income":
                cat_id = self._category_map.get(cat_name)
            funding = "regular"  # Income doesn't have a funding source tag other than regular

        try:
            # Commit to Database
            transactions_api.add_transaction(
                amount=amount,
                type=t,
                category_id=cat_id,
                description=desc,
                txn_date=date_str,
                funding_source=funding,
                db_path=self.db_path
            )
            
            # Show Success & Reset
            self.status_label.configure(text="Transaction saved successfully! ✅", text_color=theme.COLOR_SUCCESS)
            self._clear_form(preserve_status=True)

            if self.on_change:
                self.on_change()
        except Exception as e:
            self.status_label.configure(text=f"Failed to save transaction: {e}", text_color=theme.COLOR_DANGER)

    def _clear_form(self, preserve_status=False):
        if not preserve_status:
            self.status_label.configure(text="")
            
        self.amount_var.set("")
        self.desc_var.set("")
        self.date_var.set(date.today().isoformat())
        self.funding_source_var.set("regular")

        if self.is_split_var.get():
            for r in self._split_rows:
                r["amt_var"].set("")
                r["note_var"].set("")
            self._update_split_summary()
        
        # Keep selected type and first category as is, but trigger updates
        t = self.type_var.get()
        if t == "income":
            self.category_var.set("General Income")
        elif self._expense_category_names:
            self.category_var.set(self._expense_category_names[0])
            
        self._on_input_change()

