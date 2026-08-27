"""
emergency_fund.py — balance tracking, deposit/withdrawal log, and the
manual "move money" action from spec Section 6.4.

The automatic monthly-rollover contribution lives in budget_logic.py
(run_month_end_rollover), which calls _adjust_balance() here so all
balance changes — automatic or manual — go through one audited path.
"""

from datetime import date, datetime, timezone
from .db import get_connection


def _ensure_row(conn) -> None:
    row = conn.execute("SELECT id FROM emergency_fund LIMIT 1").fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO emergency_fund (balance, last_updated) VALUES (0, ?)",
            (datetime.now(timezone.utc).isoformat(),),
        )


def get_balance(db_path=None) -> float:
    conn = get_connection(db_path)
    try:
        _ensure_row(conn)
        conn.commit()
        row = conn.execute("SELECT balance FROM emergency_fund LIMIT 1").fetchone()
        return row["balance"]
    finally:
        conn.close()


def _adjust_balance(conn, delta: float, source: str, note: str = None,
                     log_date: str = None) -> None:
    """Internal: apply a signed delta to the single emergency_fund row
    and record it in emergency_fund_log. Caller must commit."""
    _ensure_row(conn)
    conn.execute(
        "UPDATE emergency_fund SET balance = balance + ?, last_updated = ?",
        (delta, datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "INSERT INTO emergency_fund_log (date, amount, source, note) VALUES (?, ?, ?, ?)",
        (log_date or date.today().isoformat(), delta, source, note),
    )


def manual_transfer(amount: float, direction: str, note: str = None, db_path=None) -> None:
    """direction: 'to_emergency_fund' deposits `amount` into the fund;
    'to_savings' withdraws `amount` from it. Amount is always positive;
    the sign is derived from direction."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    if direction not in ("to_emergency_fund", "to_savings"):
        raise ValueError("direction must be 'to_emergency_fund' or 'to_savings'")

    delta = amount if direction == "to_emergency_fund" else -amount
    conn = get_connection(db_path)
    try:
        current = get_balance(db_path)
        if direction == "to_savings" and amount > current:
            raise ValueError(f"Cannot move {amount}: emergency fund balance is only {current}")
        _adjust_balance(conn, delta, source="manual", note=note)
        conn.commit()
    finally:
        conn.close()


def get_log(limit: int = 50, db_path=None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM emergency_fund_log ORDER BY date DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
