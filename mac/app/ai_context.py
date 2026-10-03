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
from .settings import get_setting
from .savings_goals import goals_summary


def build_live_context(db_path=None) -> str:
    """
    Returns a compact, human-readable text block describing the current state
    of the user's budget. Injected into every Gemini request as live context.
    """
    month = date.today().isoformat()[:7]
    currency = get_setting("currency_symbol", db_path) or "₹"
    lines = []

    # -- Month summary --
    try:
        summary = dashboard_summary(month, db_path)
        lines.append(f"=== LIVE BUDGET DATA (as of {date.today().isoformat()}) ===")
        lines.append(f"Current month: {month}")
        lines.append(f"Currency: {currency}")
        lines.append(f"Total income this month:        {currency}{summary['total_income']:,.2f}")
        lines.append(f"Total spent this month:         {currency}{summary['total_spent']:,.2f}")
        lines.append(f"Available to spend:             {currency}{summary['available_to_spend']:,.2f}")
        lines.append(f"Savings balance:                {currency}{summary['savings_balance']:,.2f}")
        lines.append(f"Emergency fund balance:         {currency}{summary['emergency_fund_balance']:,.2f}")
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
                    (c for c in summary.get("categories", []) if c.get("category_id") == cat_id or c.get("id") == cat_id),
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
                    f"  {cat['name']}: spent {currency}{spent:,.2f} / hard limit {currency}{hard:,.2f} "
                    f"({pct:.0f}%) — {status}"
                )
        else:
            lines.append("  No expense categories configured.")

        income_cats = [c for c in cats if c["soft_limit"] == 0 and c["hard_limit"] == 0]
        if income_cats:
            lines.append("  Income categories: " + ", ".join(c["name"] for c in income_cats))
    except Exception as e:
        lines.append(f"[Could not load categories: {e}]")

    # -- Dedicated Savings Goals --
    lines.append("\n--- DEDICATED SAVINGS GOALS ---")
    try:
        g_sum = goals_summary(db_path=db_path)
        goals = g_sum.get("goals", [])
        if goals:
            lines.append(f"  Combined Goals: saved {currency}{g_sum['total_saved']:,.2f} of {currency}{g_sum['total_target']:,.2f} ({g_sum['overall_pct']}%)")
            for g in goals:
                st = "COMPLETED" if g["is_completed"] else f"{g['pct']}%"
                dt_txt = f", due: {g['target_date']}" if g.get("target_date") else ""
                lines.append(f"  • {g['name']}: {currency}{g['saved_amount']:,.2f} / {currency}{g['target_amount']:,.2f} ({st}{dt_txt})")
        else:
            lines.append("  No active savings goals.")
    except Exception as e:
        lines.append(f"[Could not load savings goals: {e}]")

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
                    f"{sign}{currency}{t['amount']:,.2f} | {desc}"
                )
        else:
            lines.append("  No transactions recorded yet.")
    except Exception as e:
        lines.append(f"[Could not load transactions: {e}]")

    lines.append("\n=== END OF LIVE DATA ===")
    return "\n".join(lines)


def build_system_prompt(db_path=None) -> str:
    """
    Returns the full system prompt: static app knowledge + live DB context + transaction quick-add instructions.
    """
    static = """You are BudgetBot, an AI financial assistant built into BudgetApp — a personal budget tracking desktop application.

YOUR ROLE:
- Help the user understand their spending, savings, and budget health.
- Deliver executive-grade financial health audits and actionable recommendations when requested.
- Answer questions about the app's features and how to use them.
- Give practical, concise financial insights based on the live data provided.
- Be friendly, direct, and focused. Never guess at numbers — always use the live data provided.

SPECIAL CAPABILITY: NATURAL LANGUAGE TRANSACTION RECORDING
When the user indicates they want to add or log a transaction (e.g. "I bought groceries for 450", "Add salary 50000", "Spent 120 on coffee"),
provide a friendly acknowledgement, and at the end of your response, ALWAYS append a JSON block formatted exactly like this:
```json
{
  "action": "add_transaction",
  "amount": <number>,
  "type": "expense" or "income",
  "category": "<matching category name from the live category list>",
  "date": "YYYY-MM-DD",
  "description": "<clean short description>"
}
```
The desktop app automatically parses this JSON and presents an interactive 1-click button for the user to confirm the transaction into their budget.

SPECIAL CAPABILITY: FINANCIAL HEALTH AUDIT
When the user asks for a financial health audit or report:
1. Assign an overall Health Grade (A/B/C/D/F).
2. Detail Budget & Runway Health (Income vs Spent pace, emergency fund coverage in months).
3. Detail Category Warnings (flagging categories approaching or over limit).
4. Detail Savings Goals Progress.
5. Provide Top 3 Actionable Steps to optimize their money this month.
Format using clean markdown with clear headers, bullet points, and emojis.
"""
    live_ctx = build_live_context(db_path)
    return static + "\n" + live_ctx

