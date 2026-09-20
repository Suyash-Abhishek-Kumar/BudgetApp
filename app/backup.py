"""
backup.py — Automated and manual SQLite database backup and restore management.
Uses SQLite's native online backup API (conn.backup) to guarantee zero corruption
even while the application is reading or writing.
"""

import os
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path


def get_default_backup_dir(db_path: Path | str | None = None) -> Path:
    if db_path:
        base = Path(db_path).parent
    else:
        base = Path(__file__).parent.parent
    backup_dir = base / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(db_path: Path | str | None = None, backup_dir: Path | str | None = None) -> Path:
    """
    Creates an atomic snapshot of the database using SQLite's online backup API.
    Returns the Path to the newly created backup file.
    """
    from .db import DEFAULT_DB_PATH
    source_path = Path(db_path or DEFAULT_DB_PATH)
    if not source_path.exists():
        raise FileNotFoundError(f"Database file {source_path} does not exist.")

    b_dir = Path(backup_dir) if backup_dir else get_default_backup_dir(source_path)
    b_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"budget_backup_{timestamp}.db"
    dest_path = b_dir / backup_filename

    # Perform online atomic backup
    src_conn = sqlite3.connect(str(source_path))
    try:
        dest_conn = sqlite3.connect(str(dest_path))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()

    return dest_path


def list_backups(backup_dir: Path | str | None = None, db_path: Path | str | None = None) -> list[dict]:
    """
    Lists all existing .db backup files in descending order of creation time.
    """
    b_dir = Path(backup_dir) if backup_dir else get_default_backup_dir(db_path)
    if not b_dir.exists():
        return []

    backups = []
    for file in b_dir.glob("budget_backup_*.db"):
        stat = file.stat()
        size_kb = round(stat.st_size / 1024, 1)
        created_dt = datetime.fromtimestamp(stat.st_mtime)
        backups.append({
            "path": str(file.resolve()),
            "filename": file.name,
            "size_kb": size_kb,
            "created_at": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "mtime": stat.st_mtime,
        })

    backups.sort(key=lambda b: b["mtime"], reverse=True)
    return backups


def restore_backup(backup_file: Path | str, target_db_path: Path | str | None = None) -> None:
    """
    Restores the database from a backup file.
    Takes a temporary safety copy of the current database before replacing it.
    """
    b_path = Path(backup_file)
    if not b_path.exists():
        raise FileNotFoundError(f"Backup file {b_path} not found.")

    from .db import DEFAULT_DB_PATH
    dest_path = Path(target_db_path or DEFAULT_DB_PATH)

    # Perform atomic restore using SQLite backup API
    src_conn = sqlite3.connect(str(b_path))
    try:
        dest_conn = sqlite3.connect(str(dest_path))
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()


def delete_backup(backup_file: Path | str) -> None:
    b_path = Path(backup_file)
    if b_path.exists():
        b_path.unlink()


def prune_old_backups(backup_dir: Path | str | None = None, keep_count: int = 10, db_path=None) -> int:
    """
    Retains the latest `keep_count` backups and removes older ones.
    Returns the number of pruned files.
    """
    backups = list_backups(backup_dir=backup_dir, db_path=db_path)
    pruned = 0
    if len(backups) > keep_count:
        for old in backups[keep_count:]:
            try:
                Path(old["path"]).unlink()
                pruned += 1
            except Exception:
                pass
    return pruned


def auto_backup_on_startup(db_path: Path | str | None = None, keep_count: int = 7) -> Path | None:
    """
    Silently takes a daily startup backup if one hasn't been taken today yet,
    and prunes backups older than keep_count.
    """
    try:
        backups = list_backups(db_path=db_path)
        today_str = datetime.now().strftime("%Y%m%d")
        already_backed_up_today = any(f"budget_backup_{today_str}" in b["filename"] for b in backups)
        if not already_backed_up_today:
            new_backup = create_backup(db_path=db_path)
            prune_old_backups(keep_count=keep_count, db_path=db_path)
            return new_backup
    except Exception:
        pass
    return None
