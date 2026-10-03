"""
dashboard_screen.py — spec Section 7.1.

Implements the Dashboard home screen of the application containing overview stats cards,
a category progress list with custom canvas limit tick bars, and three interactive
embedded Matplotlib charts:
- Category spending pie chart (click category slice to filter trend).
- Historical trend line chart (6-month history of spent vs. savings rollover).
- Cumulative pace chart (actual spending vs. dashed projected spending), with a
  hover tooltip showing the actual/projected values at the cursor's day.
"""

from datetime import date
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import matplotlib
import numpy as np
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from app import budget_logic, categories as categories_api
from ui import theme


class LimitBar(tk.Canvas):
    """
    Custom canvas widget that draws a horizontal scale representing spending progress
    against a category budget. Displays soft and hard limits as precise vertical ticks
    retaining full visibility even when spending overflows the limit.
    """
    def __init__(self, master, spent, soft_limit, hard_limit, state, **kwargs):
        kwargs.setdefault("height", 45)
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        self.spent = spent
        self.soft_limit = soft_limit
        self.hard_limit = hard_limit
        self.state = state
        self.bind("<Configure>", self.draw)

    def draw(self, event=None):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1:
            return

        # Fetch current UI theme-matching colors
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#252525" if is_dark else "#F8F9FA"
        self.configure(bg=bg_color)

        # Scale limits to fit in canvas boundaries
        scale_max = max(self.hard_limit * 1.25, self.spent * 1.1, 10.0)
        pad_x = 15
        bar_y = height // 2 - 4
        bar_h = 8
        usable_w = width - (pad_x * 2)

        def to_x(val):
            return pad_x + (val / scale_max) * usable_w

        # Draw background scale axis line
        self.create_line(pad_x, bar_y + bar_h//2, width - pad_x, bar_y + bar_h//2, fill="#555555" if is_dark else "#CCCCCC", width=2)

        # Fill spent progress rectangle
        spent_x = to_x(self.spent)
        if self.state == "under_soft":
            bar_color = "#5CB85C"  # Success Green
        elif self.state == "approaching_hard" or self.state == "between_soft_hard":
            bar_color = "#F0AD4E"  # Warning Orange
        elif self.state == "at_hard":
            bar_color = "#E8732C"  # Deep orange — exactly at limit
        else:  # over_hard
            bar_color = "#D9534F"  # Danger Red
        self.create_rectangle(pad_x, bar_y, spent_x, bar_y + bar_h, fill=bar_color, outline="")

        # Draw soft limit tick and text
        soft_x = to_x(self.soft_limit)
        self.create_line(soft_x, bar_y - 4, soft_x, bar_y + bar_h + 4, fill="#AAAAAA" if is_dark else "#666666", width=2)
        self.create_text(soft_x, bar_y - 10, text=f"Soft: {self.soft_limit:.0f}", fill="#AAAAAA" if is_dark else "#666666", font=("Helvetica", 9))

        # Draw hard limit tick and text
        hard_x = to_x(self.hard_limit)
        hard_color = "#EED382" if is_dark else "#856404"
        self.create_line(hard_x, bar_y - 6, hard_x, bar_y + bar_h + 6, fill=hard_color, width=2)
        self.create_text(hard_x, bar_y + bar_h + 10, text=f"Hard: {self.hard_limit:.0f}", fill="#AAAAAA" if is_dark else "#666666", font=("Helvetica", 9))


class BudgetTransferDialog(ctk.CTkToplevel):
    """
    Modal dialog for transferring envelope budget between categories.
    Allows user to select source category, destination category, and amount,
    showing live preview of new limits before committing.
    """
    def __init__(self, master, db_path, month=None, on_transferred=None):
        super().__init__(master)
        self.db_path = db_path
        self.month = month
        self.on_transferred = on_transferred

        self.title("🔄 Envelope Budget Transfer")
        self.geometry("490x530")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Load categories and current month summary for spending info
        summary = budget_logic.dashboard_summary(month=self.month, db_path=self.db_path)
        cat_stats = {c["category_id"]: c for c in summary.get("categories", [])}

        all_cats = categories_api.list_categories(self.db_path)
        self.categories = []
        for cat in all_cats:
            cid = cat["id"]
            stat = cat_stats.get(cid, {})
            spent = stat.get("spent", 0.0)
            remaining = max(0.0, cat["hard_limit"] - spent)
            self.categories.append({
                "id": cid,
                "name": cat["name"],
                "hard_limit": float(cat["hard_limit"]),
                "soft_limit": float(cat["soft_limit"]),
                "spent": spent,
                "remaining": remaining,
            })

        self.cat_by_label = {}
        for c in self.categories:
            label = f"{c['name']} (Limit: ₹{c['hard_limit']:,.0f} | Rem: ₹{c['remaining']:,.0f})"
            self.cat_by_label[label] = c

        self._build_ui()

    def _build_ui(self):
        labels = list(self.cat_by_label.keys())
        pad_x = 24

        ctk.CTkLabel(self, text="🔄 Envelope Budget Transfer", font=theme.FONT_TITLE).pack(anchor="w", padx=pad_x, pady=(18, 4))
        ctk.CTkLabel(self, text="Move budget limit between categories in real-time.", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED).pack(anchor="w", padx=pad_x, pady=(0, 16))

        if len(self.categories) < 2:
            ctk.CTkLabel(self, text="You need at least two categories to transfer budget.", text_color=theme.COLOR_WARNING).pack(pady=40)
            ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=10)
            return

        # Source Category
        ctk.CTkLabel(self, text="Transfer From (Source):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        self.from_var = ctk.StringVar(value=labels[0])
        self.from_menu = ctk.CTkOptionMenu(
            self, variable=self.from_var, values=labels,
            command=self._on_selection_change, width=440,
            fg_color=theme.COLOR_CARD_BG, button_color=theme.COLOR_CARD_BORDER
        )
        self.from_menu.pack(padx=pad_x, pady=(0, 12))

        # Destination Category
        ctk.CTkLabel(self, text="Transfer To (Destination):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        dest_default = labels[1] if len(labels) > 1 else labels[0]
        self.to_var = ctk.StringVar(value=dest_default)
        self.to_menu = ctk.CTkOptionMenu(
            self, variable=self.to_var, values=labels,
            command=self._on_selection_change, width=440,
            fg_color=theme.COLOR_CARD_BG, button_color=theme.COLOR_CARD_BORDER
        )
        self.to_menu.pack(padx=pad_x, pady=(0, 12))

        # Transfer Amount
        ctk.CTkLabel(self, text="Transfer Amount (₹):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        amt_frame = ctk.CTkFrame(self, fg_color="transparent")
        amt_frame.pack(fill="x", padx=pad_x, pady=(0, 6))

        self.amount_var = ctk.StringVar(value="")
        self.amount_var.trace_add("write", lambda *_: self._update_preview())
        self.amount_entry = ctk.CTkEntry(amt_frame, textvariable=self.amount_var, placeholder_text="e.g. 500", width=170)
        self.amount_entry.pack(side="left", padx=(0, 10))

        # Quick preset buttons
        for val in [200, 500, 1000]:
            ctk.CTkButton(
                amt_frame, text=f"+₹{val}", width=60, height=28,
                fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_CARD_BORDER,
                command=lambda v=val: self._add_quick_amount(v)
            ).pack(side="left", padx=3)

        ctk.CTkButton(
            amt_frame, text="Max Rem", width=75, height=28,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_CARD_BORDER,
            command=self._set_max_remaining
        ).pack(side="left", padx=3)

        # Preview card
        self.preview_card = ctk.CTkFrame(self, fg_color=("gray95", "gray18"), corner_radius=8)
        self.preview_card.pack(fill="x", padx=pad_x, pady=(10, 12))
        self.preview_lbl = ctk.CTkLabel(
            self.preview_card, text="", justify="left", font=theme.FONT_SMALL,
            text_color=theme.COLOR_MUTED
        )
        self.preview_lbl.pack(anchor="w", padx=12, pady=10)

        self.error_lbl = ctk.CTkLabel(self, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.error_lbl.pack(padx=pad_x, pady=(0, 6))

        # Action Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad_x, pady=(4, 15))

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1,
            border_color=theme.COLOR_CARD_BORDER, command=self.destroy, width=100
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="Confirm Transfer", fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER, command=self._do_transfer, width=150
        ).pack(side="right")

        self._update_preview()

    def _add_quick_amount(self, delta):
        try:
            cur = float(self.amount_var.get() or "0")
        except ValueError:
            cur = 0.0
        self.amount_var.set(str(int(cur + delta)))

    def _set_max_remaining(self):
        from_cat = self.cat_by_label.get(self.from_var.get())
        if from_cat:
            self.amount_var.set(str(int(from_cat["remaining"])))

    def _on_selection_change(self, _=None):
        self._update_preview()

    def _update_preview(self):
        self.error_lbl.configure(text="")
        from_cat = self.cat_by_label.get(self.from_var.get())
        to_cat = self.cat_by_label.get(self.to_var.get())
        if not from_cat or not to_cat:
            return

        if from_cat["id"] == to_cat["id"]:
            self.preview_lbl.configure(text="⚠️ Source and destination categories must be different.")
            return

        amt_str = self.amount_var.get().strip()
        if not amt_str:
            self.preview_lbl.configure(
                text=f"• From: {from_cat['name']} (Current Limit: ₹{from_cat['hard_limit']:,.2f})\n"
                     f"• To:   {to_cat['name']} (Current Limit: ₹{to_cat['hard_limit']:,.2f})\n"
                     f"Enter an amount to see projected limits."
            )
            return

        try:
            amt = float(amt_str)
            if amt <= 0:
                self.preview_lbl.configure(text="⚠️ Amount must be greater than zero.")
                return
            if amt > from_cat["hard_limit"]:
                self.preview_lbl.configure(
                    text=f"⚠️ Amount (₹{amt:,.2f}) exceeds {from_cat['name']}'s total limit (₹{from_cat['hard_limit']:,.2f})."
                )
                return

            new_from = from_cat["hard_limit"] - amt
            new_to = to_cat["hard_limit"] + amt
            self.preview_lbl.configure(
                text=f"• {from_cat['name']}: ₹{from_cat['hard_limit']:,.2f}  ➔  ₹{new_from:,.2f} (-₹{amt:,.2f})\n"
                     f"• {to_cat['name']}: ₹{to_cat['hard_limit']:,.2f}  ➔  ₹{new_to:,.2f} (+₹{amt:,.2f})"
            )
        except ValueError:
            self.preview_lbl.configure(text="⚠️ Please enter a valid number.")

    def _do_transfer(self):
        from_cat = self.cat_by_label.get(self.from_var.get())
        to_cat = self.cat_by_label.get(self.to_var.get())
        if not from_cat or not to_cat:
            self.error_lbl.configure(text="Please select valid categories.")
            return
        if from_cat["id"] == to_cat["id"]:
            self.error_lbl.configure(text="Source and destination cannot be identical.")
            return

        try:
            amt = float(self.amount_var.get().strip())
            if amt <= 0:
                self.error_lbl.configure(text="Amount must be greater than zero.")
                return
        except ValueError:
            self.error_lbl.configure(text="Please enter a valid amount.")
            return

        try:
            categories_api.transfer_category_budget(
                from_cat["id"],
                to_cat["id"],
                amt,
                adjust_soft=True,
                db_path=self.db_path
            )
            messagebox.showinfo(
                "Transfer Successful",
                f"Transferred ₹{amt:,.2f} from '{from_cat['name']}' to '{to_cat['name']}'."
            )
            self.destroy()
            if self.on_transferred:
                self.on_transferred()
        except Exception as e:
            self.error_lbl.configure(text=str(e))


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master, db_path):
        super().__init__(master, fg_color="transparent")
        self.db_path = db_path
        self.selected_category_id = None
        self.selected_category_name = None
        self.currency = "₹"
        self.selected_month = date.today().isoformat()[:7]
        self._month_map = {}
        self.is_privacy_mode = False

        self._build()
        self.refresh()

    def set_privacy_mode(self, enabled: bool):
        self.is_privacy_mode = enabled
        self.refresh()

    def _build(self):
        # Configure layout: left side has stats and list, right side has charts
        self.grid_columnconfigure(0, weight=1, minsize=400)
        self.grid_columnconfigure(1, weight=1, minsize=550)
        self.grid_rowconfigure(0, weight=1)

        # Left Column (Stats & Progress List)
        self.left_column = ctk.CTkFrame(self, fg_color="transparent")
        self.left_column.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=10)
        self.left_column.grid_columnconfigure(0, weight=1)

        # Header Row (Title + Month Selector)
        header_row = ctk.CTkFrame(self.left_column, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(10, 8))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header_row, text="Dashboard", font=theme.FONT_TITLE).grid(row=0, column=0, sticky="w")

        self.month_var = ctk.StringVar(value="")
        self.month_menu = ctk.CTkOptionMenu(
            header_row,
            variable=self.month_var,
            values=[],
            command=self._on_month_change,
            width=180,
            font=theme.FONT_SMALL,
        )
        self.month_menu.grid(row=0, column=1, sticky="e")

        # Archive Mode Banner
        self.archive_banner = ctk.CTkFrame(self.left_column, fg_color="#2D2415", border_color="#D97706", border_width=1, corner_radius=8)
        self.archive_banner_label = ctk.CTkLabel(
            self.archive_banner,
            text="📁 Archive View: (Closed) — Read-Only Mode",
            font=theme.FONT_SMALL,
            text_color="#FCD34D"
        )
        self.archive_banner_label.pack(side="left", padx=10, pady=6)
        self.reset_month_btn = ctk.CTkButton(
            self.archive_banner,
            text="Back to Current",
            font=theme.FONT_SMALL,
            width=105,
            height=24,
            fg_color="#D97706",
            hover_color="#B45309",
            command=self.reset_to_current_month
        )
        self.reset_month_btn.pack(side="right", padx=10, pady=6)

        # Overview Stats Cards — Row 1: Available, Income, Spent
        self.stats_frame = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.stats_frame.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        self.available_card = self._create_card(self.stats_frame, "Available to Spend", "₹0.00", "#27AE60")
        self.available_card.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.income_card = self._create_card(self.stats_frame, "Total Income", "₹0.00", theme.COLOR_PRIMARY)
        self.income_card.grid(row=0, column=1, padx=6, sticky="ew")

        self.spent_card = self._create_card(self.stats_frame, "Total Spent", "₹0.00", theme.COLOR_DANGER)
        self.spent_card.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        self.stats_frame.grid_columnconfigure(0, weight=1)
        self.stats_frame.grid_columnconfigure(1, weight=1)
        self.stats_frame.grid_columnconfigure(2, weight=1)

        self.stats_frame2 = ctk.CTkFrame(self.left_column, fg_color="transparent")
        self.stats_frame2.grid(row=3, column=0, sticky="ew", pady=(0, 6))

        self.savings_card = self._create_card(self.stats_frame2, "Savings Balance", "₹0.00", theme.COLOR_SUCCESS)
        self.savings_card.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.ef_card = self._create_card(self.stats_frame2, "Emergency Fund", "₹0.00", "#8E44AD")
        self.ef_card.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.stats_frame2.grid_columnconfigure(0, weight=1)
        self.stats_frame2.grid_columnconfigure(1, weight=1)

        # Categories list container
        cat_hdr = ctk.CTkFrame(self.left_column, fg_color="transparent")
        cat_hdr.grid(row=4, column=0, sticky="ew", pady=(2, 3))
        self.progress_lbl = ctk.CTkLabel(cat_hdr, text="Category Limits & Progress", font=theme.FONT_SUBTITLE)
        self.progress_lbl.pack(side="left")
        self.transfer_btn = ctk.CTkButton(
            cat_hdr, text="🔄 Transfer Budget", font=theme.FONT_SMALL, width=130, height=26,
            fg_color="transparent", border_width=1, border_color=theme.COLOR_CARD_BORDER,
            hover_color=theme.COLOR_CARD_BG, command=self._open_budget_transfer_dialog
        )
        self.transfer_btn.pack(side="right")

        self.categories_container = ctk.CTkScrollableFrame(
            self.left_column,
            fg_color=theme.COLOR_CARD_BG,
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12
        )
        self.categories_container.grid(row=5, column=0, sticky="nsew", pady=(0, 10))
        self.left_column.grid_rowconfigure(5, weight=1)

        # Right Column (Matplotlib Charts)
        self.right_column = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 10), pady=10)
        self.right_column.grid_columnconfigure(0, weight=1)

        # Guide banner for chart filter
        self.filter_banner = ctk.CTkFrame(self.right_column, fg_color=theme.COLOR_BANNER_BG, corner_radius=8)
        self.filter_banner.grid(row=0, column=0, sticky="ew", pady=(10, 10))
        self.filter_lbl = ctk.CTkLabel(
            self.filter_banner,
            text="💡 Click a category slice in the Pie Chart to filter trends. Press Esc to reset.",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_BANNER_TEXT
        )
        self.filter_lbl.pack(padx=12, pady=6)

        # Instantiate Matplotlib figures (3 charts)
        self._setup_charts()

    def _create_card(self, parent, title, value, color_indicator):
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.COLOR_CARD_BG,
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=8,
            height=70  # fixed height — prevents grid from stretching cards
        )
        card.pack_propagate(False)

        indicator = ctk.CTkFrame(card, width=3, fg_color=color_indicator, corner_radius=2)
        indicator.pack(side="left", fill="y", padx=(6, 0), pady=8)

        text_container = ctk.CTkFrame(card, fg_color="transparent")
        text_container.pack(side="left", fill="both", expand=True, padx=8, pady=(6, 8))

        title_lbl = ctk.CTkLabel(text_container, text=title, font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED)
        title_lbl.pack(anchor="w")

        val_lbl = ctk.CTkLabel(text_container, text=value, font=theme.FONT_SUBTITLE)
        val_lbl.pack(anchor="w", pady=(2, 0))

        card.title_label = title_lbl
        card.value_label = val_lbl
        return card

    def _on_month_change(self, choice):
        month = self._month_map.get(choice)
        if month and month != self.selected_month:
            self.selected_month = month
            self.refresh()

    def reset_to_current_month(self):
        current_m = date.today().isoformat()[:7]
        if self.selected_month != current_m:
            self.selected_month = current_m
            self.refresh()

    def set_active_month(self, month: str):
        """Allows external callers (like Settings Archives) to switch dashboard month."""
        self.selected_month = month
        self.refresh()

    # ------------------------------------------------------------ Chart Setup & Drawing
    def _get_theme_colors(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            return {
                "bg": "#1e1e1e",
                "card_bg": "#252525",
                "fg": "#FFFFFF",
                "grid": "#444444",
                "pie_palette": ["#2E86AB", "#5CB85C", "#F0AD4E", "#8E44AD", "#E74C3C", "#34495E"],
                "savings": "#5CB85C",
                "spent": "#D9534F",
                "income": "#2E86AB"
            }
        else:
            return {
                "bg": "#f0f0f0",
                "card_bg": "#F8F9FA",
                "fg": "#333333",
                "grid": "#DDDDDD",
                "pie_palette": ["#1A73E8", "#449D44", "#EC971F", "#8E44AD", "#C9302C", "#34495E"],
                "savings": "#449D44",
                "spent": "#C9302C",
                "income": "#1A73E8"
            }

    def _setup_charts(self):
        colors = self._get_theme_colors()

        # Row 1: Pie Chart & Pace Chart (Side by Side inside a container)
        row1_frame = ctk.CTkFrame(self.right_column, fg_color="transparent")
        row1_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        row1_frame.grid_columnconfigure(0, weight=1)
        row1_frame.grid_columnconfigure(1, weight=1)

        # Pie Card
        pie_card = ctk.CTkFrame(row1_frame, fg_color=colors["card_bg"], border_width=1, border_color=theme.COLOR_CARD_BORDER, corner_radius=12)
        pie_card.grid(row=0, column=0, padx=(0, 6), sticky="nsew")
        ctk.CTkLabel(pie_card, text="Spending Shares", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 0))

        self.pie_fig = plt.Figure(figsize=(3.2, 2.5), facecolor=colors["card_bg"])
        self.pie_ax = self.pie_fig.add_subplot(111)
        self.pie_canvas = FigureCanvasTkAgg(self.pie_fig, master=pie_card)
        pie_widget = self.pie_canvas.get_tk_widget()
        pie_widget.pack(fill="both", expand=True, padx=10, pady=10)
        self.pie_fig.canvas.mpl_connect("pick_event", self._on_pie_click)
        pie_widget.bind("<Button-1>", self._on_pie_tk_click)

        # Pace Card
        pace_card = ctk.CTkFrame(row1_frame, fg_color=colors["card_bg"], border_width=1, border_color=theme.COLOR_CARD_BORDER, corner_radius=12)
        pace_card.grid(row=0, column=1, padx=(6, 0), sticky="nsew")
        ctk.CTkLabel(pace_card, text="Month Pace & Projection", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=15, pady=(10, 0))

        self.pace_fig = plt.Figure(figsize=(3.2, 2.5), facecolor=colors["card_bg"])
        self.pace_ax = self.pace_fig.add_subplot(111)
        self.pace_canvas = FigureCanvasTkAgg(self.pace_fig, master=pace_card)
        self.pace_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Hover support — data arrays populated on each _draw_pace_chart() call.
        self._pace_actual_x, self._pace_actual_y = [], []
        self._pace_proj_x, self._pace_proj_y = [], []
        self.pace_annotation = None

        # NOTE: we deliberately do NOT use mpl_connect("motion_notify_event", ...)
        # here. FigureCanvasTkAgg derives matplotlib's mouse coordinates from raw
        # Tk <Motion> events, but Tk reports position in logical pixels while the
        # matplotlib renderer buffer is sized in physical/device pixels. On any
        # display where those differ — Retina/HiDPI screens, or just CustomTkinter's
        # own UI scaling — mpl's computed position lands outside the axes bounding
        # box, so event.inaxes is None even when the cursor is visibly on the chart,
        # and the tooltip never shows. Binding directly to the Tk widget and doing
        # the buffer/window scale correction ourselves avoids that entirely.
        pace_widget = self.pace_canvas.get_tk_widget()
        pace_widget.bind("<Motion>", self._on_pace_hover)
        pace_widget.bind("<Leave>", self._on_pace_leave)

        # Row 2: Trend Chart (Full Width)
        trend_card = ctk.CTkFrame(self.right_column, fg_color=colors["card_bg"], border_width=1, border_color=theme.COLOR_CARD_BORDER, corner_radius=12)
        trend_card.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.trend_title_lbl = ctk.CTkLabel(trend_card, text="Monthly Trend: All Categories", font=theme.FONT_BODY_BOLD)
        self.trend_title_lbl.pack(anchor="w", padx=15, pady=(10, 0))

        self.trend_fig = plt.Figure(figsize=(6.4, 2.5), facecolor=colors["card_bg"])
        self.trend_ax = self.trend_fig.add_subplot(111)
        self.trend_canvas = FigureCanvasTkAgg(self.trend_fig, master=trend_card)
        self.trend_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        trend_widget = self.trend_canvas.get_tk_widget()
        trend_widget.bind("<Motion>", self._on_trend_hover)
        trend_widget.bind("<Leave>", self._on_trend_leave)
        self.trend_annotation = None
        self._trend_history = []

        # Bind Esc to reset trend filter
        self.winfo_toplevel().bind("<Escape>", lambda e: self.reset_category_trend())

    def _draw_pie_chart(self, categories, colors):
        self.pie_ax.clear()
        self.pie_fig.patch.set_facecolor(colors["card_bg"])
        self.pie_ax.set_facecolor(colors["card_bg"])

        # Filter for spent categories only
        pie_data = [(c["category_name"], c["spent"]) for c in categories if c["spent"] > 0]

        if not pie_data:
            # Empty state circle
            self.pie_ax.pie([1], labels=["No spent data"], colors=["#444444" if ctk.get_appearance_mode() == "Dark" else "#DDDDDD"], startangle=90, textprops={'color': colors["fg"], 'fontsize': 9})
            self.pie_wedges = []
            self.pie_labels = []
        else:
            labels = [d[0] for d in pie_data]
            values = [d[1] for d in pie_data]

            # Palette assignment
            colors_list = colors["pie_palette"][:len(values)]
            while len(colors_list) < len(values):
                colors_list.extend(colors["pie_palette"])

            self.pie_wedges, texts, autotexts = self.pie_ax.pie(
                values,
                labels=labels,
                autopct='%1.0f%%',
                colors=colors_list,
                startangle=140,
                textprops={'color': colors["fg"], 'fontsize': 8}
            )
            self.pie_labels = labels

            # Make wedges pickable
            for wedge in self.pie_wedges:
                wedge.set_picker(True)

            for at in autotexts:
                at.set_color("white")
                at.set_weight("bold")

        self.pie_fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        self.pie_canvas.draw()

    def _draw_pace_chart(self, projection_data, colors):
        self.pace_ax.clear()
        self.pace_fig.patch.set_facecolor(colors["card_bg"])
        self.pace_ax.set_facecolor(colors["card_bg"])

        self.pace_ax.tick_params(colors=colors["fg"], labelsize=8)
        self.pace_ax.grid(True, color=colors["grid"], linestyle=":", alpha=0.5)

        self._pace_data = projection_data or {}
        self._pace_actual_map = {}
        self._pace_proj_map = {}

        has_plots = False
        spent_act = []
        spent_proj = []
        actual = self._pace_data.get("actual", [])
        if actual:
            days_act = [d["day"] for d in actual]
            spent_act = [d["cumulative_spent"] for d in actual]
            self.pace_ax.plot(days_act, spent_act, color=colors["income"], label="Actual", linewidth=2.5)
            self._pace_actual_map = {d["day"]: d for d in actual}
            has_plots = True

        proj = self._pace_data.get("projection", [])
        if proj:
            days_proj = [p["day"] for p in proj]
            spent_proj = [p["projected_cumulative"] for p in proj]
            self.pace_ax.plot(days_proj, spent_proj, color=colors["spent"], label="Projected", linestyle="--", linewidth=2.0)
            self._pace_proj_map = {p["day"]: p for p in proj}
            has_plots = True

        days_in_month = self._pace_data.get("days_in_month", 31)
        self.pace_ax.set_xlim(1, days_in_month)
        if has_plots:
            self.pace_ax.legend(facecolor=colors["card_bg"], edgecolor="none", labelcolor=colors["fg"], fontsize=8)

        for spine in self.pace_ax.spines.values():
            spine.set_color(colors["grid"])

        # Guideline and snapping marker
        self.pace_vline = self.pace_ax.axvline(x=1, color=colors["grid"], linestyle=":", alpha=0.7, zorder=5)
        self.pace_vline.set_visible(False)

        self.pace_marker, = self.pace_ax.plot([], [], marker="o", markersize=6,
                                              markerfacecolor="#FFFFFF", markeredgecolor=colors["income"],
                                              markeredgewidth=2, zorder=10)

        is_dark = ctk.get_appearance_mode() == "Dark"
        box_bg = "#1A2530" if is_dark else "#FFFFFF"
        box_fg = "#FFFFFF" if is_dark else "#222222"
        accent = colors["income"]
        self.pace_annotation = self.pace_ax.annotate(
            "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc=box_bg, ec=accent, lw=1.5),
            color=box_fg, fontsize=8, ha="left", va="bottom", zorder=15,
            arrowprops=dict(arrowstyle="->", color=accent),
        )
        self.pace_annotation.set_visible(False)

        # Clean y-limits
        self.pace_ax.set_ylim(bottom=0)
        y_max = max(
            max(spent_act, default=0.0),
            max(spent_proj, default=0.0)
        )
        if y_max <= 0:
            self.pace_ax.set_ylim(0, 1000)
        else:
            self.pace_ax.set_ylim(0, y_max * 1.1)

        self.pace_fig.tight_layout()
        self.pace_canvas.draw()

    def _draw_trend_chart(self, colors):
        self.trend_ax.clear()
        self.trend_fig.patch.set_facecolor(colors["card_bg"])
        self.trend_ax.set_facecolor(colors["card_bg"])

        self.trend_ax.tick_params(colors=colors["fg"], labelsize=8)
        self.trend_ax.grid(True, color=colors["grid"], linestyle=":", alpha=0.5)

        spent = []
        rollover = []
        try:
            history = budget_logic.get_historical_trend(
                category_id=self.selected_category_id,
                db_path=self.db_path
            )
            self._trend_history = history
            months = [h["month"] for h in history]
            spent = [h["spent"] for h in history]
            x_indices = list(range(len(months)))

            if self.selected_category_id is None:
                rollover = [h["rollover"] for h in history]
                self.trend_ax.plot(x_indices, spent, marker="o", color=colors["spent"], label="Total Spent", linewidth=2.0)
                self.trend_ax.plot(x_indices, rollover, marker="s", color=colors["savings"], label="Savings Rollover", linewidth=2.0)
                self.trend_title_lbl.configure(text="Monthly Trend: All Categories")
            else:
                self.trend_ax.plot(x_indices, spent, marker="o", color=colors["income"], label="Category Spent", linewidth=2.0)
                self.trend_title_lbl.configure(text=f"Monthly Trend: {self.selected_category_name}")

            self.trend_ax.set_xticks(x_indices)
            self.trend_ax.set_xticklabels(months)
            self.trend_ax.legend(facecolor=colors["card_bg"], edgecolor="none", labelcolor=colors["fg"], fontsize=8)
        except Exception:
            self._trend_history = []

        for spine in self.trend_ax.spines.values():
            spine.set_color(colors["grid"])

        self.trend_vline = self.trend_ax.axvline(x=0, color=colors["grid"], linestyle=":", alpha=0.7, zorder=5)
        self.trend_vline.set_visible(False)

        self.trend_marker, = self.trend_ax.plot([], [], marker="o", markersize=7,
                                                markerfacecolor="#FFFFFF", markeredgecolor=colors["spent"],
                                                markeredgewidth=2, zorder=10)

        is_dark = ctk.get_appearance_mode() == "Dark"
        box_bg = "#1A2530" if is_dark else "#FFFFFF"
        box_fg = "#FFFFFF" if is_dark else "#222222"
        accent = colors["income"]
        self.trend_annotation = self.trend_ax.annotate(
            "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc=box_bg, ec=accent, lw=1.5),
            color=box_fg, fontsize=8, ha="left", va="bottom", zorder=15,
            arrowprops=dict(arrowstyle="->", color=accent),
        )
        self.trend_annotation.set_visible(False)

        self.trend_ax.set_ylim(bottom=0)
        max_val = max(spent, default=0.0)
        if self.selected_category_id is None:
            max_val = max(max_val, max(rollover, default=0.0))
        if max_val <= 0:
            self.trend_ax.set_ylim(0, 1000)
        else:
            self.trend_ax.set_ylim(0, max_val * 1.15)

        self.trend_fig.tight_layout()
        self.trend_canvas.draw()

    def _apply_category_filter(self, cat_name: str):
        """Filters the 6-month historical trend chart by category."""
        try:
            cat = categories_api.get_category_by_name(cat_name, self.db_path)
            if cat:
                self.selected_category_id = cat["id"]
                self.selected_category_name = cat["name"]
                colors = self._get_theme_colors()
                self.filter_lbl.configure(
                    text=f"📌 Filtering trend by: {self.selected_category_name}. Press Esc to clear filter.",
                    text_color=colors["income"]
                )
                self._draw_trend_chart(colors)
        except Exception:
            pass

    def _on_pie_tk_click(self, tk_event):
        """Direct Tk Button-1 handler to ensure slice clicks always register even on HiDPI."""
        if not hasattr(self, "pie_wedges") or not self.pie_wedges or not hasattr(self, "pie_labels") or not self.pie_labels:
            return

        widget = self.pie_canvas.get_tk_widget()
        buf_w, buf_h = self.pie_fig.canvas.get_width_height()
        win_w = max(widget.winfo_width(), 1)
        win_h = max(widget.winfo_height(), 1)
        scale_x = buf_w / win_w
        scale_y = buf_h / win_h

        x = tk_event.x * scale_x
        y = buf_h - (tk_event.y * scale_y)

        try:
            data_x, data_y = self.pie_ax.transData.inverted().transform((x, y))
        except Exception:
            return

        import math
        r = math.hypot(data_x, data_y)
        if r > 1.25:
            return

        angle = math.degrees(math.atan2(data_y, data_x)) % 360
        for idx, wedge in enumerate(self.pie_wedges):
            t1 = wedge.theta1 % 360
            t2 = wedge.theta2 % 360
            matched = False
            if t1 <= t2:
                matched = (t1 <= angle <= t2)
            else:
                matched = (angle >= t1 or angle <= t2)
            if matched and idx < len(self.pie_labels):
                self._apply_category_filter(self.pie_labels[idx])
                return

    def _on_pie_click(self, event):
        """Fallback Matplotlib pick event on slice to filter trend chart."""
        if not hasattr(self, "pie_wedges") or not self.pie_wedges:
            return

        if event.artist in self.pie_wedges:
            idx = self.pie_wedges.index(event.artist)
            if idx < len(self.pie_labels):
                self._apply_category_filter(self.pie_labels[idx])

    def reset_category_trend(self):
        """Reset historical trend filter back to general summary."""
        if self.selected_category_id is not None:
            self.selected_category_id = None
            self.selected_category_name = None
            self.filter_lbl.configure(
                text="💡 Click a category slice in the Pie Chart or name below to filter trends. Press Esc to reset.",
                text_color=theme.COLOR_BANNER_TEXT
            )
            colors = self._get_theme_colors()
            self._draw_trend_chart(colors)

    # ------------------------------------------------------------ Pace & Trend chart hover
    def _on_pace_leave(self, _event=None):
        if hasattr(self, "pace_annotation") and self.pace_annotation is not None and self.pace_annotation.get_visible():
            self.pace_annotation.set_visible(False)
            if hasattr(self, "pace_marker"):
                self.pace_marker.set_data([], [])
            if hasattr(self, "pace_vline"):
                self.pace_vline.set_visible(False)
            self.pace_canvas.draw_idle()

    def _on_pace_hover(self, tk_event):
        """
        Handle raw Tk <Motion> events over the pace-chart canvas, snapping to the
        nearest day and showing formatted date, cumulative total, and daily spend.
        """
        if not hasattr(self, "pace_annotation") or self.pace_annotation is None:
            return

        actual_map = getattr(self, "_pace_actual_map", {})
        proj_map = getattr(self, "_pace_proj_map", {})
        if not actual_map and not proj_map:
            return

        widget = self.pace_canvas.get_tk_widget()
        buf_w, buf_h = self.pace_fig.canvas.get_width_height()
        win_w = max(widget.winfo_width(), 1)
        win_h = max(widget.winfo_height(), 1)
        scale_x = buf_w / win_w
        scale_y = buf_h / win_h

        x = tk_event.x * scale_x
        y = buf_h - (tk_event.y * scale_y)

        try:
            data_x, data_y = self.pace_ax.transData.inverted().transform((x, y))
        except Exception:
            return

        x0, x1 = sorted(self.pace_ax.get_xlim())
        y0, y1 = sorted(self.pace_ax.get_ylim())
        if not (x0 <= data_x <= x1 and y0 <= data_y <= y1):
            self._on_pace_leave()
            return

        days_in_month = getattr(self, "_pace_data", {}).get("days_in_month", 31)
        target_day = int(round(data_x))
        target_day = max(1, min(days_in_month, target_day))

        colors = self._get_theme_colors()
        if target_day in actual_map:
            item = actual_map[target_day]
            val_y = item["cumulative_spent"]
            date_str = item.get("date", f"Day {target_day}")
            try:
                y_i, m_i, d_i = [int(p) for p in date_str.split("-")]
                formatted_date = date(y_i, m_i, d_i).strftime("%a, %d %b %Y")
            except Exception:
                formatted_date = date_str

            daily_spent = item.get("daily_spent", 0.0)
            text = f"📅 {formatted_date}\nTotal Spent: {self.currency}{val_y:,.2f}\nDaily Spent: +{self.currency}{daily_spent:,.2f}"
            marker_color = colors["income"]
        elif target_day in proj_map:
            item = proj_map[target_day]
            val_y = item["projected_cumulative"]
            date_str = item.get("date", f"Day {target_day}")
            try:
                y_i, m_i, d_i = [int(p) for p in date_str.split("-")]
                formatted_date = date(y_i, m_i, d_i).strftime("%a, %d %b %Y")
            except Exception:
                formatted_date = date_str

            text = f"📅 {formatted_date} (Proj)\nEst. Total: {self.currency}{val_y:,.2f}"
            marker_color = colors["spent"]
        else:
            self._on_pace_leave()
            return

        # Smart offset: flip horizontally if near right edge, flip vertically if near top
        try:
            ax = self.pace_ax
            disp_pt = ax.transData.transform((target_day, val_y))
            ax_bbox = ax.get_window_extent()
            frac_x = (disp_pt[0] - ax_bbox.x0) / max(ax_bbox.width, 1)
            frac_y = (disp_pt[1] - ax_bbox.y0) / max(ax_bbox.height, 1)
            off_x = -60 if frac_x > 0.6 else 12
            off_y = -55 if frac_y > 0.7 else 12
            ha = "right" if frac_x > 0.6 else "left"
            va = "top" if frac_y > 0.7 else "bottom"
        except Exception:
            off_x, off_y, ha, va = 12, 12, "left", "bottom"
        self.pace_annotation.set_ha(ha)
        self.pace_annotation.set_va(va)
        self.pace_annotation.xytext = (off_x, off_y)

        self.pace_marker.set_data([target_day], [val_y])
        self.pace_marker.set_markeredgecolor(marker_color)
        self.pace_vline.set_xdata([target_day, target_day])
        self.pace_vline.set_visible(True)

        self.pace_annotation.xy = (target_day, val_y)
        self.pace_annotation.set_text(text)
        self.pace_annotation.set_visible(True)
        self.pace_canvas.draw_idle()

    def _on_trend_leave(self, _event=None):
        if hasattr(self, "trend_annotation") and self.trend_annotation is not None and self.trend_annotation.get_visible():
            self.trend_annotation.set_visible(False)
            if hasattr(self, "trend_marker"):
                self.trend_marker.set_data([], [])
            if hasattr(self, "trend_vline"):
                self.trend_vline.set_visible(False)
            self.trend_canvas.draw_idle()

    def _on_trend_hover(self, tk_event):
        """
        Handle raw Tk <Motion> events over the monthly trend canvas, snapping
        to the nearest month and showing spent vs savings rollover.
        """
        if not hasattr(self, "trend_annotation") or self.trend_annotation is None or not getattr(self, "_trend_history", []):
            return

        widget = self.trend_canvas.get_tk_widget()
        buf_w, buf_h = self.trend_fig.canvas.get_width_height()
        win_w = max(widget.winfo_width(), 1)
        win_h = max(widget.winfo_height(), 1)
        scale_x = buf_w / win_w
        scale_y = buf_h / win_h

        x = tk_event.x * scale_x
        y = buf_h - (tk_event.y * scale_y)

        try:
            data_x, data_y = self.trend_ax.transData.inverted().transform((x, y))
        except Exception:
            return

        x0, x1 = sorted(self.trend_ax.get_xlim())
        y0, y1 = sorted(self.trend_ax.get_ylim())
        if not (x0 <= data_x <= x1 and y0 <= data_y <= y1):
            self._on_trend_leave()
            return

        idx = int(round(data_x))
        if not (0 <= idx < len(self._trend_history)):
            self._on_trend_leave()
            return

        item = self._trend_history[idx]
        month_str = item["month"]
        spent_val = item["spent"]
        rollover_val = item.get("rollover", 0.0)

        try:
            y_i, m_i = [int(p) for p in month_str.split("-")]
            month_fmt = date(y_i, m_i, 1).strftime("%B %Y")
        except Exception:
            month_fmt = month_str

        if self.selected_category_id is None:
            text = f"📅 {month_fmt}\nTotal Spent: {self.currency}{spent_val:,.2f}\nSavings Rollover: {self.currency}{rollover_val:,.2f}"
        else:
            text = f"📅 {month_fmt}\n{self.selected_category_name}: {self.currency}{spent_val:,.2f}"

        # Smart offset: flip horizontally if near right edge, flip vertically if near top
        try:
            ax = self.trend_ax
            disp_pt = ax.transData.transform((idx, spent_val))
            ax_bbox = ax.get_window_extent()
            frac_x = (disp_pt[0] - ax_bbox.x0) / max(ax_bbox.width, 1)
            frac_y = (disp_pt[1] - ax_bbox.y0) / max(ax_bbox.height, 1)
            off_x = -60 if frac_x > 0.6 else 12
            off_y = -55 if frac_y > 0.7 else 12
            ha = "right" if frac_x > 0.6 else "left"
            va = "top" if frac_y > 0.7 else "bottom"
        except Exception:
            off_x, off_y, ha, va = 12, 12, "left", "bottom"
        self.trend_annotation.set_ha(ha)
        self.trend_annotation.set_va(va)
        self.trend_annotation.xytext = (off_x, off_y)

        self.trend_marker.set_data([idx], [spent_val])
        self.trend_vline.set_xdata([idx, idx])
        self.trend_vline.set_visible(True)

        self.trend_annotation.xy = (idx, spent_val)
        self.trend_annotation.set_text(text)
        self.trend_annotation.set_visible(True)
        self.trend_canvas.draw_idle()

    # ------------------------------------------------------------ State Refreshes
    def refresh(self):
        # --- Phase 1: Data loading and category list --- #
        try:
            current_month = date.today().isoformat()[:7]
            if not hasattr(self, "selected_month") or not self.selected_month:
                self.selected_month = current_month

            # Populate Month Selector options
            avail_months = budget_logic.get_available_months(self.db_path)
            if self.selected_month not in avail_months:
                avail_months.append(self.selected_month)
                avail_months.sort(reverse=True)

            self._month_map = {}
            display_choices = []
            for m in avail_months:
                try:
                    y_i, m_i = [int(p) for p in m.split("-")]
                    m_str = date(y_i, m_i, 1).strftime("%b %Y")
                except Exception:
                    m_str = m

                disp = f"📅 {m_str} (Current)" if m == current_month else f"📁 {m_str} (Archive)"
                self._month_map[disp] = m
                display_choices.append(disp)

            self.month_menu.configure(values=display_choices)
            for disp, m in self._month_map.items():
                if m == self.selected_month:
                    self.month_var.set(disp)
                    break

            is_archive = (self.selected_month != current_month)
            if is_archive:
                try:
                    y_i, m_i = [int(p) for p in self.selected_month.split("-")]
                    name_str = date(y_i, m_i, 1).strftime("%B %Y")
                except Exception:
                    name_str = self.selected_month
                self.archive_banner_label.configure(text=f"📁 Archive View: {name_str} (Closed) — Read-Only Mode")
                self.archive_banner.grid(row=1, column=0, sticky="ew", pady=(0, 6))
                self.transfer_btn.configure(state="disabled")
            else:
                self.archive_banner.grid_forget()
                self.transfer_btn.configure(state="normal")

            summary = budget_logic.dashboard_summary(month=self.selected_month, db_path=self.db_path)

            # Update Stats metric cards
            total_income = summary['total_income']
            total_spent = summary['total_spent']
            available = summary['available_to_spend']

            # Colour the available card: green when healthy, orange when low (<20% left), red when <= 0
            if total_income > 0:
                pct_left = available / total_income
            else:
                pct_left = 1.0 if available >= 0 else -1.0

            if available <= 0 or pct_left <= 0:
                avail_color = theme.COLOR_DANGER
            elif pct_left <= 0.2:
                avail_color = theme.COLOR_WARNING
            else:
                avail_color = "#27AE60"

            from app.settings import get_setting
            currency = get_setting("currency_symbol", self.db_path) or "₹"
            self.currency = currency  # exposed on self so _on_pace_hover can use it too

            if is_archive:
                self.available_card.title_label.configure(text="Month Net Leftover")
                self.income_card.title_label.configure(text="Final Income")
                self.spent_card.title_label.configure(text="Final Spent")
                self.savings_card.title_label.configure(text="Rolled to Savings")
                self.savings_card.value_label.configure(text=f"{currency}{summary.get('month_rollover', 0.0):.2f}")
                self.ef_card.title_label.configure(text="Rolled to EF")
                self.ef_card.value_label.configure(text=f"{currency}{summary.get('month_ef_delta', 0.0):.2f}")
            else:
                self.available_card.title_label.configure(text="Available to Spend")
                self.income_card.title_label.configure(text="Total Income")
                self.spent_card.title_label.configure(text="Total Spent")
                self.savings_card.title_label.configure(text="Savings Balance")
                self.savings_card.value_label.configure(text=f"{currency}{summary['savings_balance']:.2f}")
                self.ef_card.title_label.configure(text="Emergency Fund")
                self.ef_card.value_label.configure(text=f"{currency}{summary['emergency_fund_balance']:.2f}")

            self.available_card.value_label.configure(
                text=f"{currency}{available:.2f}",
                text_color=avail_color
            )
            self.income_card.value_label.configure(text=f"{currency}{total_income:.2f}")
            self.spent_card.value_label.configure(text=f"{currency}{total_spent:.2f}")

            if self.is_privacy_mode:
                self.available_card.value_label.configure(text=f"{currency} ••••••")
                self.income_card.value_label.configure(text=f"{currency} ••••••")
                self.spent_card.value_label.configure(text=f"{currency} ••••••")
                self.savings_card.value_label.configure(text=f"{currency} ••••••")
                self.ef_card.value_label.configure(text=f"{currency} ••••••")

            # Update Left-column Category Limit Scale List
            for widget in self.categories_container.winfo_children():
                widget.destroy()

            categories = summary.get("categories", [])
            if not categories:
                ctk.CTkLabel(
                    self.categories_container,
                    text="No budget categories set up yet.",
                    font=theme.FONT_BODY,
                    text_color=theme.COLOR_MUTED
                ).pack(pady=40)
            else:
                for cat in categories:
                    cat_frame = ctk.CTkFrame(self.categories_container, fg_color="transparent")
                    cat_frame.pack(fill="x", pady=6, padx=10)

                    # Text Labels
                    lbl_frame = ctk.CTkFrame(cat_frame, fg_color="transparent")
                    lbl_frame.pack(fill="x")
                    cat_name_str = cat["category_name"]
                    cat_lbl = ctk.CTkLabel(lbl_frame, text=cat_name_str, font=theme.FONT_BODY_BOLD, cursor="pointinghand")
                    cat_lbl.pack(side="left")
                    cat_lbl.bind("<Button-1>", lambda e, c=cat_name_str: self._apply_category_filter(c))

                    limit_text = f"{currency}{cat['spent']:.2f} of {currency}{cat['hard_limit']:.2f}"
                    ctk.CTkLabel(lbl_frame, text=limit_text, font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED).pack(side="right")

                    # Custom Canvas Limit Ticks progress bar
                    lbar = LimitBar(
                        cat_frame,
                        spent=cat["spent"],
                        soft_limit=cat["soft_limit"],
                        hard_limit=cat["hard_limit"],
                        state=cat["state"]
                    )
                    lbar.pack(fill="x", pady=(2, 2))

                    # Proximity status warning message
                    if cat.get("message"):
                        msg_color = theme.COLOR_SUCCESS
                        if cat["state"] == "approaching_hard":
                            msg_color = theme.COLOR_WARNING
                        elif cat["state"] == "at_hard":
                            msg_color = theme.COLOR_WARNING
                        elif cat["state"] == "over_hard":
                            msg_color = theme.COLOR_DANGER
                        ctk.CTkLabel(cat_frame, text=cat["message"], font=theme.FONT_SMALL, text_color=msg_color, anchor="w").pack(fill="x")

        except Exception as e:
            for widget in self.categories_container.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.categories_container,
                text=f"Error loading dashboard data: {e}",
                font=theme.FONT_BODY,
                text_color=theme.COLOR_DANGER
            ).pack(pady=40)
            # Still attempt chart refresh below with last known data
            categories = []
            summary = {}

        # --- Phase 2: Chart rendering (errors are isolated) --- #
        colors = self._get_theme_colors()
        try:
            self._draw_pie_chart(categories, colors)
        except Exception:
            pass  # Pie render failures are non-fatal

        try:
            self._draw_pace_chart(summary.get("projection", {}), colors)
        except Exception as e:
            import traceback
            traceback.print_exc()

        try:
            self._draw_trend_chart(colors)
        except Exception:
            pass  # Trend chart failures are non-fatal

    def _open_budget_transfer_dialog(self):
        BudgetTransferDialog(
            self.winfo_toplevel(),
            db_path=self.db_path,
            month=self.selected_month,
            on_transferred=self.refresh
        )