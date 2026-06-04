"""Period Lock & End of Period Router - Beauty & Shine ERP.

Handles:
- Financial period management
- Period locking/unlocking
- End of period checklist
- Period closing approval
- Correction via adjustment/reversal
"""
from __future__ import annotations

from datetime import date
import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.domain_models import DocumentKind, AuditAction
from pos_erp.repository import DocumentRegistryRepository, AuditTrailRepository
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

router = APIRouter(prefix="/api/period", tags=["Period & Closing"])

# ── Request Models ────────────────────────────────────────────────

class PeriodRequest(BaseModel):
    branch_id: str
    year: int
    month: int

class PeriodCloseRequest(BaseModel):
    period_id: str
    closed_by: str
    notes: Optional[str] = None

class PeriodUnlockRequest(BaseModel):
    period_id: str
    unlocked_by: str
    reason: str

class ChecklistItemRequest(BaseModel):
    closing_id: str
    check_name: str
    status: str = "pending"
    checked_by: Optional[str] = None


# ── Financial Period ──────────────────────────────────────────────

@router.get("/financial-periods")
def list_financial_periods(branch_id: str = ""):
    """List financial periods."""
    if branch_id:
        rows = fetch_all(
            "SELECT fp.*, b.name as branch_name FROM financial_period fp LEFT JOIN branch b ON fp.branch_id=b.id WHERE fp.branch_id=%s ORDER BY fp.year DESC, fp.month DESC",
            (branch_id,)
        )
    else:
        rows = fetch_all(
            "SELECT fp.*, b.name as branch_name FROM financial_period fp LEFT JOIN branch b ON fp.branch_id=b.id ORDER BY fp.year DESC, fp.month DESC"
        )
    import calendar
    for r in rows:
        y, m = r["year"], r["month"]
        r["name"] = f"{calendar.month_name[m]} {y}"
        _, last_day = calendar.monthrange(y, m)
        r["start_date"] = f"{y}-{m:02d}-01"
        r["end_date"] = f"{y}-{m:02d}-{last_day:02d}"
    return {"items": rows}

@router.post("/financial-period")
def create_financial_period(req: PeriodRequest):
    """Create a new financial period."""
    existing = fetch_one(
        "SELECT * FROM financial_period WHERE branch_id=%s AND year=%s AND month=%s",
        (req.branch_id, req.year, req.month)
    )
    if existing:
        raise HTTPException(400, "Period already exists")
    
    return execute_returning(
        """INSERT INTO financial_period (branch_id, year, month, status)
           VALUES (%s, %s, %s, 'open') RETURNING *""",
        (req.branch_id, req.year, req.month)
    )

@router.get("/financial-period/{id}")
def get_financial_period(id: str):
    """Get financial period details."""
    period = fetch_one(
        "SELECT fp.*, b.name as branch_name FROM financial_period fp LEFT JOIN branch b ON fp.branch_id=b.id WHERE fp.id=%s",
        (id,)
    )
    if not period:
        raise HTTPException(404, "Period not found")
    return period


# ── Period Lock ───────────────────────────────────────────────────

@router.put("/financial-period/{id}/lock")
def lock_period(id: str, locked_by: str = ""):
    """Lock a financial period."""
    period = fetch_one("SELECT * FROM financial_period WHERE id = %s", (id,))
    if not period:
        raise HTTPException(404, "Period not found")
    if period["status"] == "locked":
        raise HTTPException(400, "Period already locked")
    
    execute(
        "UPDATE financial_period SET status='locked', closed_at=NOW(), closed_by=%s WHERE id=%s",
        (locked_by or None, id)
    )
    
    AuditTrailRepository.record(
        doc_key=f"PERIOD-{period['year']}-{period['month']:02d}",
        module="period",
        action="lock",
        user_id=locked_by,
        new_value=f"Period {period['year']}-{period['month']:02d} locked",
    )
    
    return fetch_one("SELECT * FROM financial_period WHERE id=%s", (id,))

