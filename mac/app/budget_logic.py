"""
budget_logic.py — the rules that don't belong to any single table:
month-end rollover + emergency-fund split (Section 6.2 / 6.4), and the
dashboard summary + month-end spending projection (Section 7.1).

This module is the only place the UI needs to call for anything
cross-cutting — it never touches SQL directly, matching the
architecture note in spec Section 4.
"""

import calendar
from datetime import date, datetime, timezone
from .db import get_connection
from .categories import list_categories
from .transactions import category_spent_this_month, list_transactions
from .settings import get_setting_float, get_setting
from .emergency_fund import get_balance as ef_balance, _adjust_balance as ef_adjust


def compute_month_leftover(month: str = None, db_path=None) -> dict:
    """Per-category leftover = max(hard_limit - spent, 0), per spec
    Section 6.2. Overspent categories contribute zero, never negative."""
    if month is None:
        month = date.today().isoformat()[:7]

    per_category = []
    total_leftover = 0.0
    for cat in list_categories(db_path):
        spent = category_spent_this_month(cat["id"], month, db_path)
        leftover = max(cat["hard_limit"] - spent, 0.0)
        per_category.append({
            "category_id": cat["id"],
            "name": cat["name"],
            "spent": spent,
            "hard_limit": cat["hard_limit"],
            "leftover": leftover,
        })
        total_leftover += leftover

    return {"month": month, "per_category": per_category, "total_leftover": total_leftover}


def split_leftover_for_emergency_fund(total_leftover: float, db_path=None) -> dict:
    """Implements Figure 4: if the EF balance is below its target, route
    the configured monthly contribution (fixed $ or %) to the EF first,
    capped so it never pushes the balance past the target; the remainder
    rolls into ordinary savings. Once at/above target, 100% -> savings."""
    target = get_setting_float("ef_target_amount", db_path)
    contribution_type = get_setting("ef_monthly_contribution_type", db_path)
    contribution_value = get_setting_float("ef_monthly_contribution", db_path)
    current_balance = ef_balance(db_path)

    if current_balance >= target:
        return {"to_emergency_fund": 0.0, "to_savings": total_leftover}

    if contribution_type == "percent":
        desired = total_leftover * (contribution_value / 100.0)
    else:
        desired = contribution_value

    room_left = target - current_balance
    to_ef = max(0.0, min(desired, total_leftover, room_left))
    to_savings = total_leftover - to_ef

    return {"to_emergency_fund": to_ef, "to_savings": to_savings}


def run_month_end_rollover(month: str, db_path=None) -> dict:
    """Closes out `month` ('YYYY-MM'): computes leftover, splits it
    between Emergency Fund and Savings, writes one `savings` row, and
    logs the EF deposit (if any) through emergency_fund.py so it shows
    up in the same audited log as manual transfers.

    Idempotent: re-running for a month that's already closed raises,
    rather than silently double-crediting savings.
    """
    conn = get_connection(db_path)
    try:
        existing = conn.execute("SELECT id FROM savings WHERE month = ?", (month,)).fetchone()
        if existing is not None:
            raise ValueError(f"Month {month} has already been closed out.")

        leftover_info = compute_month_leftover(month, db_path)
        total_leftover = leftover_info["total_leftover"]
        split = split_leftover_for_emergency_fund(total_leftover, db_path)

        if split["to_emergency_fund"] > 0:
            ef_adjust(
                conn, split["to_emergency_fund"], source="monthly_rollover",
                note=f"Automatic contribution for {month}", log_date=date.today().isoformat(),
            )

        conn.execute(
            "INSERT INTO savings (month, rollover_amount, emergency_fund_delta) VALUES (?, ?, ?)",
            (month, split["to_savings"], split["to_emergency_fund"]),
        )
        conn.commit()

        return {
            "month": month,
            "total_leftover": total_leftover,
            "to_savings": split["to_savings"],
            "to_emergency_fund": split["to_emergency_fund"],
            "per_category": leftover_info["per_category"],
        }
    finally:
        conn.close()


def total_savings_balance(db_path=None) -> float:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(rollover_amount), 0) AS total FROM savings"
        ).fetchone()
        return row["total"]
    finally:
        conn.close()


