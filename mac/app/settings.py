"""
settings.py — dynamic key/value settings.

Nothing about thresholds is hardcoded in logic.py; every value read
there comes through get_setting(), which falls back to DEFAULTS only
if the user has never set that key. Editing Settings in the UI is just
set_setting() calls — no schema or code change needed.
"""

from datetime import datetime, timezone
from .db import get_connection

# Fallback values, used only the first time a key is read before the
# user (or app init) has ever set it.
DEFAULTS = {
    "hard_limit_warn_threshold": "50",       # dollars away from hard limit that triggers a warning
    "default_soft_limit": "100",
    "default_hard_limit": "150",
    "ef_target_amount": "1000",
    "ef_monthly_contribution": "50",         # $ or % depending on ef_monthly_contribution_type
    "ef_monthly_contribution_type": "fixed", # 'fixed' or 'percent'
    "currency_symbol": "₹",

}


def get_setting(key: str, db_path=None) -> str:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is not None:
            return row["value"]
        return DEFAULTS.get(key)
    finally:
        conn.close()


def get_setting_float(key: str, db_path=None) -> float:
    return float(get_setting(key, db_path))


def set_setting(key: str, value, db_path=None) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()


def all_settings(db_path=None) -> dict:
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        merged = dict(DEFAULTS)
        merged.update({r["key"]: r["value"] for r in rows})
        return merged
    finally:
        conn.close()
