"""
theme.py — Font and color definitions for the budget app.
Supports light and dark modes via CustomTkinter color tuples (Light, Dark).
"""

FONT_TITLE = ("Helvetica", 22, "bold")
FONT_SUBTITLE = ("Helvetica", 16, "bold")
FONT_BODY = ("Helvetica", 13)
FONT_BODY_BOLD = ("Helvetica", 13, "bold")
FONT_SMALL = ("Helvetica", 11)

# Color configurations (Light Mode, Dark Mode)
COLOR_PRIMARY = ("#1A73E8", "#2E86AB")
COLOR_PRIMARY_HOVER = ("#1557B0", "#246B8A")
COLOR_MUTED = ("#666666", "#AAAAAA")
COLOR_DANGER = ("#C9302C", "#D9534F")
COLOR_SUCCESS = ("#449D44", "#5CB85C")
COLOR_WARNING = ("#EC971F", "#F0AD4E")

# Proximity warning background & borders (Light, Dark)
COLOR_BANNER_BG = ("#FFF3CD", "#2C2515")
COLOR_BANNER_BORDER = ("#FFEBAA", "#4A3E20")
COLOR_BANNER_TEXT = ("#856404", "#FFEBAA")

COLOR_CARD_BG = ("#F8F9FA", "#252525")
COLOR_CARD_BORDER = ("#E9ECEF", "#333333")