def adjust_savings_balance(amount: float, note: str = "", db_path=None) -> None:
    """
    Manually adjust the savings balance by `amount` (positive = deposit, negative = withdrawal).
    Records the adjustment as a separate row in the savings table for the current month.
    Used to correct savings stuck from a reversed rollover.
    """
    if amount == 0:
        raise ValueError("Amount must be non-zero.")
    month = date.today().isoformat()[:7]
    conn = get_connection(db_path)
    try:
        existing = conn.execute(
            "SELECT id FROM savings WHERE month = ?", (month,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE savings SET rollover_amount = rollover_amount + ? WHERE month = ?",
                (amount, month),
            )
        else:
            conn.execute(
                "INSERT INTO savings (month, rollover_amount, emergency_fund_delta) VALUES (?, ?, 0)",
                (month, amount),
            )
        conn.commit()
    finally:
        conn.close()



def month_end_projection(month: str = None, db_path=None) -> dict:
    """Section 7.1's dashed projection line: extrapolate cumulative
    confirmed-expense spending so far this month, at the average daily
    rate observed so far, out to the last day of the month."""
    if month is None:
        month = date.today().isoformat()[:7]

    year, mon = int(month[:4]), int(month[5:7])
    days_in_month = calendar.monthrange(year, mon)[1]

    txns = list_transactions(
        start_date=f"{month}-01", end_date=f"{month}-{days_in_month:02d}",
        status="confirmed", txn_type="expense", db_path=db_path,
    )

    daily_totals = {}
    for t in txns:
        day = int(t["date"][8:10])
        daily_totals[day] = daily_totals.get(day, 0.0) + t["amount"]

    today = date.today()
    current_day = today.day if today.isoformat()[:7] == month else days_in_month

    cumulative = []
    running = 0.0
    for d in range(1, current_day + 1):
        day_amt = daily_totals.get(d, 0.0)
        running += day_amt
        cumulative.append({
            "day": d,
            "date": f"{year:04d}-{mon:02d}-{d:02d}",
            "daily_spent": day_amt,
            "cumulative_spent": running,
        })

    actual_total_so_far = running
    avg_daily_rate = actual_total_so_far / current_day if current_day > 0 else 0.0

    projection = []
    for d in range(current_day, days_in_month + 1):
        projected_value = actual_total_so_far + avg_daily_rate * (d - current_day)
        projection.append({
            "day": d,
            "date": f"{year:04d}-{mon:02d}-{d:02d}",
            "projected_cumulative": projected_value,
        })

    return {
        "month": month,
        "days_in_month": days_in_month,
        "current_day": current_day,
        "actual": cumulative,
        "projection": projection,
        "projected_month_end_total": projection[-1]["projected_cumulative"] if projection else actual_total_so_far,
    }


def dashboard_summary(month: str = None, db_path=None) -> dict:
    """Everything the Home dashboard (Section 7.1) needs in one call:
    per-category status, totals, savings/EF balances, and the projection."""
    from .transactions import category_status

    if month is None:
        month = date.today().isoformat()[:7]

    all_categories = [category_status(c["id"], month, db_path) for c in list_categories(db_path)]
    # Filter out categories that have zero limits and no spending (income-only or inactive categories)
    categories = [
        cat for cat in all_categories
        if cat["soft_limit"] > 0 or cat["hard_limit"] > 0 or cat["spent"] > 0
    ]


    income_rows = list_transactions(
        start_date=f"{month}-01", end_date=f"{month}-31",
        status="confirmed", txn_type="income", db_path=db_path,
    )
    expense_rows = list_transactions(
        start_date=f"{month}-01", end_date=f"{month}-31",
        status="confirmed", txn_type="expense", db_path=db_path,
    )

    # General income vs category-specific supplements
    general_income = sum(t["amount"] for t in income_rows if t.get("category_id") is None)
    category_inflows = sum(t["amount"] for t in income_rows if t.get("category_id") is not None)
    category_expenses = sum(t["amount"] for t in expense_rows)

    # Fetch net manual Emergency Fund changes this month
    from .db import get_connection
    conn = get_connection(db_path)
    try:
        ef_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM emergency_fund_log WHERE source = 'manual' AND date LIKE ?",
            (f"{month}%",)
        ).fetchone()
        ef_manual_net = ef_row["total"]
    finally:
        conn.close()

    # Available to Spend: Cash inflows minus expenses minus manual EF transfers
    available_to_spend = general_income + category_inflows - category_expenses - ef_manual_net

    # Check if this month is already closed in savings table
    conn = get_connection(db_path)
    try:
        savings_row = conn.execute(
            "SELECT rollover_amount, emergency_fund_delta FROM savings WHERE month = ?", (month,)
        ).fetchone()
        is_closed = savings_row is not None
        month_rollover = savings_row["rollover_amount"] if is_closed else 0.0
        month_ef_delta = savings_row["emergency_fund_delta"] if is_closed else 0.0
    finally:
        conn.close()

    pending = list_transactions(status="pending_approval", db_path=db_path)

    return {
        "month": month,
        "categories": categories,
        "total_income": general_income,
        "total_spent": sum(c["spent"] for c in categories),
        "available_to_spend": available_to_spend,
        "savings_balance": total_savings_balance(db_path),
        "emergency_fund_balance": ef_balance(db_path),
        "pending_approvals": pending,
        "projection": month_end_projection(month, db_path),
        "is_closed": is_closed,
        "month_rollover": month_rollover,
        "month_ef_delta": month_ef_delta,
    }


