"""Recurring Journal Router — Beauty & Shine POS-ERP V6."""

from __future__ import annotations
from typing import Optional
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/recurring-journal", tags=["Recurring Journal"])


class RecurringJournalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_debit: list[dict] = []
    template_credit: list[dict] = []
    frequency: str = "monthly"
    next_run_date: date
    end_date: Optional[date] = None
    max_runs: Optional[int] = None
    auto_post: bool = False
    branch_id: Optional[str] = None


class RecurringJournalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_debit: Optional[list[dict]] = None
    template_credit: Optional[list[dict]] = None
    frequency: Optional[str] = None
    next_run_date: Optional[date] = None
    end_date: Optional[date] = None
    max_runs: Optional[int] = None
    auto_post: Optional[bool] = None
    is_active: Optional[bool] = None


FREQ_DAYS = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30, "quarterly": 90, "yearly": 365}


@router.get("/list")
def list_recurring_journals(
    branch_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    offset: int = 0,
    limit: int = 50,
):
    conditions, params = [], []
    if branch_id:
        conditions.append("rj.branch_id = %s")
        params.append(branch_id)
    if is_active is not None:
        conditions.append("rj.is_active = %s")
        params.append(is_active)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT rj.*, b.name AS branch_name
            FROM recurring_journal rj
            LEFT JOIN branch b ON rj.branch_id = b.id
            {where} ORDER BY rj.next_run_date LIMIT %s OFFSET %s""",
        tuple(params),
    )
    return {"recurring_journals": rows, "total": len(rows)}


@router.get("/{rj_id}")
def get_recurring_journal(rj_id: int):
    row = fetch_one(
        """SELECT rj.*, b.name AS branch_name
           FROM recurring_journal rj LEFT JOIN branch b ON rj.branch_id = b.id
           WHERE rj.id = %s""",
        (rj_id,),
    )
    if not row:
        raise HTTPException(404, "Recurring journal not found")
    logs = fetch_all(
        "SELECT * FROM recurring_journal_log WHERE recurring_journal_id = %s ORDER BY run_date DESC LIMIT 50",
        (rj_id,),
    )
    return {**row, "logs": logs}


@router.post("/create")
def create_recurring_journal(data: RecurringJournalCreate):
    row = execute_returning(
        """INSERT INTO recurring_journal (name, description, template_debit, template_credit,
           frequency, next_run_date, end_date, max_runs, auto_post, branch_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (data.name, data.description, _json(data.template_debit), _json(data.template_credit),
         data.frequency, data.next_run_date, data.end_date, data.max_runs, data.auto_post, data.branch_id),
    )
    return row


@router.put("/{rj_id}")
def update_recurring_journal(rj_id: int, data: RecurringJournalUpdate):
    existing = fetch_one("SELECT * FROM recurring_journal WHERE id = %s", (rj_id,))
    if not existing:
        raise HTTPException(404, "Recurring journal not found")
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return existing
    sets, vals = [], []
    for k, v in fields.items():
        if k in ("template_debit", "template_credit"):
            v = _json(v)
        sets.append(f"{k} = %s")
        vals.append(v)
    sets.append("updated_at = now()")
    vals.append(rj_id)
    row = execute_returning(
        f"UPDATE recurring_journal SET {', '.join(sets)} WHERE id = %s RETURNING *",
        tuple(vals),
    )
    return row


@router.post("/{rj_id}/run")
def run_recurring_journal(rj_id: int):
    """Manually execute a recurring journal — creates journal entry from template."""
    rj = fetch_one("SELECT * FROM recurring_journal WHERE id = %s", (rj_id,))
    if not rj:
        raise HTTPException(404, "Recurring journal not found")
    if not rj["is_active"]:
        raise HTTPException(400, "Recurring journal is not active")

    # Create journal entry
    je = execute_returning(
        """INSERT INTO journal_entry (entry_date, description, source_type, status)
           VALUES (CURRENT_DATE, %s, 'recurring', 'posted') RETURNING id""",
        (f"Recurring: {rj['name']}",),
    )
    je_id = je["id"]

    # Create debit lines
    debit_entries = rj["template_debit"] or []
    credit_entries = rj["template_credit"] or []
    for line in debit_entries:
        execute(
            """INSERT INTO journal_entry_line (journal_entry_id, account_id, debit, credit, description)
               VALUES (%s, %s, %s, 0, %s)""",
            (je_id, line.get("account_id"), line.get("amount", 0), line.get("description", "")),
        )
    for line in credit_entries:
        execute(
            """INSERT INTO journal_entry_line (journal_entry_id, account_id, debit, credit, description)
               VALUES (%s, %s, 0, %s, %s)""",
            (je_id, line.get("account_id"), line.get("amount", 0), line.get("description", "")),
        )

    # Log and update
    execute(
        """INSERT INTO recurring_journal_log (recurring_journal_id, journal_entry_id, run_date, status)
           VALUES (%s, %s, CURRENT_DATE, 'posted')""",
        (rj_id, je_id),
    )
    new_total = (rj["total_runs"] or 0) + 1
    freq = rj["frequency"] or "monthly"
    next_run = date.today() + timedelta(days=FREQ_DAYS.get(freq, 30))
    execute(
        "UPDATE recurring_journal SET total_runs = %s, last_run_date = CURRENT_DATE, next_run_date = %s, updated_at = now() WHERE id = %s",
        (new_total, next_run, rj_id),
    )
    return {"journal_entry_id": je_id, "run_number": new_total, "next_run_date": str(next_run)}


@router.delete("/{rj_id}")
def delete_recurring_journal(rj_id: int):
    n = execute("DELETE FROM recurring_journal WHERE id = %s", (rj_id,))
    if n == 0:
        raise HTTPException(404, "Recurring journal not found")
    return {"deleted": True}


def _json(v):
    import json
    return json.dumps(v) if isinstance(v, list) else v
