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
