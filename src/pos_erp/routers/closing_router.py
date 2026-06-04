"""Daily Closing API router.

Database-backed daily closing with reconciliation logic.
Combines the POS closing persistence with variance checking.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from pos_erp.audit_log import AuditLog, AuditSeverity
from pos_erp.db import fetch_all, fetch_one, get_conn, execute
from pos_erp.reconciliation import (
    ClosingDecision,
    ClosingStatus,
    ReconciliationPolicy,
    evaluate_shift_closing,
)

router = APIRouter(prefix="/api/daily-closing", tags=["Daily Closing"])

_audit_log = AuditLog()


def _get_branch_id(branch_code: str) -> str | None:
    """Resolve branch_code (name or UUID) to UUID."""
    if not branch_code:
        return None
    # Try UUID first
    row = fetch_one("SELECT id FROM branch WHERE id::text = %s", (branch_code,))
    if row:
        return str(row["id"])
    # Try by name
    row = fetch_one("SELECT id FROM branch WHERE name ILIKE %s", (f"%{branch_code}%",))
    if row:
        return str(row["id"])
    return None


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/summary")
async def closing_summary(
    date: str = Query("", alias="date", description="Tanggal (YYYY-MM-DD)"),
    branchCode: str = Query("", alias="branchCode", description="Kode/ID cabang"),
    business_date: str = Query("", alias="business_date"),
    branch_code: str = Query("", alias="branch_code"),
    branch_id: str = Query("", alias="branch_id"),
):
    """Ringkasan closing harian dari database.
    Mengembalikan breakdown per metode bayar, total transaksi, expected cash.
    """
    # Use CURRENT_DATE from PostgreSQL (timezone=Asia/Jakarta) as default
    # This avoids frontend UTC vs backend WIB timezone mismatch
    branch_name = branchCode or branch_code or ""

    # Resolve branch_id — prefer explicit branch_id param, then branchCode
    resolved_branch_id = None
    if branch_id:
        resolved_branch_id = _get_branch_id(branch_id)
    if not resolved_branch_id and branch_name:
        resolved_branch_id = _get_branch_id(branch_name)

    # Build query — use CURRENT_DATE if no date provided (matches PostgreSQL timezone)
    if date or business_date:
        closing_date = date or business_date
        conditions = ["t.status = 'paid'", "DATE(t.created_at) = %s"]
        params: list = [closing_date]
    else:
        conditions = ["t.status = 'paid'", "DATE(t.created_at) = CURRENT_DATE"]
        params: list = []
    if resolved_branch_id:
        conditions.append("t.branch_id = %s")
        params.append(resolved_branch_id)
    where = " AND ".join(conditions)

    # Get paid transactions for the day
    txns = fetch_all(
        f"""SELECT t.total, t.payment_method_id, pm.type AS payment_type, pm.name AS payment_name
            FROM pos_transaction t
            LEFT JOIN payment_method pm ON t.payment_method_id = pm.id
            WHERE {where}""",
        tuple(params),
    )

    total_transactions = len(txns)
    total_nominal = sum(float(t["total"]) for t in txns)

    # Breakdown by payment method
    cash_total = 0.0
    qris_total = 0.0
    transfer_total = 0.0
    other_total = 0.0

    for t in txns:
        ptype = (t.get("payment_type") or "").lower()
        pname = (t.get("payment_name") or "").lower()
        amount = float(t["total"])
        if "cash" in ptype or "tunai" in pname:
            cash_total += amount
        elif "qris" in ptype or "qris" in pname:
            qris_total += amount
        elif "transfer" in ptype or "bank" in ptype:
            transfer_total += amount
        else:
            other_total += amount

    # Check for unposted (open) transactions — use same date logic as main query
    if date or business_date:
        open_conds = ["t.status = 'open'", "DATE(t.created_at) = %s"]
        open_params: list = [closing_date]
    else:
        open_conds = ["t.status = 'open'", "DATE(t.created_at) = CURRENT_DATE"]
        open_params: list = []
    if resolved_branch_id:
        open_conds.append("t.branch_id = %s")
        open_params.append(resolved_branch_id)
    open_where = " AND ".join(open_conds)
    open_count = fetch_one(f"SELECT COUNT(*) AS cnt FROM pos_transaction t WHERE {open_where}", tuple(open_params))

    # Check if closing already exists for this date
    if date or business_date:
        existing_conds = ["c.closing_date = %s"]
        existing_params: list = [closing_date]
    else:
        existing_conds = ["c.closing_date = CURRENT_DATE"]
        existing_params: list = []
    if resolved_branch_id:
        existing_conds.append("c.branch_id = %s")
        existing_params.append(resolved_branch_id)
    existing_where = " AND ".join(existing_conds)
    existing = fetch_one(
        f"SELECT id, status FROM pos_daily_closing c WHERE {existing_where}",
        tuple(existing_params),
    )

    # For the response, get the actual date (either from param or current WIB date)
    from datetime import timezone, timedelta
    wib = timezone(timedelta(hours=7))
    response_date = closing_date if (date or business_date) else datetime.datetime.now(wib).date().isoformat()

    return {
        "date": response_date,
        "branchCode": branch_name,
        "totalTransactions": total_transactions,
        "totalNominal": total_nominal,
        "byMethod": {
            "cash": cash_total,
            "qris": qris_total,
            "bankTransfer": transfer_total,
            "other": other_total,
        },
        "cashExpected": cash_total,
        "unpostedCount": open_count["cnt"] if open_count else 0,
        "openExceptionCount": 0,
        "alreadyClosed": existing["status"] == "submitted" if existing else False,
        "closingId": str(existing["id"]) if existing else None,
    }


@router.post("/submit")
async def submit_closing(data: dict):
    """Submit closing harian dengan reconciliation.
    Persist ke database + variance check.
    """
    from datetime import timezone, timedelta
    wib = timezone(timedelta(hours=7))
    closing_date = data.get("date") or datetime.datetime.now(wib).date().isoformat()
    branch_name = data.get("branchCode") or data.get("branch_code") or ""
    cash_counted = float(data.get("cashCounted") or data.get("cash_counted") or 0)
    manager_id = data.get("managerId") or data.get("manager_id") or ""
    manager_name = data.get("managerName") or data.get("manager_name") or ""
    variance_reason = data.get("varianceReason") or ""
    variance_note = data.get("varianceNote") or ""

    branch_id = _get_branch_id(branch_name) if branch_name else None

    # Look up branch short code (e.g. "BSD") for document_registry (varchar(10))
    branch_short_code = "ALL"
    if branch_id:
        bc_row = fetch_one("SELECT code FROM branch WHERE id = %s", (branch_id,))
        if bc_row and bc_row.get("code"):
            branch_short_code = bc_row["code"]
    elif branch_name and len(branch_name) <= 10:
        branch_short_code = branch_name

    # Get actual sales from DB
    conditions = ["t.status = 'paid'", "DATE(t.created_at) = %s"]
    params: list = [closing_date]
    if branch_id:
        conditions.append("t.branch_id = %s")
        params.append(branch_id)
    where = " AND ".join(conditions)

    txns = fetch_all(
        f"""SELECT t.id, t.total, pm.type AS payment_type, pm.name AS payment_name
            FROM pos_transaction t
            LEFT JOIN payment_method pm ON t.payment_method_id = pm.id
            WHERE {where}""",
        tuple(params),
    )

    cash_expected = 0.0
    for t in txns:
        ptype = (t.get("payment_type") or "").lower()
        pname = (t.get("payment_name") or "").lower()
        if "cash" in ptype or "tunai" in pname:
            cash_expected += float(t["total"])

    operational_sales = Decimal(str(cash_expected))
    counted_cash = Decimal(str(cash_counted))

    # Reconciliation check
    policy = ReconciliationPolicy()
    decision = evaluate_shift_closing(
        operational_sales=operational_sales,
        counted_cash=counted_cash,
        pending_queued_transactions=0,
        policy=policy,
    )

    # If blocked, return error
    if decision.status is ClosingStatus.BLOCKED:
        return JSONResponse(
            status_code=409,
            content={
                "error": "CLOSING_BLOCKED",
                "message": f"Closing diblokir: selisih Rp {decision.variance_amount:,.0f} ({decision.variance_percent}%) melebihi batas toleransi",
                "variance_amount": float(decision.variance_amount),
                "variance_percent": float(decision.variance_percent),
                "reason_code": decision.reason_code,
            },
        )

    # Check if already closed
    existing_conds = ["c.closing_date = %s"]
    existing_params: list = [closing_date]
    if branch_id:
        existing_conds.append("c.branch_id = %s")
        existing_params.append(branch_id)
    existing_where = " AND ".join(existing_conds)
    existing = fetch_one(
        f"SELECT id FROM pos_daily_closing c WHERE {existing_where} AND c.status = 'submitted'",
        tuple(existing_params),
    )
    if existing:
        return JSONResponse(
            status_code=409,
            content={"error": "ALREADY_CLOSED", "message": f"Closing untuk tanggal {closing_date} sudah disubmit"},
        )

    # Generate doc key and register in document_registry
    seq = fetch_one("SELECT COALESCE(MAX(CAST(SUBSTRING(doc_key FROM 'CLO-\\d{8}-(\\d+)') AS INTEGER)), 0) + 1 AS next FROM pos_daily_closing WHERE doc_key LIKE 'CLO-%%'")
    next_num = (seq or {}).get("next", 1)
    doc_key = f"CLO-{closing_date.replace('-', '')}-{next_num:04d}"

    # Register in document_registry (FK requirement)
    execute(
        "INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (doc_key) DO NOTHING",
        (doc_key, "CLO", branch_short_code, closing_date, next_num),
    )

    # Get total nominal
    total_nominal = sum(float(t["total"]) for t in txns)

    # Breakdown by payment type
    total_cash = sum(float(t["total"]) for t in txns if "cash" in (t.get("payment_type") or "").lower() or "tunai" in (t.get("payment_name") or "").lower())
    total_card = sum(float(t["total"]) for t in txns if "card" in (t.get("payment_type") or "").lower())
    total_transfer = sum(float(t["total"]) for t in txns if "transfer" in (t.get("payment_type") or "").lower() or "bank" in (t.get("payment_type") or "").lower())
    total_other = total_nominal - total_cash - total_card - total_transfer

    # Insert to database
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pos_daily_closing
                   (doc_key, branch_id, closing_date, total_cash, total_card, total_transfer, total_other,
                    total_transactions, status, closed_by, closed_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'submitted', %s, NOW())
                   RETURNING *""",
                (doc_key, branch_id, closing_date, total_cash, total_card, total_transfer, total_other,
                 len(txns), None),
            )
            closing = cur.fetchone()

            # Insert detail records
            for txn in txns:
                cur.execute(
                    "INSERT INTO pos_daily_closing_detail (closing_id, transaction_id, amount) VALUES (%s, %s, %s)",
                    (closing["id"], txn["id"], txn["total"]),
                )

    # Audit log
    _audit_log.record(
        action="CLOSING_SUBMITTED",
        actor_id=manager_id or "system",
        branch_code=branch_name,
        device_id="POS",
        reference_id=doc_key,
        severity=AuditSeverity.INFO,
        metadata={
            "closing_date": closing_date,
            "total_transactions": len(txns),
            "total_nominal": total_nominal,
            "cash_counted": cash_counted,
            "cash_expected": cash_expected,
            "variance_amount": float(decision.variance_amount),
            "status": decision.status.value,
        },
    )

    return {
        "id": str(closing["id"]),
        "closing_id": str(closing["id"]),
        "doc_key": doc_key,
        "date": closing_date,
        "branchCode": branch_name,
        "totalTransactions": len(txns),
        "totalNominal": total_nominal,
        "cashExpected": cash_expected,
        "cashCounted": cash_counted,
        "variance": float(decision.variance_amount),
        "variancePercent": float(decision.variance_percent),
        "status": decision.status.value,
        "managerName": manager_name,
        "message": f"Closing berhasil. Report: {doc_key}",
    }


