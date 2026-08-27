"""
transactions.py — CRUD for transactions, plus the per-category limit
status logic described in spec Section 6.1.

Key rule from the spec: pending_approval transactions (Phase 2 recurring
engine) are excluded from every total, chart, and limit calculation
until approved. All aggregate queries here filter status = 'confirmed'.
"""

from datetime import date, datetime, timezone
from .db import get_connection
from .settings import get_setting_float


def add_transaction(
    *,
    amount: float,
    type: str,
    category_id: int | None = None,
    description: str = "",
    txn_date: str | None = None,
    funding_source: str = "regular",
    status: str = "confirmed",
    recurring_id: int | None = None,
    db_path=None,
) -> int:
    if type not in ("expense", "income"):
        raise ValueError("type must be 'expense' or 'income'")
    if funding_source not in ("regular", "savings", "emergency_fund"):
        raise ValueError("invalid funding_source")
    if amount <= 0:
        raise ValueError("amount must be positive")
    if txn_date is None:
        txn_date = date.today().isoformat()

    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO transactions
                (date, amount, type, category_id, description, funding_source, recurring_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (txn_date, amount, type, category_id, description, funding_source, recurring_id, status),
        )
        txn_id = cur.lastrowid

        # ── Deduct from the funding pool when not using regular cash ──────────
        if funding_source in ("savings", "emergency_fund") and type == "expense":
            cat = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
            if cat and cat["hard_limit"] > 0:
                spent = _category_spent_this_month_conn(conn, category_id, txn_date[:7])
                # Subtract this transaction's amount to find spent prior to insertion
                spent_before = max(0.0, spent - amount)
                remaining_limit = max(0.0, cat["hard_limit"] - spent_before)
                if amount > remaining_limit:
                    deduct_amt = amount - remaining_limit
                    if funding_source == "savings":
                        _deduct_from_savings(conn, deduct_amt, txn_date)
                    elif funding_source == "emergency_fund":
                        from .emergency_fund import _adjust_balance as ef_adjust
                        ef_adjust(conn, -deduct_amt, source="manual",
                                  note=f"Expense txn #{txn_id} overflow: {description or 'no description'}",
                                  log_date=txn_date)

        conn.commit()
        return txn_id
    finally:
        conn.close()


def _category_spent_this_month_conn(conn, category_id: int, month: str) -> float:
    row_exp = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE category_id = ? AND type = 'expense' AND status = 'confirmed'
          AND date LIKE ?
        """,
        (category_id, f"{month}%"),
    ).fetchone()
    
    row_inc = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE category_id = ? AND type = 'income' AND status = 'confirmed'
          AND date LIKE ?
        """,
        (category_id, f"{month}%"),
    ).fetchone()
    
    return max(row_exp["total"] - row_inc["total"], 0.0)