def get_available_months(db_path=None) -> list[str]:
    """Returns a sorted list (newest first) of all distinct 'YYYY-MM' months
    present in transactions or closed in savings, always including the current month."""
    from datetime import date
    current_month = date.today().isoformat()[:7]
    conn = get_connection(db_path)
    try:
        months_set = {current_month}
        for r in conn.execute("SELECT DISTINCT SUBSTR(date, 1, 7) AS m FROM transactions WHERE date IS NOT NULL"):
            if r["m"] and len(r["m"]) == 7:
                months_set.add(r["m"])
        for r in conn.execute("SELECT DISTINCT month AS m FROM savings WHERE month IS NOT NULL"):
            if r["m"] and len(r["m"]) == 7:
                months_set.add(r["m"])
        return sorted(list(months_set), reverse=True)
    finally:
        conn.close()


def get_closed_months_ledger(db_path=None) -> list[dict]:
    """Returns historical archive records for all months closed out in the savings table."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT month, rollover_amount, emergency_fund_delta FROM savings ORDER BY month DESC"
        ).fetchall()
        ledger = []
        for r in rows:
            m = r["month"]
            inc_row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type = 'income' AND status = 'confirmed' AND date LIKE ?",
                (f"{m}%",)
            ).fetchone()
            exp_row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE type = 'expense' AND status = 'confirmed' AND date LIKE ?",
                (f"{m}%",)
            ).fetchone()
            ledger.append({
                "month": m,
                "total_income": inc_row["total"],
                "total_spent": exp_row["total"],
                "rollover_savings": r["rollover_amount"],
                "rollover_ef": r["emergency_fund_delta"],
                "total_saved": r["rollover_amount"] + r["emergency_fund_delta"],
            })
        return ledger
    finally:
        conn.close()


def get_historical_trend(category_id: int = None, months_count: int = 6, db_path=None) -> list[dict]:
    """
    Returns the historical spending and rollover data for the last months_count months,
    ordered from oldest to newest.
    
    If category_id is specified, returns only the spending for that category (rollover is 0.0).
    """
    from datetime import date
    
    current_date = date.today()
    months = []
    y, m = current_date.year, current_date.month
    for _ in range(months_count):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()
    
    conn = get_connection(db_path)
    try:
        results = []
        for month in months:
            if category_id is None:
                # Sum of all expenses in that month
                spent_row = conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total 
                    FROM transactions 
                    WHERE type = 'expense' AND status = 'confirmed' 
                      AND date LIKE ?
                    """,
                    (f"{month}%",)
                ).fetchone()
                spent = spent_row["total"]
                
                # Rollover amount for that month
                rollover_row = conn.execute(
                    "SELECT COALESCE(rollover_amount, 0) AS total FROM savings WHERE month = ?",
                    (month,)
                ).fetchone()
                rollover = rollover_row["total"] if rollover_row else 0.0
            else:
                # Sum of expenses for that specific category in that month
                spent_row_exp = conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total 
                    FROM transactions 
                    WHERE category_id = ? AND type = 'expense' AND status = 'confirmed' 
                      AND date LIKE ?
                    """,
                    (category_id, f"{month}%")
                ).fetchone()
                spent_row_inc = conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total 
                    FROM transactions 
                    WHERE category_id = ? AND type = 'income' AND status = 'confirmed' 
                      AND date LIKE ?
                    """,
                    (category_id, f"{month}%")
                ).fetchone()
                spent = max(spent_row_exp["total"] - spent_row_inc["total"], 0.0)
                rollover = 0.0
                
            results.append({
                "month": month,
                "spent": spent,
                "rollover": rollover
            })
        return results
    finally:
        conn.close()


def auto_run_all_past_rollovers(db_path=None) -> list[str]:
    """
    Scans transactions to find the earliest transaction month.
    Generates a list of all calendar months from that starting point up to (but excluding) the current month.
    For each month in that list, checks if a record exists in the savings table.
    If not, automatically triggers run_month_end_rollover(month, db_path).
    Returns a list of month strings that were successfully rolled over during this run.
    """
    from datetime import date
    
    today = date.today()
    current_month = today.isoformat()[:7]
    
    # Connect and find the earliest transaction date
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT MIN(date) AS min_date FROM transactions").fetchone()
        min_date_str = row["min_date"] if row and row["min_date"] else None
    finally:
        conn.close()
        
    if not min_date_str:
        # No transactions logged yet, nothing to roll over
        return []
        
    # Parse start year/month
    try:
        start_y = int(min_date_str[:4])
        start_m = int(min_date_str[5:7])
    except (ValueError, IndexError):
        # Fallback if date string is mangled or incomplete
        return []
        
    end_y, end_m = today.year, today.month
    
    # Generate list of all months between earliest transaction and previous month (inclusive)
    months_to_check = []
    y, m = start_y, start_m
    while (y < end_y) or (y == end_y and m < end_m):
        months_to_check.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
            
    # Run rollover for any unclosed months
    rolled_over = []
    for month_str in months_to_check:
        try:
            # Check if already closed
            conn = get_connection(db_path)
            try:
                existing = conn.execute("SELECT id FROM savings WHERE month = ?", (month_str,)).fetchone()
            finally:
                conn.close()
                
            if existing is None:
                run_month_end_rollover(month_str, db_path=db_path)
                rolled_over.append(month_str)
        except ValueError:
            # Already closed or similar conflict
            pass
            
    return rolled_over