@router.get("/report/{report_id}")
async def get_closing_report(report_id: str):
    """Ambil laporan closing dari database."""
    closing = fetch_one(
        """SELECT c.*, b.name as branch_name
           FROM pos_daily_closing c
           LEFT JOIN branch b ON c.branch_id = b.id
           WHERE c.id::text = %s OR c.doc_key = %s""",
        (report_id, report_id),
    )
    if not closing:
        return JSONResponse(status_code=404, content={"error": "NOT_FOUND", "message": "Laporan closing tidak ditemukan"})

    details = fetch_all(
        "SELECT d.*, t.doc_key, t.customer_name FROM pos_daily_closing_detail d JOIN pos_transaction t ON d.transaction_id = t.id WHERE d.closing_id = %s",
        (closing["id"],),
    )

    return {
        "id": str(closing["id"]),
        "doc_key": closing["doc_key"],
        "date": str(closing["closing_date"]),
        "branchCode": closing.get("branch_name", ""),
        "totalTransactions": closing["total_transactions"],
        "totalNominal": float(closing["total_cash"]) + float(closing["total_card"]) + float(closing["total_transfer"]) + float(closing["total_other"]),
        "byMethod": {
            "cash": float(closing["total_cash"]),
            "card": float(closing["total_card"]),
            "bankTransfer": float(closing["total_transfer"]),
            "other": float(closing["total_other"]),
        },
        "status": closing["status"],
        "closedBy": closing.get("closed_by", ""),
        "closedAt": str(closing.get("closed_at", "")),
        "details": [
            {"doc_key": d["doc_key"], "customer_name": d["customer_name"], "amount": float(d["amount"])}
            for d in details
        ],
    }


@router.get("/history")
async def closing_history(
    branchCode: str = Query(""),
    branch_code: str = Query(""),
    limit: int = Query(10),
):
    """Riwayat closing dari database."""
    branch_name = branchCode or branch_code
    branch_id = _get_branch_id(branch_name) if branch_name else None

    extra = "WHERE c.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()

    rows = fetch_all(
        f"""SELECT c.*, b.name as branch_name
            FROM pos_daily_closing c
            LEFT JOIN branch b ON c.branch_id = b.id
            {extra}
            ORDER BY c.closing_date DESC
            LIMIT %s""",
        (*params, limit),
    )

    return [
        {
            "id": str(r["id"]),
            "date": str(r["closing_date"]),
            "totalTransactions": r["total_transactions"],
            "totalNominal": float(r["total_cash"]) + float(r["total_card"]) + float(r["total_transfer"]) + float(r["total_other"]),
            "cashExpected": float(r["total_cash"]),
            "cashCounted": float(r["total_cash"]),  # stored amount
            "variance": 0,
            "closedAt": str(r.get("closed_at", "")),
            "managerName": r.get("closed_by", "-"),
            "status": r["status"],
        }
        for r in rows
    ]
