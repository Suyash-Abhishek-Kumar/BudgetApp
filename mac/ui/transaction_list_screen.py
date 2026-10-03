"""
transaction_list_screen.py — spec Section 7.3.

Sortable/filterable table (category, date range, type, status), with
edit and delete. Uses ttk.Treeview for the table itself — CustomTkinter
has no native table widget — styled to match the dark theme.
"""

import calendar
from pathlib import Path
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from app import categories as categories_api
from app import transactions as transactions_api
from app import recurring as recurring_api
from ui import theme
from ui.calendar_picker import CalendarPicker


def _style_treeview():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Budget.Treeview",
        background="#2b2b2b", fieldbackground="#2b2b2b", foreground="white",
        rowheight=28, borderwidth=0, font=theme.FONT_BODY,
    )
    style.configure(
        "Budget.Treeview.Heading",
        background="#1a2530", foreground="white", font=theme.FONT_BODY, relief="flat",
    )
    style.map("Budget.Treeview", background=[("selected", "#2E86AB")])


class EditTransactionDialog(ctk.CTkToplevel):
    def __init__(self, master, txn_id: int, db_path, on_saved=None):
        super().__init__(master)
        self.txn_id = txn_id
        self.db_path = db_path
        self.on_saved = on_saved

        self.title("Edit Transaction")
        self.geometry("480x530")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._txn = transactions_api.get_transaction(txn_id, db_path=self.db_path)
        if not self._txn:
            self.destroy()
            return

        self._build()

    def _build(self):
        pad_x = 24
        ctk.CTkLabel(self, text="Edit Transaction", font=theme.FONT_TITLE).pack(anchor="w", padx=pad_x, pady=(20, 10))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=pad_x, pady=10)
        form.columnconfigure(1, weight=1)

        # 1. Type
        ctk.CTkLabel(form, text="Type:", font=theme.FONT_BODY_BOLD).grid(row=0, column=0, sticky="w", pady=8)
        self.type_var = ctk.StringVar(value=self._txn["type"])
        self.type_menu = ctk.CTkOptionMenu(form, variable=self.type_var, values=["expense", "income"], command=self._on_type_change)
        self.type_menu.grid(row=0, column=1, sticky="ew", pady=8)

        # 2. Amount
        ctk.CTkLabel(form, text="Amount:", font=theme.FONT_BODY_BOLD).grid(row=1, column=0, sticky="w", pady=8)
        self.amount_var = ctk.StringVar(value=f"{self._txn['amount']:.2f}")
        self.amount_entry = ctk.CTkEntry(form, textvariable=self.amount_var)
        self.amount_entry.grid(row=1, column=1, sticky="ew", pady=8)

        # 3. Category
        ctk.CTkLabel(form, text="Category:", font=theme.FONT_BODY_BOLD).grid(row=2, column=0, sticky="w", pady=8)
        cats = categories_api.list_categories(self.db_path)
        self._cat_name_to_id = {c["name"]: c["id"] for c in cats}
        cat_names = list(self._cat_name_to_id.keys())
        if self._txn["type"] == "income":
            cat_names = ["None (General Income)"] + cat_names

        current_cat_name = "None (General Income)"
        for name, cid in self._cat_name_to_id.items():
            if cid == self._txn["category_id"]:
                current_cat_name = name
                break

        self.cat_var = ctk.StringVar(value=current_cat_name)
        self.cat_menu = ctk.CTkOptionMenu(form, variable=self.cat_var, values=cat_names)
        self.cat_menu.grid(row=2, column=1, sticky="ew", pady=8)

        # 4. Date
        ctk.CTkLabel(form, text="Date:", font=theme.FONT_BODY_BOLD).grid(row=3, column=0, sticky="w", pady=8)
        self.date_var = ctk.StringVar(value=self._txn["date"])
        self.date_entry = CalendarPicker(form, textvariable=self.date_var, entry_width=180)
        self.date_entry.grid(row=3, column=1, sticky="ew", pady=8)

        # 5. Description
        ctk.CTkLabel(form, text="Description:", font=theme.FONT_BODY_BOLD).grid(row=4, column=0, sticky="w", pady=8)
        self.desc_var = ctk.StringVar(value=self._txn["description"] or "")
        self.desc_entry = ctk.CTkEntry(form, textvariable=self.desc_var)
        self.desc_entry.grid(row=4, column=1, sticky="ew", pady=8)

        # 6. Funding Source
        ctk.CTkLabel(form, text="Funding Source:", font=theme.FONT_BODY_BOLD).grid(row=5, column=0, sticky="w", pady=8)
        self.funding_var = ctk.StringVar(value=self._txn["funding_source"])
        self.funding_menu = ctk.CTkOptionMenu(form, variable=self.funding_var, values=["regular", "savings", "emergency_fund"])
        self.funding_menu.grid(row=5, column=1, sticky="ew", pady=8)
        if self._txn["type"] == "income":
            self.funding_menu.configure(state="disabled")

        # Error label
        self.error_label = ctk.CTkLabel(form, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.error_label.grid(row=6, column=0, columnspan=2, pady=5)

        # Button row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad_x, pady=(10, 20))
        ctk.CTkButton(btn_row, text="Cancel", fg_color="transparent", border_width=1,
                      border_color=theme.COLOR_CARD_BORDER, command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Save Changes", fg_color=theme.COLOR_PRIMARY,
                      hover_color=theme.COLOR_PRIMARY_HOVER, command=self._save).pack(side="right")

    def _on_type_change(self, val):
        cats = categories_api.list_categories(self.db_path)
        cat_names = [c["name"] for c in cats]
        if val == "income":
            cat_names = ["None (General Income)"] + cat_names
            self.cat_menu.configure(values=cat_names)
            if self.cat_var.get() not in cat_names:
                self.cat_var.set("None (General Income)")
            self.funding_menu.configure(state="disabled")
        else:
            self.cat_menu.configure(values=cat_names)
            if self.cat_var.get() == "None (General Income)" and cat_names:
                self.cat_var.set(cat_names[0])
            self.funding_menu.configure(state="normal")

    def _save(self):
        try:
            amt = float(self.amount_var.get().strip())
            if amt <= 0:
                self.error_label.configure(text="Amount must be positive.")
                return
        except ValueError:
            self.error_label.configure(text="Invalid amount entered.")
            return

        date_val = self.date_var.get().strip()
        try:
            date.fromisoformat(date_val)
        except ValueError:
            self.error_label.configure(text="Date must be YYYY-MM-DD.")
            return

        ttype = self.type_var.get()
        cat_choice = self.cat_var.get()
        cat_id = self._cat_name_to_id.get(cat_choice) if cat_choice != "None (General Income)" else None

        if ttype == "expense" and cat_id is None:
            self.error_label.configure(text="Expenses must have a category.")
            return

        funding = self.funding_var.get() if ttype == "expense" else "regular"
        desc = self.desc_var.get().strip()

        try:
            transactions_api.update_transaction(
                self.txn_id,
                amount=amt,
                type=ttype,
                category_id=cat_id,
                description=desc,
                txn_date=date_val,
                funding_source=funding,
                db_path=self.db_path
            )
            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.error_label.configure(text=f"Failed to update: {e}")


class CSVImportDialog(ctk.CTkToplevel):
    def __init__(self, master, file_path: str, db_path, on_imported=None):
        super().__init__(master)
        self.file_path = file_path
        self.db_path = db_path
        self.on_imported = on_imported

        self.title("Import Transactions from CSV")
        self.geometry("680x550")
        self.transient(master)
        self.grab_set()

        self.parsed_data = transactions_api.parse_csv_file(self.file_path, db_path=self.db_path)
        self._build()

    def _build(self):
        pad_x = 20
        ctk.CTkLabel(self, text="Import Transactions from CSV", font=theme.FONT_TITLE).pack(anchor="w", padx=pad_x, pady=(15, 6))

        info_frame = ctk.CTkFrame(self, fg_color=("gray95", "gray18"), corner_radius=8)
        info_frame.pack(fill="x", padx=pad_x, pady=(0, 10))

        valid = self.parsed_data.get("valid_rows", 0)
        total = self.parsed_data.get("total_rows", 0)
        err = self.parsed_data.get("error_count", 0)
        summary_txt = f"📄 File: {Path(self.file_path).name}  |  Parsed: {valid} valid rows"
        if err > 0:
            summary_txt += f" ({err} invalid/empty rows skipped)"
        ctk.CTkLabel(info_frame, text=summary_txt, font=theme.FONT_SMALL, text_color=theme.COLOR_PRIMARY).pack(anchor="w", padx=12, pady=8)

        mapping = self.parsed_data.get("mapping", {})
        amt_detected = mapping.get('amount') or mapping.get('debit') or 'None'
        map_txt = f"Detected Columns: Date → '{mapping.get('date', 'None')}' | Desc → '{mapping.get('description', 'None')}' | Amount → '{amt_detected}'"
        ctk.CTkLabel(self, text=map_txt, font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED).pack(anchor="w", padx=pad_x, pady=(0, 6))

        ctk.CTkLabel(self, text="Preview (First Rows):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 4))
        preview_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray17"), corner_radius=8)
        preview_frame.pack(fill="both", expand=True, padx=pad_x, pady=(0, 10))

        cols = ("date", "type", "amount", "category", "description")
        tree = ttk.Treeview(preview_frame, columns=cols, show="headings", style="Budget.Treeview", height=6)
        tree.heading("date", text="Date")
        tree.heading("type", text="Type")
        tree.heading("amount", text="Amount")
        tree.heading("category", text="Category")
        tree.heading("description", text="Description")
        tree.column("date", width=85)
        tree.column("type", width=70)
        tree.column("amount", width=80)
        tree.column("category", width=110)
        tree.column("description", width=250)
        tree.pack(fill="both", expand=True, padx=2, pady=2)

        cats = {c["id"]: c["name"] for c in categories_api.list_categories(self.db_path)}
        rows = self.parsed_data.get("rows", [])
        for r in rows[:8]:
            c_name = cats.get(r.get("category_id"), "General")
            tree.insert("", "end", values=(
                r["date"], r["type"], f"{r['amount']:.2f}", c_name, r["description"][:35]
            ))

        act_row = ctk.CTkFrame(self, fg_color="transparent")
        act_row.pack(fill="x", padx=pad_x, pady=(6, 15))

        ctk.CTkButton(
            act_row, text="Cancel", fg_color="transparent", border_width=1,
            border_color=theme.COLOR_CARD_BORDER, command=self.destroy
        ).pack(side="right", padx=(8, 0))

        btn_text = f"📥 Confirm Import ({len(rows)} Transactions)"
        ctk.CTkButton(
            act_row, text=btn_text, fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER, command=self._confirm_import
        ).pack(side="right")

    def _confirm_import(self):
        rows = self.parsed_data.get("rows", [])
        if not rows:
            self.destroy()
            return
        imported_count = transactions_api.import_transactions_from_rows(rows, db_path=self.db_path)
        messagebox.showinfo("Import Successful", f"Successfully imported {imported_count} transaction(s)!")
        self.destroy()
        if self.on_imported:
            self.on_imported()


class TransactionListScreen(ctk.CTkFrame):
    COLUMNS = ("date", "category", "description", "amount", "funding_source", "status")
    HEADINGS = {
        "date": "Date", "category": "Category", "description": "Description",
        "amount": "Amount", "funding_source": "Funding", "status": "Status",
    }

    def __init__(self, master, db_path, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.db_path = db_path
        self.on_change = on_change
        self._sort_col = "date"
        self._sort_desc = True
        self._category_map = {}
        self._id_by_row = {}
        self.is_privacy_mode = False
        _style_treeview()
        self._build()
        self.refresh()

    def set_privacy_mode(self, enabled: bool):
        self.is_privacy_mode = enabled
        self.refresh()

    # ---------------------------------------------------------------- UI
    def _build(self):
        ctk.CTkLabel(self, text="Transactions", font=theme.FONT_TITLE).pack(
            anchor="w", padx=24, pady=(20, 10)
        )

        # --- filter bar (2 clean rows) ---
        filters = ctk.CTkFrame(self, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER, border_width=1, corner_radius=10)
        filters.pack(fill="x", padx=24, pady=(0, 10))

        # Row 1: Search, Period, Custom Date Range, Clear Filters
        row1 = ctk.CTkFrame(filters, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 6))

        self.search_var = ctk.StringVar(value="")
        self.search_var.trace_add("write", lambda *_: self.refresh())
        self.search_entry = ctk.CTkEntry(
            row1,
            textvariable=self.search_var,
            placeholder_text="🔍 Search description, note, amount...",
            width=270
        )
        self.search_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row1, text="Period:").pack(side="left", padx=(0, 6))
        self.period_var = ctk.StringVar(value="All Time")
        self.period_menu = ctk.CTkOptionMenu(
            row1,
            variable=self.period_var,
            values=["All Time", "This Month", "Last Month", "Last 30 Days", "Custom Range"],
            command=self._on_period_change,
            width=130
        )
        self.period_menu.pack(side="left", padx=(0, 12))

        self.date_range_frame = ctk.CTkFrame(row1, fg_color="transparent")
        self.start_date_var = ctk.StringVar(value="")
        self.end_date_var = ctk.StringVar(value="")
        ctk.CTkLabel(self.date_range_frame, text="From:").pack(side="left", padx=(0, 4))
        self.start_date_entry = CalendarPicker(self.date_range_frame, textvariable=self.start_date_var, entry_width=90)
        self.start_date_entry.pack(side="left", padx=(0, 6))
        self.start_date_var.trace_add("write", lambda *_: self.refresh())

        ctk.CTkLabel(self.date_range_frame, text="To:").pack(side="left", padx=(0, 4))
        self.end_date_entry = CalendarPicker(self.date_range_frame, textvariable=self.end_date_var, entry_width=90)
        self.end_date_entry.pack(side="left", padx=(0, 6))
        self.end_date_var.trace_add("write", lambda *_: self.refresh())

        ctk.CTkButton(
            row1, text="Clear Filters", width=95, fg_color="transparent", border_width=1,
            border_color=theme.COLOR_CARD_BORDER, command=self._clear_filters
        ).pack(side="right")

        # Row 2: Category, Type, Status
        row2 = ctk.CTkFrame(filters, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(0, 10))

        self.category_filter = ctk.StringVar(value="All")
        self.type_filter = ctk.StringVar(value="All")
        self.status_filter = ctk.StringVar(value="All")

        ctk.CTkLabel(row2, text="Category:").pack(side="left", padx=(0, 6))
        self.category_menu = ctk.CTkOptionMenu(
            row2, variable=self.category_filter, values=["All"], command=lambda _v: self.refresh(),
            width=140,
        )
        self.category_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="Type:").pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(
            row2, variable=self.type_filter, values=["All", "expense", "income"],
            command=lambda _v: self.refresh(), width=110,
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(row2, text="Status:").pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(
            row2, variable=self.status_filter, values=["All", "confirmed", "pending_approval"],
            command=lambda _v: self.refresh(), width=140,
        ).pack(side="left", padx=(0, 16))

        ctk.CTkButton(row2, text="Refresh", width=90, command=self.refresh).pack(side="left")

        # --- table ---
        table_frame = ctk.CTkFrame(self, fg_color=("gray90", "gray17"), corner_radius=12)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 10))

        self.tree = ttk.Treeview(
            table_frame, columns=self.COLUMNS, show="headings", style="Budget.Treeview", selectmode="browse"
        )
        col_widths = {
            "date": 95, "category": 110, "description": 190,
            "amount": 80, "funding_source": 90, "status": 90,
        }
        for col in self.COLUMNS:
            self.tree.heading(col, text=self.HEADINGS[col], command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=col_widths[col], anchor="w", stretch=False)
        self.tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda _e: self._edit_selected())

        # --- action row ---
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 20))
        ctk.CTkButton(actions, text="✏️ Edit Selected", fg_color=theme.COLOR_PRIMARY,
                      hover_color=theme.COLOR_PRIMARY_HOVER, width=125, command=self._edit_selected).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="✅ Approve", fg_color="#10B981",
                      hover_color="#059669", width=105, command=self._approve_selected).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Delete Selected", fg_color=theme.COLOR_DANGER,
                      hover_color="#922B21", width=120, command=self._delete_selected).pack(side="left")
        self.status_label = ctk.CTkLabel(actions, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED)
        self.status_label.pack(side="left", padx=12)

        ctk.CTkButton(actions, text="⬆️ Import CSV", width=115, fg_color="#10B981", hover_color="#059669",
                      command=self._import_csv).pack(side="right", padx=(8, 0))
        ctk.CTkButton(actions, text="⬇️ Export CSV", width=115, fg_color="transparent", border_width=1,
                      border_color=theme.COLOR_CARD_BORDER, command=self._export_csv).pack(side="right")

    # ------------------------------------------------------------ helpers
    def _on_period_change(self, choice):
        if choice == "Custom Range":
            self.date_range_frame.pack(side="left", padx=(0, 12))
        else:
            self.date_range_frame.pack_forget()
        self.refresh()

    def _clear_filters(self):
        self.search_var.set("")
        self.period_var.set("All Time")
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.category_filter.set("All")
        self.type_filter.set("All")
        self.status_filter.set("All")
        self.date_range_frame.pack_forget()
        self.refresh()

    def _sort_by(self, col):
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = False
        self.refresh()

    def refresh(self):
        try:
            recurring_api.process_due_recurring_transactions(db_path=self.db_path)
        except Exception:
            pass

        cats = categories_api.list_categories(self.db_path)
        self._category_map = {c["name"]: c["id"] for c in cats}
        self.category_menu.configure(values=["All"] + list(self._category_map.keys()))

        period = self.period_var.get()
        today = date.today()
        start_date, end_date = None, None
        if period == "This Month":
            start_date = f"{today.year:04d}-{today.month:02d}-01"
            days_in_m = calendar.monthrange(today.year, today.month)[1]
            end_date = f"{today.year:04d}-{today.month:02d}-{days_in_m:02d}"
        elif period == "Last Month":
            lm = today.month - 1
            ly = today.year
            if lm == 0:
                lm = 12
                ly -= 1
            days_in_lm = calendar.monthrange(ly, lm)[1]
            start_date = f"{ly:04d}-{lm:02d}-01"
            end_date = f"{ly:04d}-{lm:02d}-{days_in_lm:02d}"
        elif period == "Last 30 Days":
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()
        elif period == "Custom Range":
            start_date = self.start_date_var.get().strip() or None
            end_date = self.end_date_var.get().strip() or None

        kwargs = {}
        if self.category_filter.get() != "All":
            kwargs["category_id"] = self._category_map.get(self.category_filter.get())
        if self.type_filter.get() != "All":
            kwargs["txn_type"] = self.type_filter.get()
        if self.status_filter.get() != "All":
            kwargs["status"] = self.status_filter.get()
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        search = self.search_var.get().strip()
        if search:
            kwargs["search_query"] = search

        rows = transactions_api.list_transactions(db_path=self.db_path, **kwargs)

        cat_name_by_id = {c["id"]: c["name"] for c in cats}
        for r in rows:
            if r["category_id"] is not None:
                r["_category_name"] = cat_name_by_id.get(r["category_id"], "—")
            else:
                r["_category_name"] = "General Income" if r["type"] == "income" else "—"


        reverse = self._sort_desc
        sort_key = "_category_name" if self._sort_col == "category" else self._sort_col
        rows.sort(key=lambda r: (r[sort_key] is None, r[sort_key]), reverse=reverse)

        self.tree.delete(*self.tree.get_children())
        self._id_by_row.clear()
        for r in rows:
            if self.is_privacy_mode:
                amount_display = "••••••"
            else:
                amount_display = f"{'+' if r['type'] == 'income' else '-'}{r['amount']:.2f}"
            row_id = self.tree.insert("", "end", values=(
                r["date"], r["_category_name"], r["description"] or "",
                amount_display, r["funding_source"], r["status"],
            ))
            self._id_by_row[row_id] = r["id"]

        self.status_label.configure(text=f"{len(rows)} transaction(s)")
        pending_count = len([r for r in rows if r.get("status") == "pending_approval"])
        if pending_count > 0:
            self.status_label.configure(
                text=f"{len(rows)} txn(s) • ⚠️ {pending_count} pending approval",
                text_color="#E67E22"
            )
        else:
            self.status_label.configure(
                text=f"{len(rows)} transaction(s)",
                text_color=theme.COLOR_MUTED
            )

    def _approve_selected(self):
        selection = self.tree.selection()
        if not selection:
            self.status_label.configure(text="Select a pending row first.", text_color=theme.COLOR_DANGER)
            return
        txn_id = self._id_by_row.get(selection[0])
        if txn_id is not None:
            txn = transactions_api.get_transaction(txn_id, db_path=self.db_path)
            if txn and txn.get("status") == "pending_approval":
                transactions_api.approve_transaction(txn_id, db_path=self.db_path)
                self.refresh()
                self.status_label.configure(text="Transaction approved & confirmed!", text_color=theme.COLOR_SUCCESS)
                if self.on_change:
                    self.on_change()
            else:
                self.status_label.configure(text="Selected transaction is already confirmed.", text_color=theme.COLOR_MUTED)

    def _delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            self.status_label.configure(text="Select a row first.", text_color=theme.COLOR_DANGER)
            return
        txn_id = self._id_by_row.get(selection[0])
        if txn_id is not None:
            transactions_api.delete_transaction(txn_id, db_path=self.db_path)
            self.refresh()
            self.status_label.configure(text="Deleted.", text_color=theme.COLOR_MUTED)
            if self.on_change:
                self.on_change()

    def _edit_selected(self):
        selection = self.tree.selection()
        if not selection:
            self.status_label.configure(text="Select a transaction to edit.", text_color=theme.COLOR_DANGER)
            return
        txn_id = self._id_by_row.get(selection[0])
        if txn_id is not None:
            EditTransactionDialog(
                self.winfo_toplevel(),
                txn_id=txn_id,
                db_path=self.db_path,
                on_saved=self._on_transaction_edited
            )

    def _on_transaction_edited(self):
        self.refresh()
        self.status_label.configure(text="Transaction updated.", text_color=theme.COLOR_SUCCESS)
        if self.on_change:
            self.on_change()

    def _export_csv(self):
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Export Transactions to CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            initialfile=f"budget_transactions_{date.today().isoformat()}.csv"
        )
        if not file_path:
            return

        period = self.period_var.get()
        today = date.today()
        start_date, end_date = None, None
        if period == "This Month":
            start_date = f"{today.year:04d}-{today.month:02d}-01"
            days_in_m = calendar.monthrange(today.year, today.month)[1]
            end_date = f"{today.year:04d}-{today.month:02d}-{days_in_m:02d}"
        elif period == "Last Month":
            lm = today.month - 1
            ly = today.year
            if lm == 0:
                lm = 12
                ly -= 1
            days_in_m = calendar.monthrange(ly, lm)[1]
            start_date = f"{ly:04d}-{lm:02d}-01"
            end_date = f"{ly:04d}-{lm:02d}-{days_in_m:02d}"
        elif period == "Last 30 Days":
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()
        elif period == "Custom Range":
            sd = self.start_date_var.get().strip()
            ed = self.end_date_var.get().strip()
            if sd:
                start_date = sd
            if ed:
                end_date = ed

        cat_val = self.category_filter.get()
        cat_id = self._category_map.get(cat_val) if cat_val != "All" else None
        t_val = self.type_filter.get().lower()
        t = t_val if t_val in ("expense", "income") else None
        s_val = self.status_filter.get()
        s = s_val if s_val in ("confirmed", "pending_approval") else None
        q = self.search_var.get().strip() or None

        count = transactions_api.export_transactions_csv(
            file_path,
            db_path=self.db_path,
            start_date=start_date,
            end_date=end_date,
            category_id=cat_id,
            txn_type=t,
            status=s,
            search_query=q
        )
        self.status_label.configure(text=f"Exported {count} row(s) to CSV.", text_color=theme.COLOR_SUCCESS)
        messagebox.showinfo("Export Successful", f"Successfully exported {count} transaction(s) to:\n{file_path}")

    def _import_csv(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Select CSV File to Import",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return
        CSVImportDialog(
            self.winfo_toplevel(),
            file_path=file_path,
            db_path=self.db_path,
            on_imported=self._on_import_done
        )

    def _on_import_done(self):
        self.refresh()
        self.status_label.configure(text="Transactions imported successfully.", text_color=theme.COLOR_SUCCESS)
        if self.on_change:
            self.on_change()

