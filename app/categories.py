"""
categories.py — CRUD for budget categories.

soft_limit / hard_limit are fully dynamic per category (Section 6.1 of
the spec) — creating a category without explicit limits falls back to
the Settings defaults, but every value is stored per-row and editable
any time from the Settings screen.
"""

from datetime import datetime, timezone
from .db import get_connection
from .settings import get_setting_float


def create_category(name: str, soft_limit: float = None, hard_limit: float = None, db_path=None) -> int:
    if soft_limit is None:
        soft_limit = get_setting_float("default_soft_limit", db_path)
    if hard_limit is None:
        hard_limit = get_setting_float("default_hard_limit", db_path)
    if hard_limit < soft_limit:
        raise ValueError("hard_limit must be >= soft_limit")

    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO categories (name, soft_limit, hard_limit, created_at) VALUES (?, ?, ?, ?)",
            (name, soft_limit, hard_limit, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_category(category_id: int, *, name: str = None, soft_limit: float = None,
                     hard_limit: float = None, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        if row is None:
            raise ValueError(f"No category with id {category_id}")

        new_name = name if name is not None else row["name"]
        new_soft = soft_limit if soft_limit is not None else row["soft_limit"]
        new_hard = hard_limit if hard_limit is not None else row["hard_limit"]
        if new_hard < new_soft:
            raise ValueError("hard_limit must be >= soft_limit")

        conn.execute(
            "UPDATE categories SET name = ?, soft_limit = ?, hard_limit = ? WHERE id = ?",
            (new_name, new_soft, new_hard, category_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_category(category_id: int, db_path=None) -> None:
    """Refuses to delete a category that still has transactions, to avoid
    silently orphaning financial history."""
    conn = get_connection(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?", (category_id,)
        ).fetchone()["n"]
        if count > 0:
            raise ValueError(
                f"Category {category_id} has {count} transaction(s); reassign or delete them first."
            )
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
    finally:
        conn.close()


def get_category(category_id: int, db_path=None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_category_by_name(name: str, db_path=None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM categories WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_categories(db_path=None) -> list[dict]:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def transfer_category_budget(
    from_cat_id: int,
    to_cat_id: int,
    amount: float,
    adjust_soft: bool = True,
    db_path=None,
) -> dict:
    """
    Transfers envelope budget between two categories by adjusting hard_limit
    (and proportionally soft_limit).
    """
    amount = float(amount)
    if amount <= 0:
        raise ValueError("Transfer amount must be positive.")
    if from_cat_id == to_cat_id:
        raise ValueError("Source and destination categories must be different.")

    conn = get_connection(db_path)
    try:
        from_cat = conn.execute("SELECT * FROM categories WHERE id = ?", (from_cat_id,)).fetchone()
        to_cat = conn.execute("SELECT * FROM categories WHERE id = ?", (to_cat_id,)).fetchone()

        if not from_cat:
            raise ValueError(f"Source category id={from_cat_id} not found.")
        if not to_cat:
            raise ValueError(f"Destination category id={to_cat_id} not found.")

        from_hard = float(from_cat["hard_limit"])
        from_soft = float(from_cat["soft_limit"])
        if from_hard < amount:
            raise ValueError(
                f"Insufficient limit in '{from_cat['name']}'. Hard limit is ₹{from_hard:.2f}, attempted transfer: ₹{amount:.2f}"
            )

        new_from_hard = round(from_hard - amount, 2)
        if adjust_soft and from_hard > 0:
            ratio = from_soft / from_hard
            new_from_soft = round(new_from_hard * ratio, 2)
        else:
            new_from_soft = min(from_soft, new_from_hard)

        to_hard = float(to_cat["hard_limit"])
        to_soft = float(to_cat["soft_limit"])
        new_to_hard = round(to_hard + amount, 2)
        if adjust_soft and to_hard > 0:
            ratio = to_soft / to_hard
            new_to_soft = round(new_to_hard * ratio, 2)
        else:
            new_to_soft = to_soft

        conn.execute(
            "UPDATE categories SET soft_limit = ?, hard_limit = ? WHERE id = ?",
            (new_from_soft, new_from_hard, from_cat_id),
        )
        conn.execute(
            "UPDATE categories SET soft_limit = ?, hard_limit = ? WHERE id = ?",
            (new_to_soft, new_to_hard, to_cat_id),
        )
        conn.commit()

        return {
            "from_cat": {
                "id": from_cat_id,
                "name": from_cat["name"],
                "old_hard": from_hard,
                "new_hard": new_from_hard,
                "old_soft": from_soft,
                "new_soft": new_from_soft,
            },
            "to_cat": {
                "id": to_cat_id,
                "name": to_cat["name"],
                "old_hard": to_hard,
                "new_hard": new_to_hard,
                "old_soft": to_soft,
                "new_soft": new_to_soft,
            },
            "amount": amount,
        }
    finally:
        conn.close()

