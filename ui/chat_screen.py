"""
chat_screen.py — AI Assistant chat screen for BudgetApp.

A full-screen conversational chat interface powered by Gemini.
Live budget data is injected into each conversation as context.
"""

import tkinter as tk
import customtkinter as ctk
from datetime import datetime

from ui import theme
from app.ai_chat import GeminiChat, has_api_key, load_model, AVAILABLE_MODELS
from app.ai_context import build_system_prompt


class ChatScreen(ctk.CTkFrame):
    def __init__(self, parent, db_path, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.db_path = db_path
        self._chat = GeminiChat(db_path=db_path)
        self._thinking = False

        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="🤖 AI Assistant", font=theme.FONT_TITLE).grid(
            row=0, column=0, sticky="w"
        )

        self._model_label = ctk.CTkLabel(
            header, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED
        )
        self._model_label.grid(row=0, column=1, sticky="w", padx=16)

        self._clear_btn = ctk.CTkButton(
            header,
            text="Clear Chat",
            width=100,
            height=30,
            fg_color="transparent",
            border_color=theme.COLOR_MUTED,
            border_width=1,
            text_color=("black", "white"),
            font=theme.FONT_SMALL,
            command=self._clear_chat,
        )
        self._clear_btn.grid(row=0, column=2, sticky="e")

        # Chat bubble area (scrollable)
        self._bubble_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.COLOR_CARD_BG,
            border_color=theme.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12,
        )
        self._bubble_frame.grid(row=1, column=0, sticky="nsew", padx=24, pady=12)
        self._bubble_frame.grid_columnconfigure(0, weight=1)

        # Thinking indicator (hidden initially)
        self._thinking_label = ctk.CTkLabel(
            self._bubble_frame,
            text="",
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_MUTED,
            anchor="w",
        )

        # Input bar at the bottom
        input_bar = ctk.CTkFrame(self, fg_color="transparent")
        input_bar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 16))
        input_bar.grid_columnconfigure(0, weight=1)

        self._input_var = tk.StringVar()
        self._input_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask anything about your budget…",
            textvariable=self._input_var,
            height=42,
            font=theme.FONT_BODY,
            corner_radius=10,
        )
        self._input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self._input_entry.bind("<Return>", lambda e: self._send())

        self._send_btn = ctk.CTkButton(
            input_bar,
            text="Send ➤",
            width=90,
            height=42,
            fg_color=theme.COLOR_PRIMARY,
            hover_color=theme.COLOR_PRIMARY_HOVER,
            font=theme.FONT_BODY_BOLD,
            corner_radius=10,
            command=self._send,
        )
        self._send_btn.grid(row=0, column=1)

        # Status bar
        self._status_label = ctk.CTkLabel(
            self, text="", font=theme.FONT_SMALL, text_color=theme.COLOR_MUTED
        )
        self._status_label.grid(row=3, column=0, sticky="w", padx=24, pady=(0, 8))

        # Show welcome message on first load
        self._show_welcome()

    # ── Welcome ───────────────────────────────────────────────────────────────

    def _show_welcome(self):
        self._add_bubble(
            "model",
            "Hi! I'm BudgetBot. I have access to your live budget data and know how the app works.\n\n"
            "Try asking:\n"
            '  - "How much have I spent this month?"\n'
            '  - "Am I close to any spending limits?"\n'
            '  - "How do I set up an emergency fund?"\n'
            '  - "Where did most of my money go this month?"',
        )

    # ── Bubble rendering ──────────────────────────────────────────────────────

    def _add_bubble(self, role: str, text: str):
        """Adds a styled chat bubble for 'user' or 'model' role."""
        is_user = role == "user"

        outer = ctk.CTkFrame(self._bubble_frame, fg_color="transparent")
        outer.pack(fill="x", padx=8, pady=4)

        bubble_color = theme.COLOR_PRIMARY if is_user else ("white", "#2D2D2D")
        text_color   = "white" if is_user else ("black", "white")
        anchor       = "e" if is_user else "w"
        side         = "right" if is_user else "left"

        # Sender label
        sender_text = "You" if is_user else "BudgetBot"
        ctk.CTkLabel(
            outer,
            text=sender_text,
            font=theme.FONT_SMALL,
            text_color=theme.COLOR_MUTED,
            anchor=anchor,
        ).pack(fill="x", padx=4)

        # Bubble Container
        bubble_frame = ctk.CTkFrame(
            outer,
            fg_color=bubble_color,
            corner_radius=12
        )
        bubble_frame.pack(anchor=anchor, padx=4)

        # Resolve hex colors for standard Tkinter Text widget based on system mode
        mode = ctk.get_appearance_mode()
        idx = 0 if mode == "Light" else 1
        bubble_color_hex = bubble_color[idx] if isinstance(bubble_color, tuple) else bubble_color
        text_color_hex = text_color[idx] if isinstance(text_color, tuple) else text_color

        # Heuristic to calculate text box height (avoid scrollbar inside bubble)
        lines_list = text.split("\n")
        est_lines = 0
        for l in lines_list:
            est_lines += max(1, (len(l) + 74) // 75)

        text_widget = tk.Text(
            bubble_frame,
            font=theme.FONT_BODY,
            bg=bubble_color_hex,
            fg=text_color_hex,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            cursor="arrow",
            height=est_lines,
            width=75
        )
        text_widget.pack(padx=14, pady=10, fill="both", expand=True)

        text_widget.tag_configure("bold", font=theme.FONT_BODY_BOLD)

        # Parse markdown bold pattern
        parts = text.split("**")
        is_bold = False
        for part in parts:
            if is_bold:
                text_widget.insert("end", part, "bold")
            else:
                text_widget.insert("end", part)
            is_bold = not is_bold

        text_widget.configure(state="disabled")


        # Scroll to bottom after render
        self.after(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        try:
            self._bubble_frame._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    # ── Thinking indicator ────────────────────────────────────────────────────

    def _show_thinking(self):
        self._thinking_label.configure(text="⏳ BudgetBot is thinking…")
        self._thinking_label.pack(anchor="w", padx=8, pady=4)
        self._scroll_to_bottom()

    def _hide_thinking(self):
        self._thinking_label.pack_forget()
        self._thinking_label.configure(text="")

    # ── Send logic ────────────────────────────────────────────────────────────

    def _send(self):
        if self._thinking:
            return

        text = self._input_var.get().strip()
        if not text:
            return

        if not has_api_key(self.db_path):
            self._add_bubble(
                "model",
                "⚠️ No API key found. Please go to **Settings → AI Assistant** and enter your Gemini API key.",
            )
            return

        # Show user bubble and clear input
        self._add_bubble("user", text)
        self._input_var.set("")
        self._input_entry.configure(state="disabled")
        self._send_btn.configure(state="disabled")
        self._thinking = True
        self._show_thinking()

        # Build fresh system prompt with live DB context
        system_prompt = build_system_prompt(self.db_path)

        # Send in background thread
        self._chat.send(
            user_message=text,
            system_prompt=system_prompt,
            on_done=self._on_response,
            on_error=self._on_error,
        )

    def _on_response(self, reply: str):
        """Called from background thread — must schedule UI update on main thread."""
        self.after(0, lambda: self._display_response(reply))

    def _on_error(self, error_msg: str):
        self.after(0, lambda: self._display_error(error_msg))

    def _display_response(self, reply: str):
        self._hide_thinking()
        self._add_bubble("model", reply)
        self._input_entry.configure(state="normal")
        self._send_btn.configure(state="normal")
        self._thinking = False
        model = load_model(self.db_path)
        self._status_label.configure(
            text=f"Model: {model}  •  Turns: {self._chat.turn_count}"
        )

    def _display_error(self, error_msg: str):
        self._hide_thinking()
        self._add_bubble("model", f"❌ Error: {error_msg}")
        self._input_entry.configure(state="normal")
        self._send_btn.configure(state="normal")
        self._thinking = False

    # ── Clear chat ────────────────────────────────────────────────────────────

    def _clear_chat(self):
        self._chat.clear_history()
        # Remove all bubble widgets
        for widget in self._bubble_frame.winfo_children():
            if widget is not self._thinking_label:
                widget.destroy()
        self._status_label.configure(text="")
        self._show_welcome()

    # ── Refresh (called when screen becomes visible) ──────────────────────────

    def refresh(self):
        model = load_model(self.db_path)
        self._model_label.configure(text=f"Model: {model}")
        if not has_api_key(self.db_path):
            self._status_label.configure(
                text="⚠️  No API key set — go to Settings → AI Assistant",
                text_color=theme.COLOR_WARNING,
            )
        else:
            self._status_label.configure(
                text=f"Model: {model}  •  Turns: {self._chat.turn_count}",
                text_color=theme.COLOR_MUTED,
            )
