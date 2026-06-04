"""Therapist Certification Router - Beauty & Shine POS-ERP V6.

Manage therapist certifications including expiry tracking.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/certification", tags=["Therapist Certification"])


# ── Request Models ────────────────────────────────────────────────────────────

class CertificationCreate(BaseModel):
    therapist_id: str
    cert_name: str
    issuer: str = ""
    cert_number: str = ""
    issued_date: Optional[str] = None   # YYYY-MM-DD
    expiry_date: Optional[str] = None   # YYYY-MM-DD


class CertificationUpdate(BaseModel):
    cert_name: Optional[str] = None
    issuer: Optional[str] = None
    cert_number: Optional[str] = None
    issued_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def list_certifications(
    therapist_id: str = "",
    status: str = "",
):
    """List certifications with optional filters."""
    conditions = []
    params: list = []
    if therapist_id:
        conditions.append("c.therapist_id = %s")
        params.append(therapist_id)
    if status:
        conditions.append("c.status = %s")
        params.append(status)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(500)

    rows = fetch_all(
        f"""SELECT c.*, u.full_name AS therapist_name
            FROM therapist_certification c
            LEFT JOIN app_user u ON u.id = c.therapist_id
            {where}
            ORDER BY c.expiry_date DESC NULLS LAST
            LIMIT %s""",
        tuple(params),
    )
    return {"items": rows}


@router.post("")
def create_certification(req: CertificationCreate):
    """Add a new certification for a therapist."""
    row = execute_returning(
        """INSERT INTO therapist_certification
               (therapist_id, cert_name, issuer, cert_number, issued_date, expiry_date, status, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
           RETURNING *""",
        (req.therapist_id, req.cert_name, req.issuer, req.cert_number,
         req.issued_date, req.expiry_date),
    )
    return row


@router.put("/{cert_id}")
def update_certification(cert_id: str, req: CertificationUpdate):
    """Update an existing certification."""
    existing = fetch_one("SELECT * FROM therapist_certification WHERE id=%s", (cert_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Certification not found")

    fields = []
    params: list = []
    for field_name, value in [
        ("cert_name", req.cert_name),
        ("issuer", req.issuer),
        ("cert_number", req.cert_number),
        ("issued_date", req.issued_date),
        ("expiry_date", req.expiry_date),
        ("status", req.status),
    ]:
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields.append("updated_at = NOW()")
    params.append(cert_id)

    row = execute_returning(
        f"UPDATE therapist_certification SET {', '.join(fields)} WHERE id=%s RETURNING *",
        tuple(params),
    )
    return row


@router.get("/expiring")
def list_expiring_certifications(
    days: int = Query(30, ge=1, le=365, description="Certifications expiring within N days"),
    therapist_id: str = "",
):
    """List certifications expiring within the given number of days."""
    conditions = [
        "c.expiry_date IS NOT NULL",
        "c.expiry_date <= CURRENT_DATE + make_interval(days => %s)",
        "c.expiry_date >= CURRENT_DATE",
    ]
    params: list = [days]

    if therapist_id:
        conditions.append("c.therapist_id = %s")
        params.append(therapist_id)

    where = "WHERE " + " AND ".join(conditions)
    params.append(200)

    rows = fetch_all(
        f"""SELECT c.*, u.full_name AS therapist_name,
                   (c.expiry_date - CURRENT_DATE)::int AS days_remaining
            FROM therapist_certification c
            LEFT JOIN app_user u ON u.id = c.therapist_id
            {where}
            ORDER BY c.expiry_date ASC
            LIMIT %s""",
        tuple(params),
    )
    return {"items": rows, "days_threshold": days}
