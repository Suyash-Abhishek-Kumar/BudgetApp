"""
savings_goals.py — CRUD and progress tracking for dedicated named savings goals.
Allows users to set aside money for specific milestones (e.g. Vacation, Laptop, Down Payment)
with target amounts, target dates, and real-time progress calculations.
"""

from datetime import date, datetime, timezone
from pathlib import Path
from .db import get_connection


def create_goal(
    name: str,
    target_amount: float,
    target_date: str | None = None,
    initial_saved: float = 0.0,
    db_path: Path | str | None = None,
) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("Goal name cannot be empty.")
    target_amount = float(target_amount)
    if target_amount <= 0:
        raise ValueError("Target amount must be positive.")
    initial_saved = max(0.0, float(initial_saved or 0.0))

    if target_date:
        target_date = target_date.strip()
        try:
            date.fromisoformat(target_date)
        except ValueError:
            raise ValueError("Target date must be in YYYY-MM-DD format.")
    else:
        target_date = None

    is_completed = 1 if initial_saved >= target_amount else 0
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO savings_goals (name, target_amount, saved_amount, target_date, created_at, is_completed)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, target_amount, initial_saved, target_date, now_iso, is_completed),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_goal(
    goal_id: int,
    *,
    name: str | None = None,
    target_amount: float | None = None,
    target_date: str | None = None,
    is_completed: int | None = None,
    db_path: Path | str | None = None,
) -> None:
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT * FROM savings_goals WHERE id = ?", (goal_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Savings goal #{goal_id} not found.")

        new_name = name.strip() if name is not None else row["name"]
        if not new_name:
            raise ValueError("Goal name cannot be empty.")

        new_target = float(target_amount) if target_amount is not None else row["target_amount"]
        if new_target <= 0:
            raise ValueError("Target amount must be positive.")

        if target_date is not None:
            td = target_date.strip()
            if td:
                try:
                    date.fromisoformat(td)
                    new_date = td
                except ValueError:
                    raise ValueError("Target date must be in YYYY-MM-DD format.")
            else:
                new_date = None
        else:
            new_date = row["target_date"]

        if is_completed is not None:
            new_completed = int(is_completed)
        else:
            new_completed = 1 if row["saved_amount"] >= new_target else 0

        conn.execute(
            """
            UPDATE savings_goals
            SET name = ?, target_amount = ?, target_date = ?, is_completed = ?
            WHERE id = ?
            """,
            (new_name, new_target, new_date, new_completed, goal_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_goal(goal_id: int, db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
        conn.commit()
    finally:
        conn.close()


def get_goal(goal_id: int, db_path: Path | str | None = None) -> dict | None:
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT * FROM savings_goals WHERE id = ?", (goal_id,))
        row = cur.fetchone()
        if not row:
            return None
        return _enrich_goal(dict(row))
    finally:
        conn.close()


def adjust_goal_saved(
    goal_id: int,
    amount_delta: float,
    db_path: Path | str | None = None,
) -> float:
    """
    Deposits (positive delta) or withdraws (negative delta) from a savings goal.
    Returns the new saved_amount.
    """
    amount_delta = float(amount_delta)
    conn = get_connection(db_path)
    try:
        cur = conn.execute("SELECT * FROM savings_goals WHERE id = ?", (goal_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Savings goal #{goal_id} not found.")

        current = float(row["saved_amount"])
        target = float(row["target_amount"])
        new_saved = round(current + amount_delta, 2)
        if new_saved < 0:
            raise ValueError(
                f"Cannot withdraw ₹{abs(amount_delta):,.2f}; goal only has ₹{current:,.2f} saved."
            )

        new_completed = 1 if new_saved >= target else 0

        conn.execute(
            "UPDATE savings_goals SET saved_amount = ?, is_completed = ? WHERE id = ?",
            (new_saved, new_completed, goal_id),
        )
        conn.commit()
        return new_saved
    finally:
        conn.close()


def list_goals(db_path: Path | str | None = None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT * FROM savings_goals
            ORDER BY is_completed ASC, target_date IS NULL, target_date ASC, id DESC
            """
        )
        rows = cur.fetchall()
        return [_enrich_goal(dict(r)) for r in rows]
    finally:
        conn.close()


def goals_summary(db_path: Path | str | None = None) -> dict:
    goals = list_goals(db_path=db_path)
    total_target = sum(g["target_amount"] for g in goals)
    total_saved = sum(g["saved_amount"] for g in goals)
    overall_pct = min(100.0, round((total_saved / total_target) * 100, 1)) if total_target > 0 else 0.0
    active_count = sum(1 for g in goals if not g["is_completed"])
    completed_count = sum(1 for g in goals if g["is_completed"])

    return {
        "total_target": total_target,
        "total_saved": total_saved,
        "overall_pct": overall_pct,
        "active_count": active_count,
        "completed_count": completed_count,
        "goals": goals,
    }


def _enrich_goal(goal: dict) -> dict:
    target = float(goal["target_amount"])
    saved = float(goal["saved_amount"])
    pct = min(100.0, round((saved / target) * 100, 1)) if target > 0 else 0.0
    remaining = max(0.0, target - saved)

    days_left = None
    if goal.get("target_date"):
        try:
            t_date = date.fromisoformat(goal["target_date"])
            days_left = (t_date - date.today()).days
        except Exception:
            days_left = None

    goal["pct"] = pct
    goal["remaining"] = remaining
    goal["days_left"] = days_left
    return goal