@router.put("/financial-period/{id}/unlock")
def unlock_period(id: str, req: PeriodUnlockRequest):
    """Unlock a financial period (requires reason)."""
    period = fetch_one("SELECT * FROM financial_period WHERE id = %s", (id,))
    if not period:
        raise HTTPException(404, "Period not found")
    if period["status"] != "locked":
        raise HTTPException(400, "Period is not locked")
    if not req.reason:
        raise HTTPException(400, "Reason required for unlocking")
    
    execute(
        "UPDATE financial_period SET status='open', closed_at=NULL, closed_by=NULL WHERE id=%s",
        (id,)
    )
    
    AuditTrailRepository.record(
        doc_key=f"PERIOD-{period['year']}-{period['month']:02d}",
        module="period",
        action="unlock",
        user_id=req.unlocked_by,
        new_value=f"Period unlocked. Reason: {req.reason}",
    )
    
    return fetch_one("SELECT * FROM financial_period WHERE id=%s", (id,))


# ── Period Closing ────────────────────────────────────────────────

@router.get("/closings")
def list_period_closings(branch_id: str = ""):
    """List period closings with checklist."""
    if branch_id:
        rows = fetch_all(
            "SELECT pc.*, b.name as branch_name FROM period_closing pc LEFT JOIN branch b ON pc.branch_id=b.id WHERE pc.branch_id=%s ORDER BY pc.period DESC",
            (branch_id,)
        )
    else:
        rows = fetch_all(
            "SELECT pc.*, b.name as branch_name FROM period_closing pc LEFT JOIN branch b ON pc.branch_id=b.id ORDER BY pc.period DESC"
        )
    for r in rows:
        checklist = fetch_all(
            "SELECT check_name as item, CASE WHEN status='completed' THEN true ELSE false END as completed FROM period_closing_checklist WHERE closing_id=%s ORDER BY created_at",
            (r["id"],)
        )
        r["checklist"] = checklist
    return {"items": rows}

