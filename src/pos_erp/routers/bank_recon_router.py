"""Bank Reconciliation Router - Beauty & Shine POS-ERP V6."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/bank-recon", tags=["Bank Reconciliation"])


# ── Pydantic Models ──────────────────────────────────────────────────────────


class BankMutationImportRow(BaseModel):
    transaction_date: str
    description: str
    reference: Optional[str] = None
    amount: float
    bank_account_id: int
    mutation_type: str  # debit / credit


class BankMutationImportRequest(BaseModel):
    rows: list[BankMutationImportRow]


class MutationMatchRequest(BaseModel):
    journal_entry_id: int


class AutoMatchRequest(BaseModel):
    bank_account_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ReconciliationCreateRequest(BaseModel):
    bank_account_id: int
    period_start: str
    period_end: str
    opening_balance: float = 0
    closing_balance: float = 0


class ReconciliationCloseRequest(BaseModel):
    closed_by: Optional[str] = None


# ── Bank Mutation Endpoints ──────────────────────────────────────────────────


@router.post("/bank-mutation/import")
def import_bank_mutations(req: BankMutationImportRequest):
    """Bulk import bank mutations."""
    if not req.rows:
        raise HTTPException(400, "No rows to import")
    imported = 0
    errors: list[dict] = []
    for idx, row in enumerate(req.rows):
        try:
            execute_returning(
                """INSERT INTO bank_mutation
                   (bank_account_id, transaction_date, description, reference,
                    amount, mutation_type, matched, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, false, NOW())
                   RETURNING id""",
                (
                    row.bank_account_id,
                    row.transaction_date,
                    row.description,
                    row.reference,
                    row.amount,
                    row.mutation_type,
                ),
            )
            imported += 1
        except Exception as e:
            errors.append({"row": idx, "error": str(e)})
    return {"imported": imported, "errors": errors}


@router.get("/bank-mutation")
def list_bank_mutations(
    bank_account_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    matched: Optional[bool] = None,
    offset: int = 0,
    limit: int = 50,
):
    """List bank mutations with optional filters."""
    conditions: list[str] = []
    params: list = []
    if bank_account_id is not None:
        conditions.append("bm.bank_account_id = %s")
        params.append(bank_account_id)
    if date_from:
        conditions.append("bm.transaction_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("bm.transaction_date <= %s")
        params.append(date_to)
    if matched is not None:
        conditions.append("bm.matched = %s")
        params.append(matched)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT bm.*, ba.bank_name, ba.account_no
            FROM bank_mutation bm
            LEFT JOIN bank_account ba ON bm.bank_account_id = ba.id
            {where}
            ORDER BY bm.transaction_date DESC
            LIMIT %s OFFSET %s""",
        tuple(params),
    )
    return {"items": rows, "offset": offset, "limit": limit}


@router.post("/bank-mutation/{mutation_id}/match")
def match_mutation(mutation_id: int, req: MutationMatchRequest):
    """Match a bank mutation with a journal entry."""
    mutation = fetch_one(
        "SELECT * FROM bank_mutation WHERE id = %s", (mutation_id,)
    )
    if not mutation:
        raise HTTPException(404, "Bank mutation not found")
    if mutation.get("matched"):
        raise HTTPException(400, "Mutation already matched")
    journal = fetch_one(
        "SELECT * FROM journal_entry WHERE id = %s", (req.journal_entry_id,)
    )
    if not journal:
        raise HTTPException(404, "Journal entry not found")
    execute(
        """UPDATE bank_mutation
           SET matched = true, journal_entry_id = %s, matched_at = NOW()
           WHERE id = %s""",
        (req.journal_entry_id, mutation_id),
    )
    return {"status": "matched", "mutation_id": mutation_id, "journal_entry_id": req.journal_entry_id}


@router.post("/bank-mutation/auto-match")
def auto_match_mutations(req: AutoMatchRequest):
    """Auto-match bank mutations with journal entries by reference/amount/date."""
    conditions: list[str] = ["bm.matched = false"]
    params: list = []
    if req.bank_account_id is not None:
        conditions.append("bm.bank_account_id = %s")
        params.append(req.bank_account_id)
    if req.date_from:
        conditions.append("bm.transaction_date >= %s")
        params.append(req.date_from)
    if req.date_to:
        conditions.append("bm.transaction_date <= %s")
        params.append(req.date_to)
    where = " AND ".join(conditions)
    mutations = fetch_all(
        f"SELECT * FROM bank_mutation bm WHERE {where}", tuple(params)
    )
    matched_count = 0
    matched_ids: list[int] = []
    for m in mutations:
        # Try match by reference
        candidate = None
        if m.get("reference"):
            candidate = fetch_one(
                """SELECT id FROM journal_entry
                   WHERE doc_key = %s AND status = 'posted'
                   LIMIT 1""",
                (m["reference"],),
            )
        # Try match by amount + date
        if not candidate:
            candidate = fetch_one(
                """SELECT gl.journal_entry_id AS id
                   FROM general_ledger gl
                   JOIN journal_entry je ON gl.journal_entry_id = je.id
                   WHERE gl.amount = %s
                     AND je.entry_date = %s
                     AND je.status = 'posted'
                   LIMIT 1""",
                (abs(m["amount"]), m["transaction_date"]),
            )
        if candidate:
            execute(
                """UPDATE bank_mutation
                   SET matched = true, journal_entry_id = %s, matched_at = NOW()
                   WHERE id = %s""",
                (candidate["id"], m["id"]),
            )
            matched_count += 1
            matched_ids.append(m["id"])
    return {"total_checked": len(mutations), "matched": matched_count, "matched_ids": matched_ids}


