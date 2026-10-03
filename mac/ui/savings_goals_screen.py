"""
savings_goals_screen.py — Dedicated screen for named savings goals.
Allows users to create specific milestones (e.g. Vacation, Laptop, Car Down Payment),
track visual progress bars, and deposit/withdraw savings funds with live updates.
"""

from datetime import date
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from app import savings_goals as goals_api
from ui import theme
from ui.calendar_picker import CalendarPicker


class GoalFormDialog(ctk.CTkToplevel):
    """Modal dialog to create or edit a named savings goal."""

    def __init__(self, master, db_path, goal_id: int | None = None, on_saved=None):
        super().__init__(master)
        self.db_path = db_path
        self.goal_id = goal_id
        self.on_saved = on_saved

        self.title("New Savings Goal" if goal_id is None else "Edit Savings Goal")
        self.geometry("450x420")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self.existing_goal = goals_api.get_goal(goal_id, db_path=self.db_path) if goal_id else None
        self._build_ui()

    def _build_ui(self):
        pad_x = 24
        title_txt = "🎯 New Savings Goal" if not self.existing_goal else "✏️ Edit Savings Goal"
        ctk.CTkLabel(self, text=title_txt, font=theme.FONT_TITLE).pack(anchor="w", padx=pad_x, pady=(20, 6))

        # Goal Name
        ctk.CTkLabel(self, text="Goal Name:", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(10, 2))
        init_name = self.existing_goal["name"] if self.existing_goal else ""
        self.name_var = ctk.StringVar(value=init_name)
        self.name_entry = ctk.CTkEntry(self, textvariable=self.name_var, placeholder_text="e.g. Japan Vacation, MacBook M3", width=380)
        self.name_entry.pack(padx=pad_x, pady=(0, 10))

        # Target Amount
        ctk.CTkLabel(self, text="Target Amount (₹):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        init_target = f"{self.existing_goal['target_amount']:.2f}" if self.existing_goal else ""
        self.target_var = ctk.StringVar(value=init_target)
        self.target_entry = ctk.CTkEntry(self, textvariable=self.target_var, placeholder_text="e.g. 150000", width=380)
        self.target_entry.pack(padx=pad_x, pady=(0, 10))

        # Initial Saved (only for new goals)
        if not self.existing_goal:
            ctk.CTkLabel(self, text="Initial Saved Amount (₹, optional):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
            self.saved_var = ctk.StringVar(value="0")
            self.saved_entry = ctk.CTkEntry(self, textvariable=self.saved_var, placeholder_text="0.00", width=380)
            self.saved_entry.pack(padx=pad_x, pady=(0, 10))

        # Target Date
        ctk.CTkLabel(self, text="Target Date (optional):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        init_date = self.existing_goal.get("target_date") or "" if self.existing_goal else ""
        self.date_var = ctk.StringVar(value=init_date)
        self.date_entry = CalendarPicker(self, textvariable=self.date_var, entry_width=340)
        self.date_entry.pack(padx=pad_x, pady=(0, 14))

        self.error_lbl = ctk.CTkLabel(self, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.error_lbl.pack(padx=pad_x, pady=(0, 10))

        # Action buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad_x, pady=(4, 20))

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1,
            border_color=theme.COLOR_CARD_BORDER, command=self.destroy, width=100
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="Save Goal", fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER, command=self._save, width=130
        ).pack(side="right")

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            self.error_lbl.configure(text="Please enter a goal name.")
            return

        try:
            target = float(self.target_var.get().strip())
            if target <= 0:
                self.error_lbl.configure(text="Target amount must be greater than zero.")
                return
        except ValueError:
            self.error_lbl.configure(text="Please enter a valid target amount.")
            return

        date_val = self.date_var.get().strip() or None
        if date_val:
            try:
                date.fromisoformat(date_val)
            except ValueError:
                self.error_lbl.configure(text="Target date must be in YYYY-MM-DD format.")
                return

        try:
            if not self.existing_goal:
                try:
                    initial_saved = float(self.saved_var.get().strip() or "0")
                except ValueError:
                    initial_saved = 0.0
                goals_api.create_goal(
                    name=name,
                    target_amount=target,
                    target_date=date_val,
                    initial_saved=initial_saved,
                    db_path=self.db_path
                )
            else:
                goals_api.update_goal(
                    self.goal_id,
                    name=name,
                    target_amount=target,
                    target_date=date_val,
                    db_path=self.db_path
                )

            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.error_lbl.configure(text=str(e))


class GoalDepositWithdrawDialog(ctk.CTkToplevel):
    """Quick modal dialog to deposit or withdraw funds from a savings goal."""

    def __init__(self, master, goal: dict, db_path, on_saved=None):
        super().__init__(master)
        self.goal = goal
        self.db_path = db_path
        self.on_saved = on_saved

        self.title(f"Deposit / Withdraw — {goal['name']}")
        self.geometry("450x380")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        pad_x = 24
        ctk.CTkLabel(self, text=f"🎯 {self.goal['name']}", font=theme.FONT_TITLE).pack(anchor="w", padx=pad_x, pady=(18, 4))
        saved = self.goal['saved_amount']
        target = self.goal['target_amount']
        rem = self.goal['remaining']
        status_txt = f"Current Saved: ₹{saved:,.2f} of ₹{target:,.2f} ({self.goal['pct']}%)  |  Remaining: ₹{rem:,.2f}"
        ctk.CTkLabel(self, text=status_txt, font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED).pack(anchor="w", padx=pad_x, pady=(0, 14))

        # Operation type
        ctk.CTkLabel(self, text="Action:", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        self.action_var = ctk.StringVar(value="Deposit")
        self.action_menu = ctk.CTkSegmentedButton(
            self, values=["Deposit", "Withdraw"], variable=self.action_var,
            command=lambda _: self._update_preview()
        )
        self.action_menu.pack(fill="x", padx=pad_x, pady=(0, 10))

        # Amount
        ctk.CTkLabel(self, text="Amount (₹):", font=theme.FONT_BODY_BOLD).pack(anchor="w", padx=pad_x, pady=(4, 2))
        amt_frame = ctk.CTkFrame(self, fg_color="transparent")
        amt_frame.pack(fill="x", padx=pad_x, pady=(0, 6))

        self.amount_var = ctk.StringVar(value="")
        self.amount_var.trace_add("write", lambda *_: self._update_preview())
        self.amount_entry = ctk.CTkEntry(amt_frame, textvariable=self.amount_var, placeholder_text="0.00", width=160)
        self.amount_entry.pack(side="left", padx=(0, 8))

        # Quick preset buttons
        for val in [1000, 5000]:
            ctk.CTkButton(
                amt_frame, text=f"+₹{val}", width=60, height=28,
                fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_CARD_BORDER,
                text_color=("black", "white"),
                command=lambda v=val: self._add_quick_amount(v)
            ).pack(side="left", padx=2)

        ctk.CTkButton(
            amt_frame, text="Deposit Rem", width=90, height=28,
            fg_color=theme.COLOR_CARD_BG, hover_color=theme.COLOR_CARD_BORDER,
            text_color=("black", "white"),
            command=self._set_remaining
        ).pack(side="left", padx=2)

        # Preview card
        self.preview_lbl = ctk.CTkLabel(self, text="", font=theme.FONT_BODY, text_color=theme.COLOR_SUCCESS)
        self.preview_lbl.pack(anchor="w", padx=pad_x, pady=(8, 4))

        self.error_lbl = ctk.CTkLabel(self, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_DANGER)
        self.error_lbl.pack(padx=pad_x, pady=(0, 6))

        # Action row
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad_x, pady=(10, 15))

        ctk.CTkButton(
            btn_row, text="Cancel", fg_color="transparent", border_width=1,
            border_color=theme.COLOR_CARD_BORDER, command=self.destroy, width=100
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="Confirm", fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER, command=self._confirm, width=130
        ).pack(side="right")

        self._update_preview()

    def _add_quick_amount(self, delta):
        try:
            cur = float(self.amount_var.get() or "0")
        except ValueError:
            cur = 0.0
        self.amount_var.set(str(int(cur + delta)))

    def _set_remaining(self):
        self.action_var.set("Deposit")
        rem = self.goal["remaining"]
        self.amount_var.set(str(int(rem)))

    def _update_preview(self):
        self.error_lbl.configure(text="")
        amt_str = self.amount_var.get().strip()
        if not amt_str:
            self.preview_lbl.configure(text="")
            return
        try:
            amt = float(amt_str)
            if amt <= 0:
                self.preview_lbl.configure(text="")
                return
            is_dep = (self.action_var.get() == "Deposit")
            delta = amt if is_dep else -amt
            saved = self.goal["saved_amount"]
            target = self.goal["target_amount"]
            new_saved = saved + delta
            if new_saved < 0:
                self.preview_lbl.configure(text=f"⚠️ Cannot withdraw more than saved (₹{saved:,.2f})")
                return
            new_pct = min(100.0, round((new_saved / target) * 100, 1)) if target > 0 else 0.0
            act_word = "Depositing" if is_dep else "Withdrawing"
            self.preview_lbl.configure(
                text=f"{act_word} ₹{amt:,.2f} ➔ New Total: ₹{new_saved:,.2f} ({new_pct}%)"
            )
        except ValueError:
            self.preview_lbl.configure(text="")

    def _confirm(self):
        amt_str = self.amount_var.get().strip()
        try:
            amt = float(amt_str)
            if amt <= 0:
                self.error_lbl.configure(text="Amount must be greater than zero.")
                return
        except ValueError:
            self.error_lbl.configure(text="Please enter a valid number.")
            return

        is_dep = (self.action_var.get() == "Deposit")
        delta = amt if is_dep else -amt

        try:
            new_saved = goals_api.adjust_goal_saved(self.goal["id"], delta, db_path=self.db_path)
            act_text = "deposited to" if is_dep else "withdrawn from"
            messagebox.showinfo(
                "Goal Updated",
                f"Successfully {act_text} '{self.goal['name']}'!\nNew saved balance: ₹{new_saved:,.2f}"
            )
            self.destroy()
            if self.on_saved:
                self.on_saved()
        except Exception as e:
            self.error_lbl.configure(text=str(e))


class SavingsGoalsScreen(ctk.CTkFrame):
    """Main screen for managing and visualizing dedicated savings goals."""

    def __init__(self, master, db_path, on_change=None):
        super().__init__(master, fg_color="transparent")
        self.db_path = db_path
        self.on_change = on_change
        self.is_privacy_mode = False

        self._build_ui()
        self.refresh()

    def set_privacy_mode(self, enabled: bool):
        self.is_privacy_mode = enabled
        self.refresh()

    def _build_ui(self):
        # Header Row
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 10))

        title_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        title_frame.pack(side="left")
        ctk.CTkLabel(title_frame, text="🎯 Savings Goals", font=theme.FONT_TITLE).pack(anchor="w")
        ctk.CTkLabel(
            title_frame,
            text="Set aside funds for specific milestones and watch your progress grow.",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_MUTED
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            hdr, text="➕ New Goal", font=theme.FONT_BODY_BOLD,
            fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER,
            command=self._open_new_goal_dialog, width=130, height=36
        ).pack(side="right")

        # Top Summary Metric Cards
        self.metrics_container = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics_container.pack(fill="x", padx=24, pady=(0, 16))

        self.card_total_saved = self._create_card(self.metrics_container, "Total Saved in Goals", "₹0.00", theme.COLOR_SUCCESS)
        self.card_total_saved.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.card_total_target = self._create_card(self.metrics_container, "Combined Target", "₹0.00", theme.COLOR_PRIMARY)
        self.card_total_target.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.card_progress = self._create_card(self.metrics_container, "Overall Progress", "0.0%", "#8E44AD")
        self.card_progress.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.card_count = self._create_card(self.metrics_container, "Active Goals", "0", "#E8732C")
        self.card_count.pack(side="left", fill="both", expand=True)

        # Scrollable Goals List
        self.goals_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.goals_scroll.pack(fill="both", expand=True, padx=24, pady=(0, 20))

    def _create_card(self, master, title, value, accent_color):
        card = ctk.CTkFrame(
            master, fg_color=theme.COLOR_CARD_BG, border_color=theme.COLOR_CARD_BORDER,
            border_width=1, corner_radius=10
        )
        t_lbl = ctk.CTkLabel(card, text=title, font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED)
        t_lbl.pack(anchor="w", padx=16, pady=(12, 2))

        val_lbl = ctk.CTkLabel(card, text=value, font=theme.FONT_SUBTITLE, text_color=accent_color)
        val_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        card.val_lbl = val_lbl
        return card

    def refresh(self):
        summary = goals_api.goals_summary(db_path=self.db_path)
        if self.is_privacy_mode:
            self.card_total_saved.val_lbl.configure(text="₹ ••••••")
            self.card_total_target.val_lbl.configure(text="₹ ••••••")
        else:
            self.card_total_saved.val_lbl.configure(text=f"₹{summary['total_saved']:,.2f}")
            self.card_total_target.val_lbl.configure(text=f"₹{summary['total_target']:,.2f}")
        self.card_progress.val_lbl.configure(text=f"{summary['overall_pct']:.1f}%")
        self.card_count.val_lbl.configure(text=f"{summary['active_count']} active")

        # Clear goal widgets
        for w in self.goals_scroll.winfo_children():
            w.destroy()

        goals = summary.get("goals", [])
        if not goals:
            empty_frame = ctk.CTkFrame(self.goals_scroll, fg_color=theme.COLOR_CARD_BG, corner_radius=12)
            empty_frame.pack(fill="x", pady=40, padx=20)
            ctk.CTkLabel(
                empty_frame,
                text="🌟 No savings goals created yet.\nClick '+ New Goal' to start saving for your next dream milestone!",
                font=theme.FONT_BODY, justify="center", text_color=theme.COLOR_MUTED
            ).pack(pady=40)
            return

        for g in goals:
            self._render_goal_card(g)

    def _render_goal_card(self, g: dict):
        is_done = bool(g.get("is_completed"))
        card = ctk.CTkFrame(
            self.goals_scroll,
            fg_color=theme.COLOR_CARD_BG,
            border_color="#10B981" if is_done else theme.COLOR_CARD_BORDER,
            border_width=2 if is_done else 1,
            corner_radius=12
        )
        card.pack(fill="x", pady=6)

        # Header of card: Title & status badge
        hdr_row = ctk.CTkFrame(card, fg_color="transparent")
        hdr_row.pack(fill="x", padx=16, pady=(14, 4))

        ctk.CTkLabel(hdr_row, text=g["name"], font=theme.FONT_SUBTITLE).pack(side="left")

        if is_done:
            badge = ctk.CTkLabel(
                hdr_row, text="🎉 Completed!", font=theme.FONT_SMALL,
                fg_color="#10B981", text_color="white", corner_radius=6, padx=8, pady=2
            )
            badge.pack(side="right")
        else:
            pct_badge = ctk.CTkLabel(
                hdr_row, text=f"{g['pct']}%", font=theme.FONT_SMALL,
                fg_color=theme.COLOR_PRIMARY, text_color="white", corner_radius=6, padx=8, pady=2
            )
            pct_badge.pack(side="right")

        # Progress bar
        p_frame = ctk.CTkFrame(card, fg_color="transparent")
        p_frame.pack(fill="x", padx=16, pady=(4, 6))

        p_bar = ctk.CTkProgressBar(p_frame, height=10, corner_radius=5)
        p_bar.set(min(1.0, g["pct"] / 100.0))
        if is_done:
            p_bar.configure(progress_color="#10B981")
        p_bar.pack(fill="x")

        # Details Row: Saved / Target / Days Left
        det_row = ctk.CTkFrame(card, fg_color="transparent")
        det_row.pack(fill="x", padx=16, pady=(2, 8))

        saved_txt = "Saved: ₹ ••••••" if self.is_privacy_mode else f"Saved: ₹{g['saved_amount']:,.2f} / ₹{g['target_amount']:,.2f}"
        ctk.CTkLabel(det_row, text=saved_txt, font=theme.FONT_BODY_BOLD).pack(side="left")

        if g.get("target_date"):
            days = g.get("days_left")
            if is_done:
                time_txt = f"📅 Target was: {g['target_date']}"
                time_color = theme.COLOR_MUTED
            elif days is not None and days >= 0:
                time_txt = f"📅 Due: {g['target_date']} ({days} days left)"
                time_color = theme.COLOR_PRIMARY
            else:
                time_txt = f"⚠️ Overdue ({abs(days or 0)} days past {g['target_date']})"
                time_color = theme.COLOR_DANGER
            ctk.CTkLabel(det_row, text=time_txt, font=theme.FONT_SMALL, text_color=time_color).pack(side="right")
        elif not is_done:
            rem_txt = f"Remaining: ₹{g['remaining']:,.2f}"
            ctk.CTkLabel(det_row, text=rem_txt, font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED).pack(side="right")

        # Action Buttons
        act_row = ctk.CTkFrame(card, fg_color="transparent")
        act_row.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkButton(
            act_row, text="💵 Deposit / Withdraw", font=theme.FONT_SMALL, width=150, height=28,
            fg_color=theme.COLOR_PRIMARY, hover_color=theme.COLOR_PRIMARY_HOVER,
            command=lambda goal=g: self._open_deposit_withdraw(goal)
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            act_row, text="✏️ Edit", font=theme.FONT_SMALL, width=80, height=28,
            fg_color="transparent", border_width=1, border_color=theme.COLOR_CARD_BORDER,
            command=lambda gid=g["id"]: self._open_edit_dialog(gid)
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            act_row, text="🗑️ Delete", font=theme.FONT_SMALL, width=80, height=28,
            fg_color="transparent", border_width=1, border_color=theme.COLOR_DANGER,
            text_color=theme.COLOR_DANGER, command=lambda gid=g["id"], gn=g["name"]: self._delete_goal(gid, gn)
        ).pack(side="right")

    def _open_new_goal_dialog(self):
        GoalFormDialog(self.winfo_toplevel(), db_path=self.db_path, on_saved=self._on_goal_changed)

    def _open_edit_dialog(self, goal_id: int):
        GoalFormDialog(self.winfo_toplevel(), db_path=self.db_path, goal_id=goal_id, on_saved=self._on_goal_changed)

    def _open_deposit_withdraw(self, goal: dict):
        GoalDepositWithdrawDialog(self.winfo_toplevel(), goal=goal, db_path=self.db_path, on_saved=self._on_goal_changed)

    def _delete_goal(self, goal_id: int, goal_name: str):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete savings goal '{goal_name}'?"):
            goals_api.delete_goal(goal_id, db_path=self.db_path)
            self._on_goal_changed()

    def _on_goal_changed(self):
        self.refresh()
        if self.on_change:
            self.on_change()
