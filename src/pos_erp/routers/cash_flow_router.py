"""Cash Flow Category Router - Beauty & Shine POS-ERP V6."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute_returning

router = APIRouter(prefix="/api/cash-flow", tags=["Cash Flow Category"])


class CashFlowCategoryCreate(BaseModel):
    name: str
    type: str  # operating, investing, financing


class CashFlowCategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/categories")
def list_categories(type: Optional[str] = None, is_active: Optional[bool] = None):
    conditions, params = [], []
    if type:
        conditions.append("cf.type = %s")
        params.append(type)
    if is_active is not None:
        conditions.append("cf.is_active = %s")
        params.append(is_active)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows = fetch_all(
        f"SELECT * FROM cash_flow_category cf {where} ORDER BY cf.type, cf.name",
        tuple(params),
    )
    return {"categories": rows, "total": len(rows)}


@router.get("/report")
def cash_flow_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    branch_id: Optional[str] = None,
):
    """Cash flow statement grouped by category type (operating/investing/financing)."""
    conditions, params = [], []
    if date_from:
        conditions.append("je.entry_date >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("je.entry_date <= %s")
        params.append(date_to)
    if branch_id:
        conditions.append("je.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = fetch_all(
        f"""SELECT COALESCE(cf.type, 'uncategorized') AS type, COALESCE(cf.name, coa.account_name) AS name,
                COALESCE(SUM(jel.debit), 0) AS total_debit,
                COALESCE(SUM(jel.credit), 0) AS total_credit,
                COALESCE(SUM(jel.debit - jel.credit), 0) AS net_amount
            FROM journal_entry_line jel
            JOIN journal_entry je ON jel.journal_entry_id = je.id
            JOIN chart_of_account coa ON jel.account_code = coa.account_code
            LEFT JOIN cash_flow_category cf ON coa.mapped_to_id = cf.id
            {where}
            GROUP BY cf.type, cf.name, coa.account_name
            ORDER BY cf.type, coa.account_name""",
        tuple(params),
    )

    operating = [r for r in rows if r.get("type") == "operating"]
    investing = [r for r in rows if r.get("type") == "investing"]
    financing = [r for r in rows if r.get("type") == "financing"]

    return {
        "operating": operating,
        "investing": investing,
        "financing": financing,
        "net_operating": sum(r.get("net_amount", 0) for r in operating),
        "net_investing": sum(r.get("net_amount", 0) for r in investing),
        "net_financing": sum(r.get("net_amount", 0) for r in financing),
    }


@router.post("/category")
def create_category(data: CashFlowCategoryCreate):
    row = execute_returning(
        """INSERT INTO cash_flow_category (name, type, is_active)
           VALUES (%s, %s, TRUE) RETURNING *""",
        (data.name, data.type),
    )
    return row


@router.put("/category/{cat_id}")
def update_category(cat_id: str, data: CashFlowCategoryUpdate):
    existing = fetch_one("SELECT * FROM cash_flow_category WHERE id = %s", (cat_id,))
    if not existing:
        raise HTTPException(404, "Category not found")
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return existing
    sets, vals = [], []
    for k, v in fields.items():
        sets.append(f"{k} = %s")
        vals.append(v)
    vals.append(cat_id)
    row = execute_returning(
        f"UPDATE cash_flow_category SET {', '.join(sets)} WHERE id = %s RETURNING *",
        tuple(vals),
    )
    return row


@router.delete("/category/{cat_id}")
def delete_category(cat_id: str):
    existing = fetch_one("SELECT * FROM cash_flow_category WHERE id = %s", (cat_id,))
    if not existing:
        raise HTTPException(404, "Category not found")
    execute_returning(
        "UPDATE cash_flow_category SET is_active = FALSE WHERE id = %s RETURNING id",
        (cat_id,),
    )
    return {"deleted": True, "id": cat_id}
