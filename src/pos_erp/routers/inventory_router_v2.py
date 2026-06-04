"""Inventory Router - Beauty & Shine ERP.

Domain-driven implementation with:
- StockLedger for balance tracking
- InventoryPolicy for negative stock control
- BOM consumption support
- AuditTrail integration
- DocumentRegistry for consistent doc keys
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.domain_models import (
    DocumentKind, MovementType, MovementReason,
    InventoryPolicy, NegativeStockBlocked, AuditAction,
)
from pos_erp.repository import (
    DocumentRegistryRepository, AuditTrailRepository,
    StockRepository,
)
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

# ── Request Models ────────────────────────────────────────────────

class StockInRequest(BaseModel):
    product_id: str
    branch_id: str
    qty: float
    batch_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None

class StockOutRequest(BaseModel):
    product_id: str
    branch_id: str
    qty: float
    notes: Optional[str] = None
    created_by: Optional[str] = None

class OpnameItemReq(BaseModel):
    product_id: str
    system_qty: float
    actual_qty: float
    notes: Optional[str] = None

class OpnameRequest(BaseModel):
    branch_id: str
    items: list[OpnameItemReq]
    created_by: Optional[str] = None

class BatchRequest(BaseModel):
    product_id: str
    branch_id: str
    batch_no: str
    qty: float
    cost_per_unit: float = 0
    expiry_date: Optional[str] = None

class BOMComponentReq(BaseModel):
    component_product_id: str
    qty: float
    unit: str = "pcs"
    cost_per_unit: float = 0

class BOMRequest(BaseModel):
    product_id: str
    name: str
    description: Optional[str] = None
    standard_cost: float = 0
    components: list[BOMComponentReq] = []


# ── Helpers ───────────────────────────────────────────────────────

def _generate_doc_key(module: DocumentKind, branch_code: str = "BSD") -> str:
    return DocumentRegistryRepository.generate_doc_key(module.value, branch_code)

def _audit(doc_key: str, action: AuditAction, details: str = None):
    AuditTrailRepository.record(doc_key=doc_key, module="inventory", action=action.value, new_value=details)


# ── Stock Card ────────────────────────────────────────────────────

@router.get("/stock-card")
def list_stock_cards(branch_id: str = "", q: str = "", offset: int = 0, limit: int = 50):
    """List stock cards with product info."""
    conditions = []
    params = []
    if branch_id:
        conditions.append("sc.branch_id = %s")
        params.append(branch_id)
    if q:
        conditions.append("p.name ILIKE %s")
        params.append(f"%{q}%")
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    
    rows = fetch_all(
        f"""SELECT sc.*, p.name as product_name, p.sku, p.unit, b.name as branch_name
            FROM stock_card sc
            JOIN product p ON sc.product_id=p.id
            LEFT JOIN branch b ON sc.branch_id=b.id
            {where} ORDER BY p.name LIMIT %s OFFSET %s""",
        tuple(params)
    )
    return {"items": rows}

@router.get("/stock-card/{product_id}")
def get_stock_card(product_id: str, branch_id: str = ""):
    """Get stock card for a product."""
    if branch_id:
        return fetch_one("SELECT * FROM stock_card WHERE product_id=%s AND branch_id=%s", (product_id, branch_id))
    return fetch_all("SELECT sc.*, b.name as branch_name FROM stock_card sc LEFT JOIN branch b ON sc.branch_id=b.id WHERE sc.product_id=%s", (product_id,))


# ── Stock Movement ────────────────────────────────────────────────

@router.get("/movements")
def list_movements(product_id: str = "", branch_id: str = "", movement_type: str = "", offset: int = 0, limit: int = 50):
    """List stock movements with filters."""
    return {"items": StockRepository.get_movements(product_id or None, branch_id or None, limit)}


# ── Stock In ──────────────────────────────────────────────────────

@router.post("/stock-in")
def stock_in(req: StockInRequest):
    """Record stock coming in."""
    doc_key = _generate_doc_key(DocumentKind.STK)
    
    try:
        # Update stock balance
        card = StockRepository.update_balance(
            product_id=req.product_id,
            branch_id=req.branch_id,
            qty_change=req.qty,
            movement_type="in",
        )
        
        # Create movement record
        movement = StockRepository.create_movement(
            doc_key=doc_key,
            product_id=req.product_id,
            branch_id=req.branch_id,
            movement_type="in",
            qty=req.qty,
            batch_id=req.batch_id,
            notes=req.notes,
            created_by=req.created_by,
        )
        
        # Update batch qty if specified
        if req.batch_id:
            execute("UPDATE product_batch SET qty = qty + %s WHERE id = %s", (req.qty, req.batch_id))
        
        _audit(doc_key, AuditAction.CREATE, f"Stock in: {req.qty} units")
        
        return movement
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Stock Out ─────────────────────────────────────────────────────

@router.post("/stock-out")
def stock_out(req: StockOutRequest):
    """Record stock going out with negative stock policy check."""
    doc_key = _generate_doc_key(DocumentKind.STK)
    
    # Check stock availability
    card = StockRepository.get_card(req.product_id, req.branch_id)
    if not card or float(card["balance"]) < req.qty:
        policy = InventoryPolicy()
        if not policy.allow_negative:
            available = float(card["balance"]) if card else 0
            raise HTTPException(400, f"Insufficient stock: available {available}, required {req.qty}")
    
    try:
        # Update stock balance
        card = StockRepository.update_balance(
            product_id=req.product_id,
            branch_id=req.branch_id,
            qty_change=req.qty,
            movement_type="out",
        )
        
        # Create movement record
        movement = StockRepository.create_movement(
            doc_key=doc_key,
            product_id=req.product_id,
            branch_id=req.branch_id,
            movement_type="out",
            qty=req.qty,
            notes=req.notes,
            created_by=req.created_by,
        )
        
        _audit(doc_key, AuditAction.CREATE, f"Stock out: {req.qty} units")
        
        return movement
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── BOM Consumption ───────────────────────────────────────────────

@router.post("/bom-consumption")
def consume_bom(wip_order_id: str, actual_qty: float = 0):
    """Consume BOM components for a WIP order."""
    wip = fetch_one("SELECT * FROM wip_order WHERE id = %s", (wip_order_id,))
    if not wip:
        raise HTTPException(404, "WIP order not found")
    
    bom = fetch_one("SELECT * FROM bom_header WHERE id = %s", (wip["bom_id"],))
    if not bom:
        raise HTTPException(404, "BOM not found")
    
    components = fetch_all("SELECT * FROM bom_component WHERE bom_id = %s", (bom["id"],))
    movements = []
    
    for comp in components:
        consume_qty = float(comp["qty"]) * (actual_qty or float(wip["planned_qty"]))
        doc_key = _generate_doc_key(DocumentKind.STK)
        
        try:
            StockRepository.update_balance(
                product_id=comp["component_product_id"],
                branch_id=wip["branch_id"],
                qty_change=consume_qty,
                movement_type="out",
            )
            
            movement = StockRepository.create_movement(
                doc_key=doc_key,
                product_id=comp["component_product_id"],
                branch_id=wip["branch_id"],
                movement_type="out",
                qty=consume_qty,
                reference_doc_key=wip["doc_key"],
                notes=f"BOM consumption for {wip['doc_key']}",
            )
            movements.append(movement)
            
            # Record consumption
            execute(
                """INSERT INTO wip_consumption (wip_order_id, component_product_id, planned_qty, actual_qty, variance)
                   VALUES (%s, %s, %s, %s, %s)""",
                (wip_order_id, comp["component_product_id"], float(comp["qty"]) * float(wip["planned_qty"]), consume_qty, 0)
            )
        except ValueError as e:
            _audit(doc_key, AuditAction.UPDATE, f"BOM consumption warning: {e}")
    
    return {"movements": movements, "consumed": len(movements)}


# ── Stock Opname ──────────────────────────────────────────────────

@router.get("/opnames")
def list_opnames(branch_id: str = "", offset: int = 0, limit: int = 50):
    """List stock opnames."""
    extra = "WHERE so.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()
    rows = fetch_all(
        f"SELECT so.*, b.name as branch_name FROM stock_opname so LEFT JOIN branch b ON so.branch_id=b.id {extra} ORDER BY so.opname_date DESC LIMIT %s OFFSET %s",
        (*params, limit, offset)
    )
    return {"items": rows}

@router.post("/opname")
def create_opname(req: OpnameRequest):
    """Create stock opname with items."""
    doc_key = _generate_doc_key(DocumentKind.SO)
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO stock_opname (doc_key, branch_id, opname_date, status, created_by) VALUES (%s, %s, %s, 'draft', %s) RETURNING *",
                (doc_key, req.branch_id, date.today(), req.created_by)
            )
            opname = cur.fetchone()
            
            for item in req.items:
                diff = item.actual_qty - item.system_qty
                cur.execute(
                    """INSERT INTO stock_opname_item (opname_id, product_id, system_qty, actual_qty, difference, notes)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (opname["id"], item.product_id, item.system_qty, item.actual_qty, diff, item.notes)
                )
    
    _audit(doc_key, AuditAction.CREATE, f"Stock opname created with {len(req.items)} items")
    return opname

