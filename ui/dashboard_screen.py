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


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master, db_path):
        super().__init__(master, fg_color="transparent")
        self.db_path = db_path
        self.selected_category_id = None
        self.selected_category_name = None
        self.currency = "₹"

        self._build()
        self.refresh()

    def _build(self):
        # Configure layout: left side has stats and list, right side has charts
        self.grid_columnconfigure(0, weight=1, minsize=400)
        self.grid_columnconfigure(1, weight=1, minsize=550)
        self.grid_rowconfigure(0, weight=1)

        # Left Column (Stats & Progress List)
        left_column = ctk.CTkFrame(self, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(10, 10), pady=10)
        left_column.grid_columnconfigure(0, weight=1)
        left_column.grid_rowconfigure(4, weight=1)  # Categories list row expands

        # Header Title
        ctk.CTkLabel(left_column, text="Dashboard", font=theme.FONT_TITLE).grid(row=0, column=0, sticky="w", pady=(10, 8))

        # Overview Stats Cards — Row 1: Available, Income, Spent
        self.stats_frame = ctk.CTkFrame(left_column, fg_color="transparent")
        self.stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self.available_card = self._create_card(self.stats_frame, "Available to Spend", "₹0.00", "#27AE60")
        self.available_card.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.income_card = self._create_card(self.stats_frame, "Total Income", "₹0.00", theme.COLOR_PRIMARY)
        self.income_card.grid(row=0, column=1, padx=6, sticky="ew")

        self.spent_card = self._create_card(self.stats_frame, "Total Spent", "₹0.00", theme.COLOR_DANGER)
        self.spent_card.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        self.stats_frame.grid_columnconfigure(0, weight=1)
        self.stats_frame.grid_columnconfigure(1, weight=1)
        self.stats_frame.grid_columnconfigure(2, weight=1)

        self.stats_frame2 = ctk.CTkFrame(left_column, fg_color="transparent")
        self.stats_frame2.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        self.savings_card = self._create_card(self.stats_frame2, "Savings Balance", "₹0.00", theme.COLOR_SUCCESS)
        self.savings_card.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.ef_card = self._create_card(self.stats_frame2, "Emergency Fund", "₹0.00", "#8E44AD")
        self.ef_card.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self.stats_frame2.grid_columnconfigure(0, weight=1)
        self.stats_frame2.grid_columnconfigure(1, weight=1)

        # Categories list container
        progress_lbl = ctk.CTkLabel(left_column, text="Category Limits & Progress", font=theme.FONT_SUBTITLE)
        progress_lbl.grid(row=3, column=0, sticky="w", pady=(2, 3))

        self.categories_container = ctk.CTkScrollableFrame(
            left_column,
            fg_color=theme.COLOR_CARD_BG,
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12
        )
        self.categories_container.grid(row=4, column=0, sticky="nsew", pady=(0, 10))
        left_column.grid_rowconfigure(4, weight=1)

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

        card.value_label = val_lbl
        return card

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
        self.pie_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self.pie_fig.canvas.mpl_connect("pick_event", self._on_pie_click)

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

        # Reset hover data for this refresh — repopulated below.
        self._pace_actual_x, self._pace_actual_y = [], []
        self._pace_proj_x, self._pace_proj_y = [], []

        has_plots = False
        actual = projection_data.get("actual", [])
        if actual:
            days_act = [d["day"] for d in actual]
            spent_act = [d["cumulative_spent"] for d in actual]
            self.pace_ax.plot(days_act, spent_act, color=colors["income"], label="Actual", linewidth=2.5)
            self._pace_actual_x, self._pace_actual_y = days_act, spent_act
            has_plots = True

        proj = projection_data.get("projection", [])
        if proj:
            days_proj = [p["day"] for p in proj]
            spent_proj = [p["projected_cumulative"] for p in proj]
            self.pace_ax.plot(days_proj, spent_proj, color=colors["spent"], label="Projected", linestyle="--", linewidth=2.0)
            self._pace_proj_x, self._pace_proj_y = days_proj, spent_proj
            has_plots = True

        self.pace_ax.set_xlim(1, projection_data.get("days_in_month", 31))
        if has_plots:
            self.pace_ax.legend(facecolor=colors["card_bg"], edgecolor="none", labelcolor=colors["fg"], fontsize=8)

        for spine in self.pace_ax.spines.values():
            spine.set_color(colors["grid"])

        # clear() destroys any previous annotation artist, so it must be
        # recreated fresh every redraw, after clear() and before draw().
        self.pace_annotation = self.pace_ax.annotate(
            "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4", fc="#1a2530", ec=theme.COLOR_PRIMARY, lw=1),
            color="white", fontsize=8, ha="left", va="bottom", zorder=10,
            arrowprops=dict(arrowstyle="->", color=theme.COLOR_PRIMARY),
        )
        self.pace_annotation.set_visible(False)

        self.pace_fig.tight_layout()
        self.pace_canvas.draw()

    def _draw_trend_chart(self, colors):
        self.trend_ax.clear()
        self.trend_fig.patch.set_facecolor(colors["card_bg"])
        self.trend_ax.set_facecolor(colors["card_bg"])

        self.trend_ax.tick_params(colors=colors["fg"], labelsize=8)
        self.trend_ax.grid(True, color=colors["grid"], linestyle=":", alpha=0.5)

        try:
            # Query the historical trend data from application layer
            history = budget_logic.get_historical_trend(
                category_id=self.selected_category_id,
                db_path=self.db_path
            )

            months = [h["month"] for h in history]
            spent = [h["spent"] for h in history]

            if self.selected_category_id is None:
                rollover = [h["rollover"] for h in history]
                # Plot Spending & Rollover
                self.trend_ax.plot(months, spent, marker="o", color=colors["spent"], label="Total Spent", linewidth=2.0)
                self.trend_ax.plot(months, rollover, marker="s", color=colors["savings"], label="Savings Rollover", linewidth=2.0)
                self.trend_title_lbl.configure(text="Monthly Trend: All Categories")
            else:
                # Plot selected category spending
                self.trend_ax.plot(months, spent, marker="o", color=colors["income"], label="Category Spent", linewidth=2.0)
                self.trend_title_lbl.configure(text=f"Monthly Trend: {self.selected_category_name}")

            self.trend_ax.legend(facecolor=colors["card_bg"], edgecolor="none", labelcolor=colors["fg"], fontsize=8)
        except Exception:
            pass  # Fail silently if DB schema not written or empty

        # Style borders
        for spine in self.trend_ax.spines.values():
            spine.set_color(colors["grid"])

        self.trend_fig.tight_layout()
        self.trend_canvas.draw()

    def _on_pie_click(self, event):
        """Click event on slice to filter trend chart."""
        if not hasattr(self, "pie_wedges") or not self.pie_wedges:
            return

        if event.artist in self.pie_wedges:
            idx = self.pie_wedges.index(event.artist)
            cat_name = self.pie_labels[idx]

            try:
                cat = categories_api.get_category_by_name(cat_name, self.db_path)
                if cat:
                    self.selected_category_id = cat["id"]
                    self.selected_category_name = cat["name"]

                    # Highlight warning banner message
                    self.filter_lbl.configure(
                        text=f"📌 Filtering trend by: {self.selected_category_name}. Press Esc to clear filter.",
                        text_color=theme.COLOR_PRIMARY
                    )
                    # Redraw trend
                    colors = self._get_theme_colors()
                    self._draw_trend_chart(colors)
            except Exception:
                pass

    def reset_category_trend(self):
        """Reset historical trend filter back to general summary."""
        if self.selected_category_id is not None:
            self.selected_category_id = None
            self.selected_category_name = None
            self.filter_lbl.configure(
                text="💡 Click a category slice in the Pie Chart to filter trends. Press Esc to reset.",
                text_color=theme.COLOR_BANNER_TEXT
            )
            colors = self._get_theme_colors()
            self._draw_trend_chart(colors)

    # ------------------------------------------------------------ Pace chart hover
    def _on_pace_leave(self, _event=None):
        if self.pace_annotation is not None and self.pace_annotation.get_visible():
            self.pace_annotation.set_visible(False)
            self.pace_canvas.draw_idle()

    def _on_pace_hover(self, tk_event):
        """
        Handle raw Tk <Motion> events over the pace-chart canvas and manually
        map the cursor position into matplotlib data coordinates.

        We can't trust matplotlib's own motion_notify_event/event.inaxes here:
        FigureCanvasTkAgg computes it from Tk's logical-pixel coordinates, but
        the figure's actual render buffer is sized in physical/device pixels.
        Whenever those two scales differ (HiDPI/Retina displays, or scaling
        applied by CustomTkinter), the computed point falls outside the axes'
        bounding box and event.inaxes is always None — so the tooltip never
        shows even though the cursor is clearly over the chart. Doing the
        scale correction explicitly below avoids that failure mode.
        """
        if self.pace_annotation is None or not self._pace_actual_x:
            return

        widget = self.pace_canvas.get_tk_widget()
        buf_w, buf_h = self.pace_fig.canvas.get_width_height()  # physical pixels
        win_w = max(widget.winfo_width(), 1)                    # logical pixels
        win_h = max(widget.winfo_height(), 1)
        scale_x = buf_w / win_w
        scale_y = buf_h / win_h

        # Convert Tk widget coords -> matplotlib figure pixel coords.
        # Tk's origin is top-left; matplotlib's is bottom-left, so flip y.
        x = tk_event.x * scale_x
        y = buf_h - (tk_event.y * scale_y)

        # Convert figure pixel coords -> data coords for this axes.
        data_x, data_y = self.pace_ax.transData.inverted().transform((x, y))

        x0, x1 = sorted(self.pace_ax.get_xlim())
        y0, y1 = sorted(self.pace_ax.get_ylim())
        if not (x0 <= data_x <= x1 and y0 <= data_y <= y1):
            if self.pace_annotation.get_visible():
                self.pace_annotation.set_visible(False)
                self.pace_canvas.draw_idle()
            return

        actual_x = np.array(self._pace_actual_x)
        idx = int(np.argmin(np.abs(actual_x - data_x)))
        day = actual_x[idx]
        actual_val = self._pace_actual_y[idx]

        proj_val = None
        if self._pace_proj_x:
            proj_x = np.array(self._pace_proj_x)
            if proj_x.min() <= day <= proj_x.max():
                proj_val = float(np.interp(day, proj_x, self._pace_proj_y))

        text = f"Day {int(day)}\nActual: {self.currency}{actual_val:,.2f}"
        if proj_val is not None:
            text += f"\nProjected: {self.currency}{proj_val:,.2f}"

        self.pace_annotation.xy = (day, actual_val)
        self.pace_annotation.set_text(text)
        self.pace_annotation.set_visible(True)
        self.pace_canvas.draw_idle()

    # ------------------------------------------------------------ State Refreshes
    def refresh(self):
        # --- Phase 1: Data loading and category list --- #
        try:
            summary = budget_logic.dashboard_summary(db_path=self.db_path)

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

            self.available_card.value_label.configure(
                text=f"{currency}{available:.2f}",
                text_color=avail_color
            )
            self.income_card.value_label.configure(text=f"{currency}{total_income:.2f}")
            self.spent_card.value_label.configure(text=f"{currency}{total_spent:.2f}")
            self.savings_card.value_label.configure(text=f"{currency}{summary['savings_balance']:.2f}")
            self.ef_card.value_label.configure(text=f"{currency}{summary['emergency_fund_balance']:.2f}")

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
                    ctk.CTkLabel(lbl_frame, text=cat["category_name"], font=theme.FONT_BODY_BOLD).pack(side="left")

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
        except Exception:
            pass  # Pace chart failures are non-fatal

        try:
            self._draw_trend_chart(colors)
        except Exception:
            pass  # Trend chart failures are non-fatal