"""
transaction_list_screen.py — spec Section 7.3.

Sortable/filterable table (category, date range, type, status), with
edit and delete. Uses ttk.Treeview for the table itself — CustomTkinter
has no native table widget — styled to match the dark theme.
"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from app import categories as categories_api
from app import transactions as transactions_api
from ui import theme


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
        _style_treeview()
        self._build()
        self.refresh()

    # ---------------------------------------------------------------- UI
    def _build(self):
        ctk.CTkLabel(self, text="Transactions", font=theme.FONT_TITLE).pack(
            anchor="w", padx=24, pady=(20, 10)
        )

        # --- filter bar ---
        filters = ctk.CTkFrame(self, fg_color="transparent")
        filters.pack(fill="x", padx=24, pady=(0, 10))

        self.category_filter = ctk.StringVar(value="All")
        self.type_filter = ctk.StringVar(value="All")
        self.status_filter = ctk.StringVar(value="All")

        ctk.CTkLabel(filters, text="Category").pack(side="left", padx=(0, 6))
        self.category_menu = ctk.CTkOptionMenu(
            filters, variable=self.category_filter, values=["All"], command=lambda _v: self.refresh(),
            width=140,
        )
        self.category_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(filters, text="Type").pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(
            filters, variable=self.type_filter, values=["All", "expense", "income"],
            command=lambda _v: self.refresh(), width=110,
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(filters, text="Status").pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(
            filters, variable=self.status_filter, values=["All", "confirmed", "pending_approval"],
            command=lambda _v: self.refresh(), width=140,
        ).pack(side="left", padx=(0, 16))

        ctk.CTkButton(filters, text="Refresh", width=90, command=self.refresh).pack(side="left")

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

        # --- action row ---
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 20))
        ctk.CTkButton(actions, text="Delete Selected", fg_color=theme.COLOR_DANGER,
                      hover_color="#922B21", command=self._delete_selected).pack(side="left")
        self.status_label = ctk.CTkLabel(actions, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED)
        self.status_label.pack(side="left", padx=12)

    # ------------------------------------------------------------ helpers
    def _sort_by(self, col):
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = False
        self.refresh()

    def refresh(self):
        cats = categories_api.list_categories(self.db_path)
        self._category_map = {c["name"]: c["id"] for c in cats}
        self.category_menu.configure(values=["All"] + list(self._category_map.keys()))

        kwargs = {}
        if self.category_filter.get() != "All":
            kwargs["category_id"] = self._category_map.get(self.category_filter.get())
        if self.type_filter.get() != "All":
            kwargs["txn_type"] = self.type_filter.get()
        if self.status_filter.get() != "All":
            kwargs["status"] = self.status_filter.get()

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
            amount_display = f"{'+' if r['type'] == 'income' else '-'}{r['amount']:.2f}"
            row_id = self.tree.insert("", "end", values=(
                r["date"], r["_category_name"], r["description"] or "",
                amount_display, r["funding_source"], r["status"],
            ))
            self._id_by_row[row_id] = r["id"]

        self.status_label.configure(text=f"{len(rows)} transaction(s)")

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