@router.post("/closing")
def create_period_closing(branch_id: str = "", period: str = ""):
    """Create a period closing with checklist."""
    if not period:
        now = datetime.datetime.now()
        period = f"{now.year}-{now.month:02d}"
    
    doc_key = DocumentRegistryRepository.generate_doc_key(DocumentKind.EOP.value)
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO period_closing (branch_id, period, status)
                   VALUES (%s, %s, 'draft') RETURNING *""",
                (branch_id, period)
            )
            closing = cur.fetchone()
            
            # Create checklist items
            checklist_items = [
                "Verifikasi semua transaksi POS tercatat",
                "Verifikasi stock opname selesai",
                "Verifikasi journal entry sudah di-post",
                "Verifikasi bank reconciliation selesai",
                "Verifikasi AP sudah di-reconcile",
                "Verifikasi aset sudah di-depreciate",
                "Verifikasi laporan penjualan akurat",
                "Verifikasi laporan inventory akurat",
                "Verifikasi laporan keuangan akurat",
                "Owner approval",
            ]
            for item_name in checklist_items:
                cur.execute(
                    """INSERT INTO period_closing_checklist (closing_id, check_name, status)
                       VALUES (%s, %s, 'pending')""",
                    (closing["id"], item_name)
                )
    
    AuditTrailRepository.record(
        doc_key=doc_key,
        module="period",
        action="create",
        new_value=f"Period closing created for {period}",
    )
    
    return closing

@router.get("/closing/{id}")
def get_period_closing(id: str):
    """Get period closing with checklist."""
    closing = fetch_one(
        "SELECT pc.*, b.name as branch_name FROM period_closing pc LEFT JOIN branch b ON pc.branch_id=b.id WHERE pc.id=%s",
        (id,)
    )
    if not closing:
        raise HTTPException(404, "Period closing not found")
    
    closing["checklist"] = fetch_all(
        "SELECT * FROM period_closing_checklist WHERE closing_id=%s ORDER BY created_at",
        (id,)
    )
    return closing

@router.put("/closing/{id}/checklist")
def update_checklist_item(id: str, req: ChecklistItemRequest):
    """Update checklist item status."""
    item = fetch_one(
        "SELECT * FROM period_closing_checklist WHERE closing_id=%s AND check_name=%s",
        (id, req.check_name)
    )
    if not item:
        raise HTTPException(404, "Checklist item not found")
    
    execute(
        "UPDATE period_closing_checklist SET status=%s, checked_by=%s, checked_at=NOW() WHERE id=%s",
        (req.status, req.checked_by, item["id"])
    )
    
    return fetch_one("SELECT * FROM period_closing_checklist WHERE id=%s", (item["id"],))

@router.put("/closing/{id}/review")
def review_period_closing(id: str, reviewed_by: str = ""):
    """Review period closing (all checklist items must be completed)."""
    closing = fetch_one("SELECT * FROM period_closing WHERE id = %s", (id,))
    if not closing:
        raise HTTPException(404, "Period closing not found")
    
    pending = fetch_one(
        "SELECT count(*) as count FROM period_closing_checklist WHERE closing_id=%s AND status='pending'",
        (id,)
    )
    if pending and pending["count"] > 0:
        raise HTTPException(400, f"{pending['count']} checklist items still pending")
    
    execute(
        "UPDATE period_closing SET status='reviewed', reviewed_by=%s, reviewed_at=NOW() WHERE id=%s",
        (reviewed_by or None, id)
    )
    
    return fetch_one("SELECT * FROM period_closing WHERE id=%s", (id,))

@router.put("/closing/{id}/close")
def close_period(id: str, closed_by: str = ""):
    """Close the period (final step)."""
    closing = fetch_one("SELECT * FROM period_closing WHERE id = %s", (id,))
    if not closing:
        raise HTTPException(404, "Period closing not found")
    if closing["status"] != "reviewed":
        raise HTTPException(400, "Period must be reviewed before closing")
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Close the period
            cur.execute(
                "UPDATE period_closing SET status='closed', closed_by=%s, closed_at=NOW() WHERE id=%s",
                (closed_by or None, id)
            )
            
            # Lock the financial period
            cur.execute(
                "UPDATE financial_period SET status='locked', closed_at=NOW(), closed_by=%s WHERE branch_id=%s AND year||'-'||LPAD(month::text,2,'0')=%s",
                (closed_by or None, closing["branch_id"], closing["period"])
            )
    
    AuditTrailRepository.record(
        doc_key=f"EOP-{closing['period']}",
        module="period",
        action="close",
        user_id=closed_by,
        new_value=f"Period {closing['period']} closed",
    )
    
    return fetch_one("SELECT * FROM period_closing WHERE id=%s", (id,))


# ── Period Status Check ───────────────────────────────────────────

@router.get("/status")
def get_period_status(branch_id: str = "", year: int = 0, month: int = 0):
    """Check if a period is locked."""
    if not year or not month:
        now = datetime.datetime.now()
        year, month = now.year, now.month
    
    if branch_id:
        period = fetch_one(
            "SELECT * FROM financial_period WHERE branch_id=%s AND year=%s AND month=%s",
            (branch_id, year, month)
        )
    else:
        period = fetch_one(
            "SELECT * FROM financial_period WHERE year=%s AND month=%s LIMIT 1",
            (year, month)
        )
    
    if not period:
        return {"exists": False, "status": "unknown", "is_locked": False, "current_period": f"{year}-{month:02d}", "days_remaining": 0}

    import calendar
    _, last_day = calendar.monthrange(year, month)
    today = datetime.date.today()
    end_date = datetime.date(year, month, last_day)
    days_remaining = max(0, (end_date - today).days)

    return {
        "exists": True,
        "status": period["status"],
        "is_locked": period["status"] == "locked",
        "closed_at": period.get("closed_at"),
        "closed_by": period.get("closed_by"),
        "current_period": f"{year}-{month:02d}",
        "days_remaining": days_remaining,
    }

@router.get("/check-transaction")
def check_transaction_allowed(branch_id: str = "", transaction_date: str = ""):
    """Check if a transaction is allowed for a given date."""
    if not transaction_date:
        return {"allowed": True, "reason": "No date specified"}
    
    try:
        dt = datetime.datetime.strptime(transaction_date, "%Y-%m-%d")
        year, month = dt.year, dt.month
    except ValueError:
        return {"allowed": False, "reason": "Invalid date format"}
    
    period = fetch_one(
        "SELECT * FROM financial_period WHERE branch_id=%s AND year=%s AND month=%s",
        (branch_id, year, month)
    )
    
    if not period:
        return {"allowed": True, "reason": "Period not found (auto-create)"}
    
    if period["status"] == "locked":
        return {
            "allowed": False,
            "reason": "Period is locked",
            "period_id": period["id"],
            "period_status": period["status"],
        }
    
    return {"allowed": True, "period_status": period["status"]}
