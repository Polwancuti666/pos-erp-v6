"""WIP & Manufacture Module Router for Beauty & Shine POS-ERP V6."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/wip", tags=["WIP & Manufacture"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class ProductionOrderReq(BaseModel):
    order_no: str
    product_id: int
    bom_id: Optional[int] = None
    planned_qty: float
    unit: str = "pcs"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notes: Optional[str] = None


class ProductionMaterialReq(BaseModel):
    production_order_id: int
    product_id: int
    planned_qty: float
    actual_qty: float = 0
    unit: str = "pcs"
    notes: Optional[str] = None


class ProductionQCReq(BaseModel):
    production_order_id: int
    inspector: str
    passed_qty: float = 0
    rejected_qty: float = 0
    notes: Optional[str] = None


class QCRecordReq(BaseModel):
    inspector: str
    passed_qty: float = 0
    rejected_qty: float = 0
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Production Order CRUD
# ---------------------------------------------------------------------------

@router.get("/production-order")
def list_production_orders():
    """List all production orders."""
    rows = fetch_all(
        "SELECT po.*, p.name AS product_name "
        "FROM production_order po "
        "LEFT JOIN product p ON p.id = po.product_id "
        "ORDER BY po.created_at DESC"
    )
    return {"items": rows}


@router.get("/production-order/variance")
def production_order_variance():
    """BOM variance analysis: planned vs actual material usage."""
    rows = fetch_all(
        "SELECT po.id AS order_id, po.order_no, po.product_id, "
        "po.planned_qty, po.status, "
        "pm.product_id AS material_product_id, "
        "pm.planned_qty AS material_planned_qty, "
        "pm.actual_qty AS material_actual_qty, "
        "pm.unit, "
        "CASE WHEN pm.planned_qty > 0 "
        "  THEN ROUND((pm.actual_qty - pm.planned_qty) / pm.planned_qty * 100, 2) "
        "  ELSE 0 END AS variance_pct "
        "FROM production_order po "
        "JOIN production_material pm ON pm.production_order_id = po.id "
        "ORDER BY po.created_at DESC, pm.id"
    )
    return {"items": rows}


@router.get("/production-order/{order_id}")
def get_production_order(order_id: int):
    """Get a single production order by ID."""
    row = fetch_one(
        "SELECT po.*, p.name AS product_name "
        "FROM production_order po "
        "LEFT JOIN product p ON p.id = po.product_id "
        "WHERE po.id = %s",
        (order_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Production order not found")
    return row


@router.post("/production-order")
def create_production_order(req: ProductionOrderReq):
    """Create a new production order."""
    existing = fetch_one(
        "SELECT id FROM production_order WHERE order_no = %s", (req.order_no,)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Order number already exists")

    row = execute_returning(
        "INSERT INTO production_order "
        "(order_no, product_id, bom_id, planned_qty, unit, start_date, end_date, status, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
        (
            req.order_no,
            req.product_id,
            req.bom_id,
            req.planned_qty,
            req.unit,
            req.start_date,
            req.end_date,
            "draft",
            req.notes,
        ),
    )
    return row


@router.put("/production-order/{order_id}")
def update_production_order(order_id: int, req: ProductionOrderReq):
    """Update an existing production order."""
    existing = fetch_one("SELECT id FROM production_order WHERE id = %s", (order_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Production order not found")

    row = execute_returning(
        "UPDATE production_order SET "
        "order_no=%s, product_id=%s, bom_id=%s, planned_qty=%s, unit=%s, "
        "start_date=%s, end_date=%s, notes=%s, updated_at=NOW() "
        "WHERE id=%s RETURNING *",
        (
            req.order_no,
            req.product_id,
            req.bom_id,
            req.planned_qty,
            req.unit,
            req.start_date,
            req.end_date,
            req.notes,
            order_id,
        ),
    )
    return row


# ---------------------------------------------------------------------------
# Production Order Actions
# ---------------------------------------------------------------------------

@router.post("/production-order/{order_id}/start")
def start_production_order(order_id: int):
    """Start a production order – change status to in_progress."""
    existing = fetch_one("SELECT * FROM production_order WHERE id = %s", (order_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Production order not found")
    if existing["status"] not in ("draft", "planned"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start order with status '{existing['status']}'",
        )

    row = execute_returning(
        "UPDATE production_order SET status='in_progress', updated_at=NOW() "
        "WHERE id=%s RETURNING *",
        (order_id,),
    )
    return row


@router.post("/production-order/{order_id}/complete")
def complete_production_order(order_id: int):
    """Complete a production order and update stock card with finished goods."""
    po = fetch_one("SELECT * FROM production_order WHERE id = %s", (order_id,))
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")
    if po["status"] != "in_progress":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete order with status '{po['status']}'",
        )

    # Deduct raw materials from stock card
    materials = fetch_all(
        "SELECT * FROM production_material WHERE production_order_id = %s",
        (order_id,),
    )
    for mat in materials:
        if mat["actual_qty"] and mat["actual_qty"] > 0:
            execute(
                "INSERT INTO stock_card "
                "(product_id, ref_type, ref_id, qty_change, unit, notes, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                (
                    mat["product_id"],
                    "production_order",
                    order_id,
                    -abs(mat["actual_qty"]),
                    mat["unit"],
                    f"Material consumed for PO {po['order_no']}",
                ),
            )

    # Add finished goods to stock card
    execute(
        "INSERT INTO stock_card "
        "(product_id, ref_type, ref_id, qty_change, unit, notes, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, NOW())",
        (
            po["product_id"],
            "production_order",
            order_id,
            po["planned_qty"],
            po["unit"],
            f"Finished goods from PO {po['order_no']}",
        ),
    )

    # Derive actual_qty from QC passed if available
    qc = fetch_one(
        "SELECT COALESCE(SUM(passed_qty), 0) AS total_passed "
        "FROM production_qc WHERE production_order_id = %s",
        (order_id,),
    )
    actual_qty = qc["total_passed"] if qc and qc["total_passed"] else po["planned_qty"]

    row = execute_returning(
        "UPDATE production_order SET status='completed', actual_qty=%s, "
        "completed_at=NOW(), updated_at=NOW() WHERE id=%s RETURNING *",
        (actual_qty, order_id),
    )
    return row


@router.post("/production-order/{order_id}/qc")
def add_qc_record(order_id: int, req: QCRecordReq):
    """Add a QC record to a production order."""
    po = fetch_one("SELECT id FROM production_order WHERE id = %s", (order_id,))
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    row = execute_returning(
        "INSERT INTO production_qc "
        "(production_order_id, inspector, passed_qty, rejected_qty, notes, created_at) "
        "VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING *",
        (order_id, req.inspector, req.passed_qty, req.rejected_qty, req.notes),
    )
    return row


# ---------------------------------------------------------------------------
# Production Materials
# ---------------------------------------------------------------------------

@router.get("/production-material")
def list_production_materials(production_order_id: Optional[int] = None):
    """List production materials, optionally filtered by order."""
    if production_order_id:
        rows = fetch_all(
            "SELECT pm.*, p.name AS product_name "
            "FROM production_material pm "
            "LEFT JOIN product p ON p.id = pm.product_id "
            "WHERE pm.production_order_id = %s ORDER BY pm.id",
            (production_order_id,),
        )
    else:
        rows = fetch_all(
            "SELECT pm.*, p.name AS product_name "
            "FROM production_material pm "
            "LEFT JOIN product p ON p.id = pm.product_id "
            "ORDER BY pm.created_at DESC"
        )
    return {"items": rows}


@router.post("/production-material")
def create_production_material(req: ProductionMaterialReq):
    """Record material usage for a production order."""
    po = fetch_one(
        "SELECT id FROM production_order WHERE id = %s", (req.production_order_id,)
    )
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    row = execute_returning(
        "INSERT INTO production_material "
        "(production_order_id, product_id, planned_qty, actual_qty, unit, notes, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, NOW()) RETURNING *",
        (
            req.production_order_id,
            req.product_id,
            req.planned_qty,
            req.actual_qty,
            req.unit,
            req.notes,
        ),
    )
    return row


# ---------------------------------------------------------------------------
# Production QC
# ---------------------------------------------------------------------------

@router.get("/production-qc")
def list_production_qc(production_order_id: Optional[int] = None):
    """List QC records, optionally filtered by production order."""
    if production_order_id:
        rows = fetch_all(
            "SELECT pqc.*, po.order_no "
            "FROM production_qc pqc "
            "LEFT JOIN production_order po ON po.id = pqc.production_order_id "
            "WHERE pqc.production_order_id = %s ORDER BY pqc.id",
            (production_order_id,),
        )
    else:
        rows = fetch_all(
            "SELECT pqc.*, po.order_no "
            "FROM production_qc pqc "
            "LEFT JOIN production_order po ON po.id = pqc.production_order_id "
            "ORDER BY pqc.created_at DESC"
        )
    return {"items": rows}


@router.post("/production-qc")
def create_production_qc(req: ProductionQCReq):
    """Create a QC record for a production order."""
    po = fetch_one(
        "SELECT id FROM production_order WHERE id = %s", (req.production_order_id,)
    )
    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    row = execute_returning(
        "INSERT INTO production_qc "
        "(production_order_id, inspector, passed_qty, rejected_qty, notes, created_at) "
        "VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING *",
        (
            req.production_order_id,
            req.inspector,
            req.passed_qty,
            req.rejected_qty,
            req.notes,
        ),
    )
    return row
