"""Cost Center Router - Beauty & Shine POS-ERP V6."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/cost-center", tags=["Cost Center"])


# ── Pydantic Models ──────────────────────────────────────────────────────────


class CostCenterCreate(BaseModel):
    code: str
    name: str
    branch_id: Optional[int] = None
    description: Optional[str] = None


class CostCenterUpdate(BaseModel):
    name: Optional[str] = None
    branch_id: Optional[int] = None
    description: Optional[str] = None


# ── CRUD Endpoints ───────────────────────────────────────────────────────────


@router.get("/cost_center")
def list_cost_centers(
    branch_id: Optional[int] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
):
    """List cost centers."""
    conditions: list[str] = []
    params: list = []
    if branch_id is not None:
        conditions.append("cc.branch_id = %s")
        params.append(branch_id)
    if search:
        conditions.append("(cc.code ILIKE %s OR cc.name ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT cc.*, b.name AS branch_name
            FROM cost_center cc
            LEFT JOIN branch b ON cc.branch_id = b.id
            {where}
            ORDER BY cc.code
            LIMIT %s OFFSET %s""",
        tuple(params),
    )
    return {"items": rows, "offset": offset, "limit": limit}


@router.post("/cost_center")
def create_cost_center(req: CostCenterCreate):
    """Create a new cost center."""
    existing = fetch_one(
        "SELECT id FROM cost_center WHERE code = %s", (req.code,)
    )
    if existing:
        raise HTTPException(400, f"Cost center code '{req.code}' already exists")
    row = execute_returning(
        """INSERT INTO cost_center (code, name, branch_id, description, created_at)
           VALUES (%s, %s, %s, %s, NOW())
           RETURNING id""",
        (req.code, req.name, req.branch_id, req.description),
    )
    return {"id": row["id"], "code": req.code}


@router.put("/cost_center/{cost_center_id}")
def update_cost_center(cost_center_id: int, req: CostCenterUpdate):
    """Update a cost center."""
    existing = fetch_one(
        "SELECT * FROM cost_center WHERE id = %s", (cost_center_id,)
    )
    if not existing:
        raise HTTPException(404, "Cost center not found")
    fields: list[str] = []
    params: list = []
    if req.name is not None:
        fields.append("name = %s")
        params.append(req.name)
    if req.branch_id is not None:
        fields.append("branch_id = %s")
        params.append(req.branch_id)
    if req.description is not None:
        fields.append("description = %s")
        params.append(req.description)
    if not fields:
        raise HTTPException(400, "No fields to update")
    params.append(cost_center_id)
    execute(
        f"UPDATE cost_center SET {', '.join(fields)} WHERE id = %s",
        tuple(params),
    )
    return {"id": cost_center_id, "status": "updated"}


@router.get("/cost_center/{cost_center_id}")
def get_cost_center(cost_center_id: int):
    """Get a single cost center."""
    row = fetch_one(
        """SELECT cc.*, b.name AS branch_name
           FROM cost_center cc
           LEFT JOIN branch b ON cc.branch_id = b.id
           WHERE cc.id = %s""",
        (cost_center_id,),
    )
    if not row:
        raise HTTPException(404, "Cost center not found")
    return row


# ── Summary & Transactions ───────────────────────────────────────────────────


@router.get("/cost-center/summary")
def cost_center_summary(branch_id: Optional[int] = None):
    """Cost center summary with total debit/credit from general ledger."""
    conditions: list[str] = []
    params: list = []
    if branch_id is not None:
        conditions.append("cc.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = fetch_all(
        f"""SELECT cc.id, cc.code, cc.name, cc.branch_id,
                   COALESCE(SUM(gl.debit), 0) AS total_debit,
                   COALESCE(SUM(gl.credit), 0) AS total_credit,
                   COALESCE(SUM(gl.debit), 0) - COALESCE(SUM(gl.credit), 0) AS balance
            FROM cost_center cc
            LEFT JOIN general_ledger gl ON gl.cost_center_id = cc.id
            {where}
            GROUP BY cc.id, cc.code, cc.name, cc.branch_id
            ORDER BY cc.code""",
        tuple(params),
    )
    return {"items": rows}


@router.get("/cost-center/{cost_center_id}/transactions")
def cost_center_transactions(
    cost_center_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
):
    """Get GL transactions for a cost center."""
    cc = fetch_one("SELECT * FROM cost_center WHERE id = %s", (cost_center_id,))
    if not cc:
        raise HTTPException(404, "Cost center not found")
    conditions: list[str] = ["gl.cost_center_id = %s"]
    params: list = [cost_center_id]
    if date_from:
        conditions.append("gl.entry_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("gl.entry_date <= %s")
        params.append(date_to)
    where = "WHERE " + " AND ".join(conditions)
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT gl.*, coa.account_name
            FROM general_ledger gl
            LEFT JOIN chart_of_accounts coa ON gl.account_code = coa.account_code
            {where}
            ORDER BY gl.entry_date DESC
            LIMIT %s OFFSET %s""",
        tuple(params),
    )
    return {
        "cost_center": cc,
        "items": rows,
        "offset": offset,
        "limit": limit,
    }