def _deduct_from_savings(conn, amount: float, txn_date: str) -> None:
    """Insert a negative savings adjustment for the month of the transaction."""
    month = txn_date[:7]
    # Check if a row already exists for this month
    existing = conn.execute(
        "SELECT id, rollover_amount FROM savings WHERE month = ?", (month,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE savings SET rollover_amount = rollover_amount - ? WHERE month = ?",
            (amount, month),
        )
    else:
        # Create a withdrawal-only row for this month
        conn.execute(
            "INSERT INTO savings (month, rollover_amount, emergency_fund_delta) VALUES (?, ?, 0)",
            (month, -amount),
        )


def update_transaction(transaction_id: int, *, amount=None, category_id=None,
                        description=None, txn_date=None, funding_source=None,
                        status=None, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if row is None:
            raise ValueError(f"No transaction with id {transaction_id}")

        conn.execute(
            """
            UPDATE transactions SET
                amount = ?, category_id = ?, description = ?,
                date = ?, funding_source = ?, status = ?
            WHERE id = ?
            """,
            (
                amount if amount is not None else row["amount"],
                category_id if category_id is not None else row["category_id"],
                description if description is not None else row["description"],
                txn_date if txn_date is not None else row["date"],
                funding_source if funding_source is not None else row["funding_source"],
                status if status is not None else row["status"],
                transaction_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def delete_transaction(transaction_id: int, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
        if row is None:
            conn.close()
            return

        # ── Reverse any savings/EF deduction that was made when adding ───────
        if row["type"] == "expense" and row["funding_source"] in ("savings", "emergency_fund"):
            cat = conn.execute("SELECT * FROM categories WHERE id = ?", (row["category_id"],)).fetchone()
            if cat and cat["hard_limit"] > 0:
                month = row["date"][:7]
                # current spent in db includes this transaction's amount
                spent_after = _category_spent_this_month_conn(conn, row["category_id"], month)
                spent_before = max(0.0, spent_after - row["amount"])
                if spent_after > cat["hard_limit"]:
                    overflow_amount = spent_after - max(cat["hard_limit"], spent_before)
                    if overflow_amount > 0:
                        if row["funding_source"] == "savings":
                            _deduct_from_savings(conn, -overflow_amount, row["date"])  # negative = refund
                        elif row["funding_source"] == "emergency_fund":
                            from .emergency_fund import _adjust_balance as ef_adjust
                            ef_adjust(conn, overflow_amount, source="manual",
                                      note=f"Reversal of deleted txn #{transaction_id} overflow",
                                      log_date=date.today().isoformat())

        conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
    finally:
        conn.close()


def approve_transaction(transaction_id: int, *, actual_date: str = None,
                         actual_amount: float = None, db_path=None) -> None:
    """Phase-2 recurring-approval action: flips a pending_approval row to
    confirmed, optionally correcting date/amount first (Section 8.1)."""
    update_transaction(
        transaction_id,
        txn_date=actual_date,
        amount=actual_amount,
        status="confirmed",
        db_path=db_path,
    )


def dismiss_transaction(transaction_id: int, db_path=None) -> None:
    """Phase-2 recurring-approval action: discard a pending occurrence
    entirely (e.g. a subscription that was cancelled that month)."""
    delete_transaction(transaction_id, db_path=db_path)


def list_transactions(*, category_id=None, start_date=None, end_date=None,
                       status=None, txn_type=None, db_path=None) -> list[dict]:
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if category_id is not None:
        query += " AND category_id = ?"
        params.append(category_id)
    if start_date is not None:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date is not None:
        query += " AND date <= ?"
        params.append(end_date)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    if txn_type is not None:
        query += " AND type = ?"
        params.append(txn_type)
    query += " ORDER BY date DESC, id DESC"

    conn = get_connection(db_path)
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def category_spent_this_month(category_id: int, month: str = None, db_path=None) -> float:
    if month is None:
        month = date.today().isoformat()[:7]
    conn = get_connection(db_path)
    try:
        row_exp = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE category_id = ? AND type = 'expense' AND status = 'confirmed'
              AND date LIKE ?
            """,
            (category_id, f"{month}%"),
        ).fetchone()
        
        row_inc = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE category_id = ? AND type = 'income' AND status = 'confirmed'
              AND date LIKE ?
            """,
            (category_id, f"{month}%"),
        ).fetchone()
        
        # Net spent: expenses minus any category-specific supplement/contribution
        return max(row_exp["total"] - row_inc["total"], 0.0)
    finally:
        conn.close()


def category_status(category_id: int, month: str = None, db_path=None) -> dict:
    """Implements the state machine from Figure 3 of the spec:
    under soft -> approaching hard -> at/over hard (overflow into savings).

    Returns a dict the UI can use directly to color the bar and, when
    relevant, show the proximity or overflow message from Section 6.1.
    """
    from .categories import get_category  # local import avoids a cycle

    cat = get_category(category_id, db_path)
    if cat is None:
        raise ValueError(f"No category with id {category_id}")

    spent = category_spent_this_month(category_id, month, db_path)
    soft, hard = cat["soft_limit"], cat["hard_limit"]
    warn_threshold = get_setting_float("hard_limit_warn_threshold", db_path)

    if spent < soft:
        state = "under_soft"
    elif spent < hard:
        state = "approaching_hard" if (hard - spent) <= warn_threshold else "between_soft_hard"
    elif spent == hard:
        state = "at_hard"
    else:  # spent > hard
        state = "over_hard"

    result = {
        "category_id": category_id,
        "category_name": cat["name"],
        "spent": spent,
        "soft_limit": soft,
        "hard_limit": hard,
        "state": state,
        "remaining_to_hard": max(hard - spent, 0),
        "overflow_amount": max(spent - hard, 0),
    }

    from .settings import get_setting
    currency = get_setting("currency_symbol", db_path) or "₹"

    if state == "approaching_hard":
        result["message"] = f"You're {currency}{result['remaining_to_hard']:.2f} away from your {cat['name']} hard limit."
    elif state == "at_hard":
        result["message"] = f"You've exactly reached your {cat['name']} hard limit."
    elif state == "over_hard":
        result["message"] = f"Overflow: {currency}{result['overflow_amount']:.2f} above hard limit — excess will roll into savings."
    else:
        result["message"] = None

    return result


def preview_transaction_impact(category_id: int, amount: float, month: str = None, db_path=None) -> dict:
    """What the Add-Transaction UI calls BEFORE saving, to show the live
    inline feedback described in spec Section 7.2 (proximity message /
    overflow banner) without having committed the transaction yet."""
    from .categories import get_category
    from .settings import get_setting
    currency = get_setting("currency_symbol", db_path) or "₹"

    cat = get_category(category_id, db_path)
    if cat is None:
        raise ValueError(f"No category with id {category_id}")

    current_spent = category_spent_this_month(category_id, month, db_path)
    projected_spent = current_spent + amount
    soft, hard = cat["soft_limit"], cat["hard_limit"]
    warn_threshold = get_setting_float("hard_limit_warn_threshold", db_path)

    if projected_spent < soft:
        state = "under_soft"
        message = None
    elif projected_spent < hard:
        remaining = hard - projected_spent
        if remaining <= warn_threshold:
            state = "approaching_hard"
            message = f"You're {currency}{remaining:.2f} away from your {cat['name']} hard limit."
        else:
            state = "between_soft_hard"
            message = None
    elif projected_spent == hard:
        state = "at_hard"
        message = f"This will exactly reach your {cat['name']} hard limit."
    else:  # projected_spent > hard
        state = "over_hard"
        overflow = projected_spent - hard
        message = f"Overflow: {currency}{overflow:.2f} above hard limit — excess rolls into savings."

    return {
        "category_id": category_id,
        "current_spent": current_spent,
        "projected_spent": projected_spent,
        "state": state,
        "message": message,
    }

