"""Therapist Work Schedule Router - Beauty & Shine POS-ERP V6.

Manage therapist work schedules per branch with shift times,
bulk creation, and availability checking.
"""
from __future__ import annotations

from datetime import date, time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/schedule", tags=["Therapist Schedule"])


# ── Request Models ────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    therapist_id: str
    branch_id: str
    schedule_date: str  # YYYY-MM-DD
    shift_start: str    # HH:MM
    shift_end: str      # HH:MM


class ScheduleUpdate(BaseModel):
    branch_id: Optional[str] = None
    schedule_date: Optional[str] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None


class BulkScheduleItem(BaseModel):
    therapist_id: str
    branch_id: str
    schedule_date: str
    shift_start: str
    shift_end: str


class BulkScheduleCreate(BaseModel):
    schedules: list[BulkScheduleItem]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def list_schedules(
    therapist_id: str = "",
    branch_id: str = "",
    date_from: str = "",
    date_to: str = "",
):
    """List schedules with optional filters."""
    conditions = []
    params: list = []
    if therapist_id:
        conditions.append("s.therapist_id = %s")
        params.append(therapist_id)
    if branch_id:
        conditions.append("s.branch_id = %s")
        params.append(branch_id)
    if date_from:
        conditions.append("s.schedule_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("s.schedule_date <= %s")
        params.append(date_to)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(500)

    rows = fetch_all(
        f"""SELECT s.*, u.full_name AS therapist_name
            FROM therapist_schedule s
            LEFT JOIN app_user u ON u.id = s.therapist_id
            {where}
            ORDER BY s.schedule_date DESC, s.shift_start
            LIMIT %s""",
        tuple(params),
    )
    return {"items": rows}


@router.post("")
def create_schedule(req: ScheduleCreate):
    """Create a single schedule entry."""
    existing = fetch_one(
        """SELECT id FROM therapist_schedule
           WHERE therapist_id=%s AND branch_id=%s AND schedule_date=%s""",
        (req.therapist_id, req.branch_id, req.schedule_date),
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Schedule already exists for this therapist, branch, and date",
        )

    row = execute_returning(
        """INSERT INTO therapist_schedule
               (therapist_id, branch_id, schedule_date, shift_start, shift_end, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
           RETURNING *""",
        (req.therapist_id, req.branch_id, req.schedule_date, req.shift_start, req.shift_end),
    )
    return row


@router.put("/{schedule_id}")
def update_schedule(schedule_id: str, req: ScheduleUpdate):
    """Update an existing schedule entry."""
    existing = fetch_one("SELECT * FROM therapist_schedule WHERE id=%s", (schedule_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    fields = []
    params: list = []
    for field_name, value in [
        ("branch_id", req.branch_id),
        ("schedule_date", req.schedule_date),
        ("shift_start", req.shift_start),
        ("shift_end", req.shift_end),
    ]:
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields.append("updated_at = NOW()")
    params.append(schedule_id)

    row = execute_returning(
        f"UPDATE therapist_schedule SET {', '.join(fields)} WHERE id=%s RETURNING *",
        tuple(params),
    )
    return row


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: str):
    """Delete a schedule entry."""
    existing = fetch_one("SELECT id FROM therapist_schedule WHERE id=%s", (schedule_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule not found")

    execute("DELETE FROM therapist_schedule WHERE id=%s", (schedule_id,))
    return {"message": "Schedule deleted", "id": schedule_id}


@router.post("/bulk")
def bulk_create_schedules(req: BulkScheduleCreate):
    """Bulk create schedule entries for multiple dates/therapists."""
    created = []
    skipped = []
    for item in req.schedules:
        exists = fetch_one(
            """SELECT id FROM therapist_schedule
               WHERE therapist_id=%s AND branch_id=%s AND schedule_date=%s""",
            (item.therapist_id, item.branch_id, item.schedule_date),
        )
        if exists:
            skipped.append(
                {"therapist_id": item.therapist_id, "schedule_date": item.schedule_date, "reason": "already exists"}
            )
            continue
        row = execute_returning(
            """INSERT INTO therapist_schedule
                   (therapist_id, branch_id, schedule_date, shift_start, shift_end, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
               RETURNING *""",
            (item.therapist_id, item.branch_id, item.schedule_date, item.shift_start, item.shift_end),
        )
        created.append(row)

    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "created": created,
        "skipped": skipped,
    }


@router.get("/availability")
def check_availability(
    branch_id: str = Query(...),
    check_date: str = Query(..., description="YYYY-MM-DD"),
    check_time: str = Query("", description="HH:MM — filter therapists whose shift covers this time"),
):
    """Check which therapists are available at a given branch/date/time."""
    if check_time:
        rows = fetch_all(
            """SELECT s.*, u.full_name AS therapist_name
               FROM therapist_schedule s
               LEFT JOIN app_user u ON u.id = s.therapist_id
               WHERE s.branch_id = %s
                 AND s.schedule_date = %s
                 AND s.shift_start <= %s
                 AND s.shift_end > %s
               ORDER BY u.full_name""",
            (branch_id, check_date, check_time, check_time),
        )
    else:
        rows = fetch_all(
            """SELECT s.*, u.full_name AS therapist_name
               FROM therapist_schedule s
               LEFT JOIN app_user u ON u.id = s.therapist_id
               WHERE s.branch_id = %s
                 AND s.schedule_date = %s
               ORDER BY u.full_name""",
            (branch_id, check_date),
        )
    return {"available_therapists": rows}
