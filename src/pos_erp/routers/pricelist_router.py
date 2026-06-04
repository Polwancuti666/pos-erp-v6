"""Product/Treatment Pricelist Router - Beauty & Shine POS-ERP V6.

Manage per-branch pricing for products and treatments with validity periods.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/pricelist", tags=["Pricelist"])


# ── Request Models ────────────────────────────────────────────────────────────

class ProductPricelistCreate(BaseModel):
    product_id: str
    branch_id: str
    price: float
    valid_from: Optional[str] = None   # YYYY-MM-DD
    valid_until: Optional[str] = None  # YYYY-MM-DD


class ProductPricelistUpdate(BaseModel):
    price: Optional[float] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


class TreatmentPricelistCreate(BaseModel):
    treatment_id: str
    branch_id: str
    price: float
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


class TreatmentPricelistUpdate(BaseModel):
    price: Optional[float] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None


# ── Product Pricelist Endpoints ───────────────────────────────────────────────

@router.get("/product-pricelist")
def list_product_pricelist(
    product_id: str = "",
    branch_id: str = "",
):
    """List product prices with optional filters."""
    conditions = []
    params: list = []
    if product_id:
        conditions.append("pp.product_id = %s")
        params.append(product_id)
    if branch_id:
        conditions.append("pp.branch_id = %s")
        params.append(branch_id)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(500)

    rows = fetch_all(
        f"""SELECT pp.*, p.name AS product_name
            FROM product_pricelist pp
            LEFT JOIN product p ON p.id = pp.product_id
            {where}
            ORDER BY pp.branch_id, p.name
            LIMIT %s""",
        tuple(params),
    )
    return {"items": rows}


@router.post("/product-pricelist")
def create_product_pricelist(req: ProductPricelistCreate):
    """Create a product price entry for a branch."""
    row = execute_returning(
        """INSERT INTO product_pricelist
               (product_id, branch_id, price, valid_from, valid_until, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
           RETURNING *""",
        (req.product_id, req.branch_id, req.price, req.valid_from, req.valid_until),
    )
    return row


@router.put("/product-pricelist/{pricelist_id}")
def update_product_pricelist(pricelist_id: str, req: ProductPricelistUpdate):
    """Update a product price entry."""
    existing = fetch_one("SELECT * FROM product_pricelist WHERE id=%s", (pricelist_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Product pricelist entry not found")

    fields = []
    params: list = []
    for field_name, value in [
        ("price", req.price),
        ("valid_from", req.valid_from),
        ("valid_until", req.valid_until),
    ]:
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields.append("updated_at = NOW()")
    params.append(pricelist_id)

    row = execute_returning(
        f"UPDATE product_pricelist SET {', '.join(fields)} WHERE id=%s RETURNING *",
        tuple(params),
    )
    return row


# ── Treatment Pricelist Endpoints ─────────────────────────────────────────────

@router.get("/treatment-pricelist")
def list_treatment_pricelist(
    treatment_id: str = "",
    branch_id: str = "",
):
    """List treatment prices with optional filters."""
    conditions = []
    params: list = []
    if treatment_id:
        conditions.append("tp.treatment_id = %s")
        params.append(treatment_id)
    if branch_id:
        conditions.append("tp.branch_id = %s")
        params.append(branch_id)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(500)

    rows = fetch_all(
        f"""SELECT tp.*, t.name AS treatment_name
            FROM treatment_pricelist tp
            LEFT JOIN treatment t ON t.id = tp.treatment_id
            {where}
            ORDER BY tp.branch_id, t.name
            LIMIT %s""",
        tuple(params),
    )
    return {"items": rows}


@router.post("/treatment-pricelist")
def create_treatment_pricelist(req: TreatmentPricelistCreate):
    """Create a treatment price entry for a branch."""
    row = execute_returning(
        """INSERT INTO treatment_pricelist
               (treatment_id, branch_id, price, valid_from, valid_until, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
           RETURNING *""",
        (req.treatment_id, req.branch_id, req.price, req.valid_from, req.valid_until),
    )
    return row


@router.put("/treatment-pricelist/{pricelist_id}")
def update_treatment_pricelist(pricelist_id: str, req: TreatmentPricelistUpdate):
    """Update a treatment price entry."""
    existing = fetch_one("SELECT * FROM treatment_pricelist WHERE id=%s", (pricelist_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Treatment pricelist entry not found")

    fields = []
    params: list = []
    for field_name, value in [
        ("price", req.price),
        ("valid_from", req.valid_from),
        ("valid_until", req.valid_until),
    ]:
        if value is not None:
            fields.append(f"{field_name} = %s")
            params.append(value)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields.append("updated_at = NOW()")
    params.append(pricelist_id)

    row = execute_returning(
        f"UPDATE treatment_pricelist SET {', '.join(fields)} WHERE id=%s RETURNING *",
        tuple(params),
    )
    return row


# ── Price Lookup ──────────────────────────────────────────────────────────────

@router.get("/price-lookup")
def price_lookup(
    branch_id: str = Query(..., description="Branch to look up prices for"),
    product_id: str = "",
    treatment_id: str = "",
    effective_date: str = "",
):
    """Get the effective price for a product or treatment at a branch.

    If effective_date is not provided, uses CURRENT_DATE.
    Returns the first matching price where the date falls within valid_from..valid_until.
    """
    if not product_id and not treatment_id:
        raise HTTPException(status_code=400, detail="Provide product_id or treatment_id")

    result = {}

    if product_id:
        if effective_date:
            row = fetch_one(
                """SELECT pp.*, p.name AS product_name
                   FROM product_pricelist pp
                   LEFT JOIN product p ON p.id = pp.product_id
                   WHERE pp.product_id = %s
                     AND pp.branch_id = %s
                     AND (pp.valid_from IS NULL OR pp.valid_from <= %s)
                     AND (pp.valid_until IS NULL OR pp.valid_until >= %s)
                   ORDER BY pp.valid_from DESC NULLS LAST
                   LIMIT 1""",
                (product_id, branch_id, effective_date, effective_date),
            )
        else:
            row = fetch_one(
                """SELECT pp.*, p.name AS product_name
                   FROM product_pricelist pp
                   LEFT JOIN product p ON p.id = pp.product_id
                   WHERE pp.product_id = %s
                     AND pp.branch_id = %s
                     AND (pp.valid_from IS NULL OR pp.valid_from <= CURRENT_DATE)
                     AND (pp.valid_until IS NULL OR pp.valid_until >= CURRENT_DATE)
                   ORDER BY pp.valid_from DESC NULLS LAST
                   LIMIT 1""",
                (product_id, branch_id),
            )
        result["product"] = row

    if treatment_id:
        if effective_date:
            row = fetch_one(
                """SELECT tp.*, t.name AS treatment_name
                   FROM treatment_pricelist tp
                   LEFT JOIN treatment t ON t.id = tp.treatment_id
                   WHERE tp.treatment_id = %s
                     AND tp.branch_id = %s
                     AND (tp.valid_from IS NULL OR tp.valid_from <= %s)
                     AND (tp.valid_until IS NULL OR tp.valid_until >= %s)
                   ORDER BY tp.valid_from DESC NULLS LAST
                   LIMIT 1""",
                (treatment_id, branch_id, effective_date, effective_date),
            )
        else:
            row = fetch_one(
                """SELECT tp.*, t.name AS treatment_name
                   FROM treatment_pricelist tp
                   LEFT JOIN treatment t ON t.id = tp.treatment_id
                   WHERE tp.treatment_id = %s
                     AND tp.branch_id = %s
                     AND (tp.valid_from IS NULL OR tp.valid_from <= CURRENT_DATE)
                     AND (tp.valid_until IS NULL OR tp.valid_until >= CURRENT_DATE)
                   ORDER BY tp.valid_from DESC NULLS LAST
                   LIMIT 1""",
                (treatment_id, branch_id),
            )
        result["treatment"] = row

    return result
