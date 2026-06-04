"""Executive Dashboard Router — Beauty & Shine POS-ERP V6."""

from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/executive", tags=["Executive Dashboard"])


class KPITargetCreate(BaseModel):
    name: str
    metric_type: str
    target_value: float
    period: str = "monthly"
    branch_id: Optional[str] = None


class KPITargetUpdate(BaseModel):
    name: Optional[str] = None
    target_value: Optional[float] = None
    period: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/summary")
def executive_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    branch_id: Optional[str] = None,
):
    """Executive KPI summary — revenue, transactions, customer, staff."""
    cond = ["pt.status = 'paid'"]
    params = []
    if date_from:
        cond.append("pt.created_at::date >= %s")
        params.append(date_from)
    if date_to:
        cond.append("pt.created_at::date <= %s")
        params.append(date_to)
    if branch_id:
        cond.append("pt.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(cond)

    revenue = fetch_one(
        f"SELECT COALESCE(SUM(total),0) AS val FROM pos_transaction pt {where}",
        tuple(params),
    )
    transactions = fetch_one(
        f"SELECT COUNT(*) AS val FROM pos_transaction pt {where}",
        tuple(params),
    )
    avg_ticket = fetch_one(
        f"SELECT COALESCE(AVG(total),0) AS val FROM pos_transaction pt {where}",
        tuple(params),
    )
    new_customers = fetch_one(
        f"""SELECT COUNT(DISTINCT customer_name) AS val FROM pos_transaction pt
            {where}""",
        tuple(params),
    )
    # Therapist occupancy
    total_treatments = fetch_one(
        f"""SELECT COUNT(*) AS val FROM treatment_record tr
            JOIN pos_transaction pt ON tr.transaction_id = pt.id
            {where}""",
        tuple(params),
    )
    # Expense total
    expense = fetch_one(
        f"""SELECT COALESCE(SUM(amount),0) AS val FROM accounts_payable ap
            WHERE ap.status = 'paid'""",
        (),
    )

    rev = (revenue or {}).get("val", 0) or 0
    exp = (expense or {}).get("val", 0) or 0

    return {
        "revenue": rev,
        "expense": exp,
        "profit": rev - exp,
        "transactions": (transactions or {}).get("val", 0) or 0,
        "avg_ticket_size": round((avg_ticket or {}).get("val", 0) or 0),
        "new_customers": (new_customers or {}).get("val", 0) or 0,
        "total_treatments": (total_treatments or {}).get("val", 0) or 0,
    }


@router.get("/branch-comparison")
def branch_comparison(date_from: Optional[str] = None, date_to: Optional[str] = None):
    """Compare performance across all branches."""
    cond, params = [], []
    if date_from:
        cond.append("pt.created_at::date >= %s")
        params.append(date_from)
    if date_to:
        cond.append("pt.created_at::date <= %s")
        params.append(date_to)
    cond.append("pt.status = 'paid'")
    where = "WHERE " + " AND ".join(cond)

    rows = fetch_all(
        f"""SELECT b.id, b.name AS branch_name,
                COUNT(pt.id) AS transactions,
                COALESCE(SUM(pt.total), 0) AS revenue,
                COALESCE(AVG(pt.total), 0) AS avg_ticket
            FROM branch b
            LEFT JOIN pos_transaction pt ON pt.branch_id = b.id AND pt.status = 'paid'
                {"AND pt.created_at::date >= %s AND pt.created_at::date <= %s" if date_from and date_to else ""}
            GROUP BY b.id, b.name ORDER BY revenue DESC""",
        tuple([p for p in [date_from, date_to] if p]),
    )
    return {"branches": rows}


@router.get("/kpi-targets")
def list_kpi_targets(branch_id: Optional[str] = None):
    cond, params = [], []
    if branch_id:
        cond.append("kt.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(cond) if cond else ""
    rows = fetch_all(f"SELECT * FROM kpi_target kt {where} ORDER BY kt.metric_type", tuple(params))
    return {"targets": rows}


@router.post("/kpi-target")
def create_kpi_target(data: KPITargetCreate):
    return execute_returning(
        """INSERT INTO kpi_target (name, metric_type, target_value, period, branch_id)
           VALUES (%s,%s,%s,%s,%s) RETURNING *""",
        (data.name, data.metric_type, data.target_value, data.period, data.branch_id),
    )


@router.put("/kpi-target/{target_id}")
def update_kpi_target(target_id: int, data: KPITargetUpdate):
    existing = fetch_one("SELECT * FROM kpi_target WHERE id = %s", (target_id,))
    if not existing:
        raise HTTPException(404, "KPI target not found")
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return existing
    sets, vals = [], []
    for k, v in fields.items():
        sets.append(f"{k} = %s")
        vals.append(v)
    vals.append(target_id)
    return execute_returning(
        f"UPDATE kpi_target SET {', '.join(sets)} WHERE id = %s RETURNING *", tuple(vals)
    )


@router.delete("/kpi-target/{target_id}")
def delete_kpi_target(target_id: int):
    n = execute("DELETE FROM kpi_target WHERE id = %s", (target_id,))
    if n == 0:
        raise HTTPException(404, "KPI target not found")
    return {"deleted": True}


@router.get("/top-treatments")
def top_treatments(date_from: Optional[str] = None, date_to: Optional[str] = None, branch_id: Optional[str] = None, limit: int = 10):
    cond, params = [], []
    if date_from:
        cond.append("pt.created_at::date >= %s")
        params.append(date_from)
    if date_to:
        cond.append("pt.created_at::date <= %s")
        params.append(date_to)
    if branch_id:
        cond.append("pt.branch_id = %s")
        params.append(branch_id)
    cond.append("pt.status = 'paid'")
    where = "WHERE " + " AND ".join(cond)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT t.name AS treatment_name, tc.name AS treatment_category,
                COUNT(tr.id) AS booking_count,
                COALESCE(SUM(pt.total), 0) AS total_revenue,
                COALESCE(AVG(pt.total), 0) AS avg_price
            FROM treatment_record tr
            JOIN treatment t ON tr.treatment_id = t.id
            LEFT JOIN treatment_category tc ON t.category_id = tc.id
            JOIN pos_transaction pt ON tr.transaction_id = pt.id
            {where}
            GROUP BY t.name, tc.name
            ORDER BY total_revenue DESC LIMIT %s""",
        tuple(params),
    )
    return {"treatments": rows}


@router.get("/top-therapists")
def top_therapists(date_from: Optional[str] = None, date_to: Optional[str] = None, branch_id: Optional[str] = None, limit: int = 10):
    cond, params = [], []
    if date_from:
        cond.append("pt.created_at::date >= %s")
        params.append(date_from)
    if date_to:
        cond.append("pt.created_at::date <= %s")
        params.append(date_to)
    if branch_id:
        cond.append("pt.branch_id = %s")
        params.append(branch_id)
    cond.append("pt.status = 'paid'")
    where = "WHERE " + " AND ".join(cond)
    params.append(limit)
    rows = fetch_all(
        f"""SELECT u.username AS therapist_name,
                COUNT(tr.id) AS treatments_done,
                COALESCE(SUM(pt.total), 0) AS total_revenue
            FROM treatment_record tr
            JOIN app_user u ON tr.therapist_id = u.id
            JOIN pos_transaction pt ON tr.transaction_id = pt.id
            {where}
            GROUP BY u.username
            ORDER BY total_revenue DESC LIMIT %s""",
        tuple(params),
    )
    return {"therapists": rows}
