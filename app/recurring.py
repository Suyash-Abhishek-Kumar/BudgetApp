"""
recurring.py — CRUD operations for recurring transaction rules (Milestone 4 / Phase 2).
"""

from datetime import datetime, timezone
from .db import get_connection


def create_rule(
    *,
    category_id: int | None,
    amount: float,
    description: str,
    rule_type: str,
    frequency: str,
    interval_days: int | None = None,
    next_due_date: str,
    db_path=None,
) -> int:
    if rule_type not in ("expense", "income"):
        raise ValueError("rule_type must be 'expense' or 'income'")
    if frequency not in ("daily", "monthly", "yearly", "custom"):
        raise ValueError("frequency must be 'daily', 'monthly', 'yearly', or 'custom'")
    if amount <= 0:
        raise ValueError("amount must be positive")

    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO recurring_transactions
                (category_id, amount, description, type, frequency, interval_days, next_due_date, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                category_id,
                amount,
                description,
                rule_type,
                frequency,
                interval_days,
                next_due_date,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_rule(
    rule_id: int,
    *,
    category_id=None,
    amount=None,
    description=None,
    rule_type=None,
    frequency=None,
    interval_days=None,
    next_due_date=None,
    active=None,
    db_path=None,
) -> None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM recurring_transactions WHERE id = ?", (rule_id,)).fetchone()
        if row is None:
            raise ValueError(f"No rule with id {rule_id}")

        new_cat = category_id if category_id is not None else row["category_id"]
        new_amt = amount if amount is not None else row["amount"]
        new_desc = description if description is not None else row["description"]
        new_type = rule_type if rule_type is not None else row["type"]
        new_freq = frequency if frequency is not None else row["frequency"]
        new_interval = interval_days if interval_days is not None else row["interval_days"]
        new_due = next_due_date if next_due_date is not None else row["next_due_date"]
        new_active = active if active is not None else row["active"]

        if new_type not in ("expense", "income"):
            raise ValueError("type must be 'expense' or 'income'")
        if new_freq not in ("daily", "monthly", "yearly", "custom"):
            raise ValueError("frequency must be 'daily', 'monthly', 'yearly', or 'custom'")
        if new_amt <= 0:
            raise ValueError("amount must be positive")

        conn.execute(
            """
            UPDATE recurring_transactions SET
                category_id = ?, amount = ?, description = ?,
                type = ?, frequency = ?, interval_days = ?,
                next_due_date = ?, active = ?
            WHERE id = ?
            """,
            (new_cat, new_amt, new_desc, new_type, new_freq, new_interval, new_due, new_active, rule_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_rule(rule_id: int, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        # Null out reference in historical transactions first to preserve references without restriction errors
        conn.execute("UPDATE transactions SET recurring_id = NULL WHERE recurring_id = ?", (rule_id,))
        conn.execute("DELETE FROM recurring_transactions WHERE id = ?", (rule_id,))
        conn.commit()
    finally:
        conn.close()


def list_rules(db_path=None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM recurring_transactions ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_rule(rule_id: int, db_path=None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM recurring_transactions WHERE id = ?", (rule_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
