"""
transactions.py — CRUD for transactions, plus the per-category limit
status logic described in spec Section 6.1.

Key rule from the spec: pending_approval transactions (Phase 2 recurring
engine) are excluded from every total, chart, and limit calculation
until approved. All aggregate queries here filter status = 'confirmed'.
"""

import csv
import re
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


def add_split_transaction(
    splits: list[dict],
    total_amount: float,
    type: str = "expense",
    txn_date: str = None,
    description: str = None,
    funding_source: str = "regular",
    status: str = "confirmed",
    db_path=None,
) -> list[int]:
    """
    Creates multiple transactions representing an expense or income split
    across multiple categories within a single atomic database operation.

    Each item in splits:
        {"category_id": int, "amount": float, "description": str (optional)}
    """
    if not splits:
        raise ValueError("At least one split item is required.")

    total_amount = float(total_amount)
    if total_amount <= 0:
        raise ValueError("Total amount must be positive.")

    alloc_sum = sum(float(s["amount"]) for s in splits)
    if abs(alloc_sum - total_amount) > 0.01:
        raise ValueError(
            f"Split allocation total (₹{alloc_sum:.2f}) does not match total amount (₹{total_amount:.2f})."
        )

    if txn_date is None:
        txn_date = date.today().isoformat()

    conn = get_connection(db_path)
    txn_ids = []
    try:
        for idx, s in enumerate(splits, 1):
            s_amt = float(s["amount"])
            if s_amt <= 0:
                raise ValueError("Each split amount must be positive.")
            s_cat = s.get("category_id")
            sub_desc = s.get("description", "").strip()

            if description and sub_desc:
                item_desc = f"{description} ({sub_desc})"
            elif description:
                item_desc = f"{description} [Split {idx}/{len(splits)}]"
            elif sub_desc:
                item_desc = sub_desc
            else:
                item_desc = f"Split transaction {idx}/{len(splits)}"

            cur = conn.execute(
                """
                INSERT INTO transactions
                    (date, amount, type, category_id, description, funding_source, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (txn_date, s_amt, type, s_cat, item_desc, funding_source, status),
            )
            txn_id = cur.lastrowid
            txn_ids.append(txn_id)

            if funding_source in ("savings", "emergency_fund") and type == "expense":
                cat = conn.execute("SELECT * FROM categories WHERE id = ?", (s_cat,)).fetchone()
                if cat and cat["hard_limit"] > 0:
                    spent = _category_spent_this_month_conn(conn, s_cat, txn_date[:7])
                    spent_before = max(0.0, spent - s_amt)
                    remaining_limit = max(0.0, cat["hard_limit"] - spent_before)
                    if s_amt > remaining_limit:
                        deduct_amt = s_amt - remaining_limit
                        if funding_source == "savings":
                            _deduct_from_savings(conn, deduct_amt, txn_date)
                        elif funding_source == "emergency_fund":
                            from .emergency_fund import _adjust_balance as ef_adjust
                            ef_adjust(
                                conn,
                                -deduct_amt,
                                source="manual",
                                note=f"Split expense #{txn_id} overflow: {item_desc}",
                                log_date=txn_date,
                            )
        conn.commit()
        return txn_ids
    except Exception:
        conn.rollback()
        raise
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


def get_transaction(transaction_id: int, db_path=None) -> dict | None:
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_transaction(
    transaction_id: int,
    *,
    amount: float = None,
    type: str = None,
    category_id: int | None = None,
    description: str = None,
    txn_date: str = None,
    funding_source: str = None,
    status: str = None,
    db_path=None,
) -> None:
    conn = get_connection(db_path)
    try:
        old = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if old is None:
            raise ValueError(f"No transaction with id {transaction_id}")

        # 1. Reverse old funding source deduction if applicable
        if old["type"] == "expense" and old["funding_source"] in ("savings", "emergency_fund"):
            cat = conn.execute("SELECT * FROM categories WHERE id = ?", (old["category_id"],)).fetchone()
            if cat and cat["hard_limit"] > 0:
                month = old["date"][:7]
                spent_after = _category_spent_this_month_conn(conn, old["category_id"], month)
                spent_before = max(0.0, spent_after - old["amount"])
                if spent_after > cat["hard_limit"]:
                    overflow_amount = spent_after - max(cat["hard_limit"], spent_before)
                    if overflow_amount > 0:
                        if old["funding_source"] == "savings":
                            _deduct_from_savings(conn, -overflow_amount, old["date"])  # refund
                        elif old["funding_source"] == "emergency_fund":
                            from .emergency_fund import _adjust_balance as ef_adjust
                            ef_adjust(conn, overflow_amount, source="manual",
                                      note=f"Update reversal of txn #{transaction_id}",
                                      log_date=date.today().isoformat())

        # Determine new values
        new_amount = amount if amount is not None else old["amount"]
        new_type = type if type is not None else old["type"]
        new_cat_id = category_id if category_id is not None else old["category_id"]
        new_desc = description if description is not None else old["description"]
        new_date = txn_date if txn_date is not None else old["date"]
        new_funding = funding_source if funding_source is not None else old["funding_source"]
        new_status = status if status is not None else old["status"]

        if new_amount <= 0:
            raise ValueError("amount must be positive")
        if new_type not in ("expense", "income"):
            raise ValueError("type must be 'expense' or 'income'")
        if new_funding not in ("regular", "savings", "emergency_fund"):
            raise ValueError("invalid funding_source")

        # 2. Update the row
        conn.execute(
            """
            UPDATE transactions SET
                amount = ?, type = ?, category_id = ?, description = ?,
                date = ?, funding_source = ?, status = ?
            WHERE id = ?
            """,
            (new_amount, new_type, new_cat_id, new_desc, new_date, new_funding, new_status, transaction_id),
        )

        # 3. Apply new funding source deduction if applicable
        if new_funding in ("savings", "emergency_fund") and new_type == "expense" and new_cat_id is not None:
            cat = conn.execute("SELECT * FROM categories WHERE id = ?", (new_cat_id,)).fetchone()
            if cat and cat["hard_limit"] > 0:
                spent = _category_spent_this_month_conn(conn, new_cat_id, new_date[:7])
                spent_before = max(0.0, spent - new_amount)
                remaining_limit = max(0.0, cat["hard_limit"] - spent_before)
                if new_amount > remaining_limit:
                    deduct_amt = new_amount - remaining_limit
                    if new_funding == "savings":
                        _deduct_from_savings(conn, deduct_amt, new_date)
                    elif new_funding == "emergency_fund":
                        from .emergency_fund import _adjust_balance as ef_adjust
                        ef_adjust(conn, -deduct_amt, source="manual",
                                  note=f"Expense txn #{transaction_id} overflow: {new_desc or 'no description'}",
                                  log_date=new_date)

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
                       status=None, txn_type=None, search_query=None, db_path=None) -> list[dict]:
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
    if search_query:
        query += " AND (description LIKE ? OR CAST(amount AS TEXT) LIKE ?)"
        pattern = f"%{search_query}%"
        params.extend([pattern, pattern])
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


# ── CSV Export & Import (Bank Statement / Google Pay Ingestion) ──────────────────

def export_transactions_csv(
    file_path: str,
    *,
    category_id=None,
    start_date=None,
    end_date=None,
    search_query=None,
    status=None,
    txn_type=None,
    type_=None,
    type=None,
    db_path=None
) -> int:
    """Exports transactions matching the given filter criteria to a CSV file."""
    resolved_type = txn_type or type_ or type
    rows = list_transactions(
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        search_query=search_query,
        status=status,
        txn_type=resolved_type,
        db_path=db_path
    )
    from .categories import list_categories
    cats = {c["id"]: c["name"] for c in list_categories(db_path)}

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Category", "Description", "Amount", "Type", "Funding Source", "Status"])
        for r in rows:
            cat_name = cats.get(r["category_id"], "General Income" if r["type"] == "income" else "")
            writer.writerow([
                r["date"],
                cat_name,
                r["description"] or "",
                f"{r['amount']:.2f}",
                r["type"],
                r["funding_source"],
                r["status"]
            ])
    return len(rows)


def auto_detect_columns(headers: list[str]) -> dict:
    """Intelligently detects column roles from header names (supporting Google Pay & bank statements)."""
    norm = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in headers]
    mapping = {
        "date": None,
        "description": None,
        "amount": None,
        "debit": None,
        "credit": None,
        "type": None,
        "category": None
    }

    date_candidates = ["date", "txn_date", "transaction_date", "value_date", "posting_date", "time", "trans_date"]
    desc_candidates = ["description", "desc", "narration", "remarks", "particulars", "paid_to", "name", "merchant", "payee"]
    amt_candidates = ["amount", "amt", "transaction_amount", "net_amount", "total"]
    debit_candidates = ["debit", "withdrawal", "dr", "debit_amount", "spent", "paid_out"]
    credit_candidates = ["credit", "deposit", "cr", "credit_amount", "received", "paid_in"]
    type_candidates = ["type", "txn_type", "transaction_type", "dr_cr", "cr_dr"]
    cat_candidates = ["category", "category_name", "tag"]

    for orig, n in zip(headers, norm):
        if not mapping["date"] and any(c == n or c in n for c in date_candidates):
            mapping["date"] = orig
        elif not mapping["description"] and any(c == n or c in n for c in desc_candidates):
            mapping["description"] = orig
        elif not mapping["debit"] and any(c == n or c in n for c in debit_candidates):
            mapping["debit"] = orig
        elif not mapping["credit"] and any(c == n or c in n for c in credit_candidates):
            mapping["credit"] = orig
        elif not mapping["amount"] and any(c == n or c in n for c in amt_candidates):
            mapping["amount"] = orig
        elif not mapping["type"] and any(c == n or c in n for c in type_candidates):
            mapping["type"] = orig
        elif not mapping["category"] and any(c == n or c in n for c in cat_candidates):
            mapping["category"] = orig

    return mapping


def normalize_date_string(raw: str) -> str | None:
    if not raw:
        return None
    raw = str(raw).strip()
    if " " in raw:
        raw = raw.split(" ")[0]

    # YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # DD/MM/YYYY or DD-MM-YYYY (numeric month)
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", raw)
    if m:
        d, mon, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mon <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mon:02d}-{d:02d}"
    # DD/MM/YY (numeric month)
    m2 = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})$", raw)
    if m2:
        d, mon, y = int(m2.group(1)), int(m2.group(2)), int(m2.group(3)) + 2000
        if 1 <= mon <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mon:02d}-{d:02d}"
    # DD-Mon-YYYY  e.g. "13-Sep-2026"  or  DD/Mon/YYYY
    for fmt in ("%d-%b-%Y", "%d/%b/%Y", "%d-%b-%y", "%d/%b/%y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # DD Mon YYYY  e.g. "13 Sep 2026"
    try:
        dt = datetime.strptime(raw, "%d %b %Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    # DD Mon YY  e.g. "13 Sep 26"
    try:
        dt = datetime.strptime(raw, "%d %b %y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def normalize_amount_string(raw: str) -> float | None:
    if raw is None:
        return None
    cleaned = re.sub(r"[^\d.-]", "", str(raw).strip())
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_csv_file(file_path: str, column_mapping: dict = None, default_category_id: int = None, db_path=None) -> dict:
    """
    Parses a CSV file using automatic or custom column mapping.
    Matches categories against existing categories in the database.
    Returns preview data, headers, and parsed transaction dicts.
    """
    from .categories import list_categories
    cats = list_categories(db_path)
    cat_by_name = {c["name"].lower().strip(): c["id"] for c in cats}

    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return {"headers": [], "mapping": {}, "rows": [], "error": "CSV file is empty."}

        mapping = column_mapping or auto_detect_columns(headers)

        rows = []
        error_count = 0
        for row_idx, row in enumerate(reader):
            if not any(row):
                continue
            row_dict = {h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(headers)}

            # 1. Parse Date
            date_col = mapping.get("date")
            raw_date = row_dict.get(date_col, "") if date_col else ""
            parsed_date = normalize_date_string(raw_date) or date.today().isoformat()

            # 2. Parse Description
            desc_col = mapping.get("description")
            desc = row_dict.get(desc_col, "") if desc_col else ""

            # 3. Parse Amount and Type
            ttype = "expense"
            amt = None

            debit_col = mapping.get("debit")
            credit_col = mapping.get("credit")
            amt_col = mapping.get("amount")
            type_col = mapping.get("type")

            if debit_col and credit_col:
                debit_val = normalize_amount_string(row_dict.get(debit_col))
                credit_val = normalize_amount_string(row_dict.get(credit_col))
                if debit_val and debit_val > 0:
                    amt = debit_val
                    ttype = "expense"
                elif credit_val and credit_val > 0:
                    amt = credit_val
                    ttype = "income"
            elif amt_col:
                raw_amt = normalize_amount_string(row_dict.get(amt_col))
                if raw_amt is not None:
                    if raw_amt < 0:
                        amt = abs(raw_amt)
                        ttype = "expense"
                    else:
                        amt = raw_amt
                        if type_col:
                            raw_type = row_dict.get(type_col, "").lower()
                            if any(k in raw_type for k in ["cr", "credit", "income", "received"]):
                                ttype = "income"
                            else:
                                ttype = "expense"
                        else:
                            ttype = "expense"

            if amt is None or amt <= 0:
                error_count += 1
                continue

            # 4. Parse Category
            cat_id = None
            cat_col = mapping.get("category")
            if cat_col and row_dict.get(cat_col):
                raw_cat = row_dict.get(cat_col).lower().strip()
                cat_id = cat_by_name.get(raw_cat)

            if cat_id is None and ttype == "expense":
                # Smart keyword categorizer for common merchants
                lower_desc = desc.lower()
                if any(w in lower_desc for w in ["swiggy", "zomato", "restaurant", "cafe", "food", "mcdonald"]):
                    cat_id = cat_by_name.get("food") or cat_by_name.get("dining")
                elif any(w in lower_desc for w in ["uber", "ola", "metro", "fuel", "petrol"]):
                    cat_id = cat_by_name.get("transport") or cat_by_name.get("travel")
                elif any(w in lower_desc for w in ["amazon", "flipkart", "shopping", "myntra"]):
                    cat_id = cat_by_name.get("shopping")

                if cat_id is None:
                    cat_id = default_category_id or (cats[0]["id"] if cats else None)

            rows.append({
                "date": parsed_date,
                "amount": amt,
                "type": ttype,
                "category_id": cat_id,
                "description": desc,
                "funding_source": "regular",
                "status": "confirmed"
            })

        return {
            "headers": headers,
            "mapping": mapping,
            "rows": rows,
            "total_rows": len(rows) + error_count,
            "valid_rows": len(rows),
            "error_count": error_count
        }


def import_transactions_from_rows(parsed_rows: list[dict], db_path=None) -> int:
    """Inserts a list of parsed transaction dictionaries into the database."""
    count = 0
    for r in parsed_rows:
        add_transaction(
            amount=r["amount"],
            type=r["type"],
            category_id=r.get("category_id"),
            description=r.get("description", ""),
            txn_date=r["date"],
            funding_source=r.get("funding_source", "regular"),
            status=r.get("status", "confirmed"),
            db_path=db_path
        )
        count += 1
    return count

