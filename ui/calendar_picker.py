"""
ui/calendar_picker.py — Reusable calendar date-picker widget.

Provides:
    CalendarPicker  : Compound CTkFrame (entry + 📅 button)
    CalendarPopup   : CTkToplevel floating calendar grid with month navigation

Drop-in companion for any CTkEntry used to collect YYYY-MM-DD dates.
"""

import calendar
from datetime import date
import customtkinter as ctk
from ui import theme


class CalendarPopup(ctk.CTkToplevel):
    """
    Floating popup calendar. Clicking a day writes 'YYYY-MM-DD'
    into the supplied StringVar and closes the window.
    """

    _HEADERS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, anchor_widget, string_var: ctk.StringVar):
        super().__init__(anchor_widget)
        self._var = string_var

        self.title("Select Date")
        self.resizable(False, False)
        self.transient(anchor_widget.winfo_toplevel())
        self.grab_set()
        self.focus_set()

        # Start month: use current var value, fall back to today
        try:
            d = date.fromisoformat(string_var.get().strip())
            self._year, self._month = d.year, d.month
        except (ValueError, AttributeError):
            t = date.today()
            self._year, self._month = t.year, t.month

        self._today = date.today()
        self._build()
        self._position_near(anchor_widget)

    # ---------------------------------------------------------------- build
    def _build(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#1C1C2E" if is_dark else "white"
        self.configure(fg_color=bg)

        # ── Navigation header ─────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=("gray92", "#252540"), corner_radius=0)
        hdr.pack(fill="x")

        ctk.CTkButton(
            hdr, text="‹", width=36, height=36, font=("Helvetica", 20),
            fg_color="transparent", hover_color=("gray78", "gray30"),
            text_color=("black", "white"), command=self._prev_month
        ).pack(side="left", padx=4, pady=6)

        self._hdr_lbl = ctk.CTkLabel(
            hdr, text="", font=("Helvetica", 13, "bold"),
            text_color=("black", "white")
        )
        self._hdr_lbl.pack(side="left", expand=True)

        ctk.CTkButton(
            hdr, text="›", width=36, height=36, font=("Helvetica", 20),
            fg_color="transparent", hover_color=("gray78", "gray30"),
            text_color=("black", "white"), command=self._next_month
        ).pack(side="right", padx=4, pady=6)

        # ── Weekday header row ────────────────────────────────────────
        dow = ctk.CTkFrame(self, fg_color="transparent")
        dow.pack(padx=10, pady=(8, 2))
        for col, h in enumerate(self._HEADERS):
            color = "#E05252" if col >= 5 else ("gray50", "gray60")
            ctk.CTkLabel(
                dow, text=h, width=36, font=("Helvetica", 10, "bold"),
                text_color=color
            ).grid(row=0, column=col, padx=1)

        # ── Day grid (rebuilt on month change) ────────────────────────
        self._grid = ctk.CTkFrame(self, fg_color="transparent")
        self._grid.pack(padx=10, pady=2)

        # ── Footer: Today shortcut ────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(4, 10))
        ctk.CTkButton(
            footer, text="Today", height=28, font=("Helvetica", 11),
            fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._select_today
        ).pack(expand=True, fill="x")

        self._render_month()

    # ---------------------------------------------------------------- render
    def _render_month(self):
        for w in self._grid.winfo_children():
            w.destroy()

        self._hdr_lbl.configure(
            text=date(self._year, self._month, 1).strftime("%B %Y")
        )

        # Currently selected day (if within this month)
        selected_day = None
        try:
            d = date.fromisoformat(self._var.get().strip())
            if d.year == self._year and d.month == self._month:
                selected_day = d.day
        except (ValueError, AttributeError):
            pass

        weeks = calendar.monthcalendar(self._year, self._month)
        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(self._grid, text="", width=36, height=34).grid(
                        row=row, column=col, padx=1, pady=1
                    )
                    continue

                is_sel = (day == selected_day)
                is_today = (date(self._year, self._month, day) == self._today)
                is_wknd = (col >= 5)

                if is_sel:
                    fg, txt = theme.COLOR_PRIMARY, "white"
                    font_weight = "bold"
                elif is_today:
                    fg = ("#DCEEFF", "#1A3A5A")
                    txt = theme.COLOR_PRIMARY
                    font_weight = "bold"
                elif is_wknd:
                    fg = ("gray90", "gray22")
                    txt = "#E05252"
                    font_weight = "normal"
                else:
                    fg = ("gray90", "gray22")
                    txt = ("black", "white")
                    font_weight = "normal"

                ctk.CTkButton(
                    self._grid, text=str(day),
                    width=36, height=34,
                    font=("Helvetica", 11, font_weight),
                    fg_color=fg, hover_color=("gray75", "gray35"),
                    text_color=txt, corner_radius=6,
                    command=lambda d=day: self._select(d)
                ).grid(row=row, column=col, padx=1, pady=1)

    # ---------------------------------------------------------------- actions
    def _prev_month(self):
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._render_month()

    def _next_month(self):
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._render_month()

    def _select(self, day: int):
        self._var.set(date(self._year, self._month, day).isoformat())
        self.destroy()

    def _select_today(self):
        t = self._today
        self._year, self._month = t.year, t.month
        self._select(t.day)

    # ---------------------------------------------------------------- positioning
    def _position_near(self, anchor_widget):
        """Appear just below the anchor widget, clamped to screen bounds."""
        self.update_idletasks()
        try:
            ax = anchor_widget.winfo_rootx()
            ay = anchor_widget.winfo_rooty() + anchor_widget.winfo_height()
        except Exception:
            ax, ay = 100, 100

        pw = self.winfo_reqwidth()
        ph = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()

        # Clamp so it never goes off-screen
        x = min(ax, sw - pw - 10)
        y = min(ay + 4, sh - ph - 10)
        self.geometry(f"{pw}x{ph}+{x}+{y}")


class CalendarPicker(ctk.CTkFrame):
    """
    Compound widget: text entry (YYYY-MM-DD) + 📅 calendar button.

    Usage — replace any ``ctk.CTkEntry`` used for a date with::

        self.date_picker = CalendarPicker(parent, textvariable=self.date_var,
                                          entry_width=160)
        self.date_picker.grid(...)   # or .pack(...)

    The underlying ``textvariable`` StringVar is updated both by manual
    typing and by selecting a day in the popup calendar.
    """

    def __init__(self, master, textvariable: ctk.StringVar,
                 entry_width: int = 150, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._var = textvariable

        self._entry = ctk.CTkEntry(
            self, textvariable=self._var,
            width=entry_width, placeholder_text="YYYY-MM-DD"
        )
        self._entry.pack(side="left")

        self._btn = ctk.CTkButton(
            self, text="📅", width=32, height=32,
            fg_color=("gray85", "gray28"),
            hover_color=("gray72", "gray38"),
            text_color=("black", "white"),
            command=self._open
        )
        self._btn.pack(side="left", padx=(4, 0))

    # ---------------------------------------------------------------- helpers
    def _open(self):
        CalendarPopup(self, self._var)

    def get(self) -> str:
        return self._var.get()

    def configure(self, **kwargs):
        state = kwargs.pop("state", None)
        if state is not None:
            self._entry.configure(state=state)
            self._btn.configure(state=state)
        super().configure(**kwargs)
