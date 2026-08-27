"""
ai_context.py — Builds a live database context snapshot for the AI chatbot.

Every Gemini request gets a fresh snapshot of the current state of the user's
budget, injected as context so the model can answer questions accurately.
"""

from datetime import date
from .budget_logic import dashboard_summary
from .categories import list_categories
from .transactions import list_transactions
from .emergency_fund import get_balance as ef_balance


def build_live_context(db_path=None) -> str:
    """
    Returns a compact, human-readable text block describing the current state
    of the user's budget. Injected into every Gemini request as live context.
    """
    month = date.today().isoformat()[:7]
    lines = []

    # -- Month summary --
    try:
        summary = dashboard_summary(month, db_path)
        lines.append(f"=== LIVE BUDGET DATA (as of {date.today().isoformat()}) ===")
        lines.append(f"Current month: {month}")
        lines.append(f"Total income this month:        ${summary['total_income']:,.2f}")
        lines.append(f"Total spent this month:         ${summary['total_spent']:,.2f}")
        lines.append(f"Available to spend:             ${summary['available_to_spend']:,.2f}")
        lines.append(f"Savings balance:                ${summary['savings_balance']:,.2f}")
        lines.append(f"Emergency fund balance:         ${summary['emergency_fund_balance']:,.2f}")
        lines.append(f"Pending approval transactions:  {len(summary.get('pending_approvals', []))}")
    except Exception as e:
        lines.append(f"[Could not load summary: {e}]")
        summary = {}

    # -- Category breakdown --
    lines.append("\n--- CATEGORY BREAKDOWN ---")
    try:
        cats = list_categories(db_path)
        expense_cats = [c for c in cats if c["soft_limit"] > 0 or c["hard_limit"] > 0]
        if expense_cats:
            for cat in expense_cats:
                cat_id = cat["id"]
                cat_data = next(
                    (c for c in summary.get("categories", []) if c["id"] == cat_id),
                    None
                )
                spent = cat_data["spent"] if cat_data else 0.0
                soft = cat["soft_limit"]
                hard = cat["hard_limit"]
                pct = (spent / hard * 100) if hard > 0 else 0
                status = "OK"
                if spent >= hard:
                    status = "OVER HARD LIMIT"
                elif spent >= soft:
                    status = "OVER SOFT LIMIT"
                lines.append(
                    f"  {cat['name']}: spent ${spent:,.2f} / hard limit ${hard:,.2f} "
                    f"({pct:.0f}%) — {status}"
                )
        else:
            lines.append("  No expense categories configured.")

        income_cats = [c for c in cats if c["soft_limit"] == 0 and c["hard_limit"] == 0]
        if income_cats:
            lines.append("  Income categories: " + ", ".join(c["name"] for c in income_cats))
    except Exception as e:
        lines.append(f"[Could not load categories: {e}]")

    # -- Last 30 transactions --
    lines.append("\n--- RECENT TRANSACTIONS (last 30) ---")
    try:
        txns = list_transactions(db_path=db_path)
        txns_sorted = sorted(txns, key=lambda t: t["date"], reverse=True)[:30]
        cats_map = {c["id"]: c["name"] for c in list_categories(db_path)}

        if txns_sorted:
            for t in txns_sorted:
                cat_name = cats_map.get(t["category_id"], "General Income" if t["type"] == "income" else "—")
                sign = "+" if t["type"] == "income" else "-"
                desc = t["description"] or "(no description)"
                lines.append(
                    f"  {t['date']} | {t['type'].upper():7s} | {cat_name:20s} | "
                    f"{sign}${t['amount']:,.2f} | {desc}"
                )
        else:
            lines.append("  No transactions recorded yet.")
    except Exception as e:
        lines.append(f"[Could not load transactions: {e}]")

    lines.append("\n=== END OF LIVE DATA ===")
    return "\n".join(lines)


def build_system_prompt(db_path=None) -> str:
    """
    Returns the full system prompt: static app knowledge + live DB context.
    """
    static = """You are BudgetBot, an AI financial assistant built into BudgetApp — a personal budget tracking desktop application for macOS.

YOUR ROLE:
- Help the user understand their spending, savings, and budget health.
- Answer questions about the app's features and how to use them.
- Give practical, concise financial insights based on the live data provided.
- Be friendly, direct, and focused. Never guess at numbers — always use the live data provided.

APP FEATURE KNOWLEDGE:

1. DASHBOARD
   - Shows 5 summary cards: Available to Spend, Total Income, Total Spent (row 1); Savings Balance, Emergency Fund (row 2).
   - "Available to Spend" = General Income + Category Inflows − Total Expenses − Manual EF Deposits for this month.
   - Shows a spending pace chart (actual vs projected) and a category limits & progress section.

2. ADD TRANSACTION
   - Transaction types: Expense or Income.
   - For EXPENSES: must select an expense category (categories with spending limits > 0).
   - For INCOME: select "General Income" for regular salary/rent, OR select a zero-limit income category (e.g. Gifts, Parents) for supplemental money.
   - Funding source for expenses: Regular, Savings, or Emergency Fund.
   - Date, amount, and optional description are required.

3. TRANSACTIONS LIST
   - Shows all transactions with filters for category, type, and status.
   - Sortable by date, category, amount, etc.
   - Can delete individual transactions.

4. SETTINGS
   - Categories: Create, rename, or delete spending categories. Set soft and hard limits per category.
     - EXPENSE categories: set limits > 0 (e.g. soft=$800, hard=$1000 for Food).
     - INCOME categories: set both limits to 0 (e.g. Gifts, Parents, Side Hustle).
   - Thresholds: Set per-category warning thresholds.
   - Emergency Fund: Set EF target amount and monthly contribution (fixed $ or %).
   - Rollover: Trigger manual month-end rollover; leftover money goes to savings and/or EF.
   - AI Assistant: Set your Gemini API key and preferred model.

5. EMERGENCY FUND (EF)
   - Separate from Savings. Has its own target amount.
   - Manual deposits reduce "Available to Spend" for the month.
   - At month-end rollover, remaining leftover can auto-contribute to EF until the target is hit.

6. MONTH-END ROLLOVER
   - At month end, leftover = total limits − total spent.
   - Leftover is split between EF (until target is reached) and Savings.
   - Can be triggered manually from Settings → Rollover section.

CONVERSATION STYLE:
- Keep answers short and actionable.
- When referencing numbers, always cite the live data.
- If the user asks something outside personal finance or this app, politely redirect.

"""
    live_ctx = build_live_context(db_path)
    return static + "\n" + live_ctx
