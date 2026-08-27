"""
db.py — connection management and schema initialization.

Single-user, local SQLite database. One connection is opened per call
via `get_connection()`, using sqlite3.Row so results behave like dicts.
"""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Default location for the live database. The app (Milestone 2+) will
# point this at a real per-user path (e.g. ~/Library/Application Support/
# BudgetApp/budget.db on macOS); for now it defaults next to this file.
DEFAULT_DB_PATH = Path(__file__).parent / "budget.db"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a connection with foreign keys enforced and Row access.
    Passing None (the common case) uses DEFAULT_DB_PATH."""
    conn = sqlite3.connect(str(db_path or DEFAULT_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create all tables if they don't already exist."""
    schema_sql = SCHEMA_PATH.read_text()
    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def reset_db(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Danger: wipes the database file entirely and recreates an empty one.
    Intended for tests/dev only — never call this from the running app
    without an explicit, confirmed user action."""
    p = Path(db_path)
    if p.exists():
        p.unlink()
    init_db(db_path)