# ── Reconciliation Endpoints ─────────────────────────────────────────────────


@router.post("/reconciliation/create")
def create_reconciliation(req: ReconciliationCreateRequest):
    """Create a bank reconciliation for a period."""
    existing = fetch_one(
        """SELECT id FROM bank_reconciliation
           WHERE bank_account_id = %s AND period_start = %s AND period_end = %s""",
        (req.bank_account_id, req.period_start, req.period_end),
    )
    if existing:
        raise HTTPException(400, "Reconciliation already exists for this period")
    row = execute_returning(
        """INSERT INTO bank_reconciliation
           (bank_account_id, period_start, period_end, opening_balance,
            closing_balance, status, created_at)
           VALUES (%s, %s, %s, %s, %s, 'open', NOW())
           RETURNING id""",
        (
            req.bank_account_id,
            req.period_start,
            req.period_end,
            req.opening_balance,
            req.closing_balance,
        ),
    )
    return {"id": row["id"], "status": "open"}


@router.get("/reconciliation/summary")
def list_reconciliations(
    bank_account_id: Optional[int] = None,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
):
    """List reconciliations."""
    conditions: list[str] = []
    params: list = []
    if bank_account_id is not None:
        conditions.append("br.bank_account_id = %s")
        params.append(bank_account_id)
    if status:
        conditions.append("br.status = %s")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT br.*, ba.bank_name, ba.account_no
            FROM bank_reconciliation br
            LEFT JOIN bank_account ba ON br.bank_account_id = ba.id
            {where}
            ORDER BY br.period DESC
            LIMIT %s OFFSET %s""",
        tuple(params),
    )
    return {"items": rows, "offset": offset, "limit": limit}


@router.get("/reconciliation/{recon_id}")
def get_reconciliation(recon_id: int):
    """Get reconciliation detail with matched and unmatched items."""
    recon = fetch_one(
        """SELECT br.*, ba.bank_name, ba.account_no
           FROM bank_reconciliation br
           LEFT JOIN bank_account ba ON br.bank_account_id = ba.id
           WHERE br.id = %s""",
        (recon_id,),
    )
    if not recon:
        raise HTTPException(404, "Reconciliation not found")
    matched = fetch_all(
        """SELECT bm.*, je.doc_key AS journal_doc_key
           FROM bank_mutation bm
           LEFT JOIN journal_entry je ON bm.journal_entry_id = je.id
           WHERE bm.bank_account_id = %s
             AND bm.transaction_date BETWEEN %s AND %s
             AND bm.matched = true
           ORDER BY bm.transaction_date""",
        (recon["bank_account_id"], recon["period_start"], recon["period_end"]),
    )
    unmatched = fetch_all(
        """SELECT * FROM bank_mutation
           WHERE bank_account_id = %s
             AND transaction_date BETWEEN %s AND %s
             AND matched = false
           ORDER BY transaction_date""",
        (recon["bank_account_id"], recon["period_start"], recon["period_end"]),
    )
    return {
        "reconciliation": recon,
        "matched_items": matched,
        "unmatched_items": unmatched,
        "summary": {
            "matched_count": len(matched),
            "unmatched_count": len(unmatched),
        },
    }


@router.post("/reconciliation/{recon_id}/close")
def close_reconciliation(recon_id: int, req: ReconciliationCloseRequest = ReconciliationCloseRequest()):
    """Close a reconciliation."""
    recon = fetch_one(
        "SELECT * FROM bank_reconciliation WHERE id = %s", (recon_id,)
    )
    if not recon:
        raise HTTPException(404, "Reconciliation not found")
    if recon.get("status") == "closed":
        raise HTTPException(400, "Reconciliation already closed")
    execute(
        """UPDATE bank_reconciliation
           SET status = 'closed', closed_by = %s, closed_at = NOW()
           WHERE id = %s""",
        (req.closed_by, recon_id),
    )
    return {"id": recon_id, "status": "closed"}
