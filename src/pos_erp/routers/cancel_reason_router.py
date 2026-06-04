"""Cancel Reason Router - Beauty & Shine POS-ERP V6.

Manage transaction cancel reasons and process cancellations with mandatory reason tracking.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/cancel-reason", tags=["Cancel Reason"])


# ── Request Models ────────────────────────────────────────────────────────────

class CancelReasonCreate(BaseModel):
    module: str = "POS"
    reason: str = ""


class CancelReasonUpdate(BaseModel):
    module: Optional[str] = None
    reason: Optional[str] = None
    is_active: Optional[bool] = None


class CancelWithReasonRequest(BaseModel):
    reason_id: str
    notes: str = ""


# ── Cancel Reason CRUD ────────────────────────────────────────────────────────

@router.get("/cancel-reason")
def list_cancel_reasons():
    """List all active cancel reasons."""
    rows = fetch_all(
        "SELECT * FROM cancel_reason WHERE is_active = TRUE ORDER BY module, reason"
    )
    return {"items": rows}


@router.post("/cancel-reason")
def create_cancel_reason(req: CancelReasonCreate):
    """Create a new cancel reason."""
    row = execute_returning(
        """INSERT INTO cancel_reason (module, reason, is_active)
           VALUES (%s, %s, TRUE)
           RETURNING *""",
        (req.module, req.reason),
    )
    return row


@router.put("/cancel-reason/{reason_id}")
def update_cancel_reason(reason_id: str, req: CancelReasonUpdate):
    """Update a cancel reason."""
    existing = fetch_one("SELECT * FROM cancel_reason WHERE id=%s", (reason_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Cancel reason not found")

    fields = []
    params: list = []
    for field_name, value in [
        ("module", req.module),
        ("reason", req.reason),
        ("is_active", req.is_active),
    ]:
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(reason_id)
    row = execute_returning(
        f"UPDATE cancel_reason SET {', '.join(fields)} WHERE id=%s RETURNING *",
        tuple(params),
    )
    return row


@router.delete("/cancel-reason/{reason_id}")
def delete_cancel_reason(reason_id: str):
    """Soft-delete a cancel reason."""
    row = execute_returning(
        "UPDATE cancel_reason SET is_active=FALSE WHERE id=%s RETURNING id",
        (reason_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Cancel reason not found")
    return {"deleted": True, "id": row["id"]}


@router.post("/pos/transaction/{transaction_id}/cancel-with-reason")
def cancel_transaction_with_reason(transaction_id: str, req: CancelWithReasonRequest):
    """Cancel a POS transaction with a mandatory reason."""
    reason = fetch_one("SELECT * FROM cancel_reason WHERE id=%s AND is_active=TRUE", (req.reason_id,))
    if not reason:
        raise HTTPException(status_code=404, detail="Cancel reason not found or inactive")

    txn = fetch_one("SELECT * FROM pos_transaction WHERE id=%s", (transaction_id,))
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn["status"] in ("cancelled", "voided"):
        raise HTTPException(status_code=400, detail="Transaction already cancelled")

    row = execute_returning(
        """UPDATE pos_transaction
           SET status='cancelled', cancel_reason_id=%s, cancel_notes=%s
           WHERE id=%s RETURNING *""",
        (req.reason_id, req.notes, transaction_id),
    )
    return row