@router.put("/opname/{id}/approve")
def approve_opname(id: str, approved_by: str = ""):
    """Approve stock opname and adjust stock."""
    opname = fetch_one("SELECT * FROM stock_opname WHERE id = %s", (id,))
    if not opname:
        raise HTTPException(404, "Opname not found")
    if opname["status"] == "approved":
        raise HTTPException(400, "Already approved")
    
    items = fetch_all("SELECT * FROM stock_opname_item WHERE opname_id = %s", (id,))
    
    for item in items:
        diff = float(item["difference"])
        if diff != 0:
            doc_key = _generate_doc_key(DocumentKind.STK)
            movement_type = "in" if diff > 0 else "out"
            abs_diff = abs(diff)
            
            try:
                StockRepository.update_balance(
                    product_id=item["product_id"],
                    branch_id=opname["branch_id"],
                    qty_change=abs_diff,
                    movement_type=movement_type,
                )
                StockRepository.create_movement(
                    doc_key=doc_key,
                    product_id=item["product_id"],
                    branch_id=opname["branch_id"],
                    movement_type=movement_type,
                    qty=abs_diff,
                    reference_doc_key=opname["doc_key"],
                    notes=f"Opname adjustment: {item['notes'] or ''}",
                )
            except ValueError as e:
                _audit(doc_key, AuditAction.UPDATE, f"Opname adjustment warning: {e}")
    
    execute("UPDATE stock_opname SET status='approved', approved_by=%s WHERE id=%s", (approved_by or None, id))
    _audit(opname["doc_key"], AuditAction.APPROVE, "Stock opname approved")
    
    return fetch_one("SELECT * FROM stock_opname WHERE id=%s", (id,))


# ── Low Stock ─────────────────────────────────────────────────────

@router.get("/low-stock")
def get_low_stock(threshold: float = 10, branch_id: str = ""):
    """Get products with low stock."""
    return {"items": StockRepository.get_low_stock(branch_id or None, threshold)}


# ── Batch Management ──────────────────────────────────────────────

@router.get("/batches")
def list_batches(product_id: str = "", branch_id: str = ""):
    """List product batches."""
    conditions = []
    params = []
    if product_id:
        conditions.append("pb.product_id = %s")
        params.append(product_id)
    if branch_id:
        conditions.append("pb.branch_id = %s")
        params.append(branch_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    rows = fetch_all(
        f"SELECT pb.*, p.name as product_name FROM product_batch pb JOIN product p ON pb.product_id=p.id {where} ORDER BY pb.received_date DESC",
        tuple(params)
    )
    return {"items": rows}

@router.post("/batch")
def create_batch(req: BatchRequest):
    """Create new product batch."""
    return execute_returning(
        """INSERT INTO product_batch (product_id, branch_id, batch_no, qty, cost_per_unit, expiry_date)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
        (req.product_id, req.branch_id, req.batch_no, req.qty, req.cost_per_unit, req.expiry_date)
    )


# ── BOM Management ────────────────────────────────────────────────

@router.get("/bom")
def list_boms(product_id: str = ""):
    """List Bill of Materials."""
    if product_id:
        boms = fetch_all("SELECT * FROM bom_header WHERE product_id = %s AND is_active = true", (product_id,))
    else:
        boms = fetch_all("SELECT bh.*, p.name as product_name FROM bom_header bh JOIN product p ON bh.product_id=p.id WHERE bh.is_active = true")
    
    for bom in boms:
        bom["components"] = fetch_all(
            "SELECT bc.*, p.name as component_name FROM bom_component bc JOIN product p ON bc.component_product_id=p.id WHERE bc.bom_id = %s",
            (bom["id"],)
        )
    return {"items": boms}

@router.post("/bom")
def create_bom(req: BOMRequest):
    """Create Bill of Materials."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO bom_header (product_id, name, description, standard_cost) VALUES (%s, %s, %s, %s) RETURNING *",
                (req.product_id, req.name, req.description, req.standard_cost)
            )
            bom = cur.fetchone()
            
            for comp in req.components:
                cur.execute(
                    "INSERT INTO bom_component (bom_id, component_product_id, qty, unit, cost_per_unit) VALUES (%s, %s, %s, %s, %s)",
                    (bom["id"], comp.component_product_id, comp.qty, comp.unit, comp.cost_per_unit)
                )
    
    return bom


# ── Inventory Alerts ─────────────────────────────────────────────

@router.get("/alerts")
def get_inventory_alerts(branch_id: str = "", threshold: float = 0):
    """Get inventory alerts — products below their min_stock_threshold."""
    where_parts = ["p.is_active = true"]
    params = []
    if branch_id:
        where_parts.append("sc.branch_id = %s")
        params.append(branch_id)
    where = " AND ".join(where_parts)

    items = fetch_all(
        f"""SELECT p.id, p.name, p.sku,
                COALESCE(sc.balance, 0) as balance,
                COALESCE(p.min_stock_threshold, 10) as threshold,
                sc.last_movement_date,
                CASE
                    WHEN COALESCE(sc.balance, 0) = 0 THEN 'out_of_stock'
                    WHEN COALESCE(sc.balance, 0) < COALESCE(p.min_stock_threshold, 10) * 0.5 THEN 'critical'
                    WHEN COALESCE(sc.balance, 0) < COALESCE(p.min_stock_threshold, 10) THEN 'low'
                    ELSE 'ok'
                END as alert_level
            FROM product p
            LEFT JOIN stock_card sc ON p.id = sc.product_id
            WHERE {where}
            ORDER BY
                CASE
                    WHEN COALESCE(sc.balance, 0) = 0 THEN 0
                    WHEN COALESCE(sc.balance, 0) < COALESCE(p.min_stock_threshold, 10) * 0.5 THEN 1
                    WHEN COALESCE(sc.balance, 0) < COALESCE(p.min_stock_threshold, 10) THEN 2
                    ELSE 3
                END,
                sc.balance ASC""",
        tuple(params),
    )

    # Apply custom threshold override if provided
    if threshold > 0:
        items = [i for i in items if i["balance"] < threshold]

    # Summary
    out_of_stock = sum(1 for i in items if i["alert_level"] == "out_of_stock")
    critical = sum(1 for i in items if i["alert_level"] == "critical")
    low = sum(1 for i in items if i["alert_level"] == "low")

    return {
        "items": items,
        "summary": {
            "out_of_stock": out_of_stock,
            "critical": critical,
            "low": low,
            "total_alerts": out_of_stock + critical + low,
        },
    }


class UpdateThresholdRequest(BaseModel):
    min_stock_threshold: float

@router.put("/product/{product_id}/threshold")
def update_product_threshold(product_id: str, req: UpdateThresholdRequest):
    """Update min_stock_threshold for a product."""
    result = execute_returning(
        "UPDATE product SET min_stock_threshold = %s WHERE id = %s RETURNING id, name, sku, min_stock_threshold",
        (req.min_stock_threshold, product_id),
    )
    if not result:
        raise HTTPException(404, "Product not found")
    return result
from pos_erp.db import get_conn
