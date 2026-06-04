"""Inventory Router - Beauty & Shine ERP."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])

def generate_doc_key(module: str, branch_code: str = "BSD") -> str:
    today = date.today().strftime("%Y%m%d")
    seq_key = f"SEQ-{module}-{branch_code}-2026"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE document_registry SET sequence = sequence + 1 WHERE doc_key = %s RETURNING sequence", (seq_key,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence) VALUES (%s, %s, %s, %s, 1) RETURNING sequence", (seq_key, module, branch_code, date.today()))
                row = cur.fetchone()
            return f"{module}-{branch_code}-{today}-{row['sequence']:04d}"

# ── Stock Card ────────────────────────────────────────────────────

@router.get("/stock-card")
def list_stock_cards(branch_id: str = "", q: str = "", offset: int = 0, limit: int = 50):
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
    if branch_id:
        return fetch_one("SELECT * FROM stock_card WHERE product_id=%s AND branch_id=%s", (product_id, branch_id))
    return fetch_all("SELECT sc.*, b.name as branch_name FROM stock_card sc LEFT JOIN branch b ON sc.branch_id=b.id WHERE sc.product_id=%s", (product_id,))

# ── Stock Movement ────────────────────────────────────────────────

@router.get("/movements")
def list_movements(product_id: str = "", branch_id: str = "", movement_type: str = "", offset: int = 0, limit: int = 50):
    conditions = []
    params = []
    if product_id:
        conditions.append("sm.product_id = %s")
        params.append(product_id)
    if branch_id:
        conditions.append("sm.branch_id = %s")
        params.append(branch_id)
    if movement_type:
        conditions.append("sm.movement_type = %s")
        params.append(movement_type)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    rows = fetch_all(
        f"""SELECT sm.*, p.name as product_name, p.sku, b.name as branch_name
            FROM stock_movement sm
            JOIN product p ON sm.product_id=p.id
            LEFT JOIN branch b ON sm.branch_id=b.id
            {where} ORDER BY sm.created_at DESC LIMIT %s OFFSET %s""",
        tuple(params)
    )
    return {"items": rows}

# ── Stock In ──────────────────────────────────────────────────────

class StockInRequest(BaseModel):
    product_id: str
    branch_id: str
    batch_id: Optional[str] = None
    qty: float
    notes: Optional[str] = None

@router.post("/stock-in")
def stock_in(req: StockInRequest):
    doc_key = generate_doc_key("STK")
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Create movement
            cur.execute(
                """INSERT INTO stock_movement (doc_key, product_id, batch_id, branch_id, movement_type, qty, notes)
                   VALUES (%s, %s, %s, %s, 'in', %s, %s) RETURNING *""",
                (doc_key, req.product_id, req.batch_id, req.branch_id, req.qty, req.notes)
            )
            movement = cur.fetchone()
            
            # Update or create stock card
            cur.execute("SELECT * FROM stock_card WHERE product_id=%s AND branch_id=%s", (req.product_id, req.branch_id))
            card = cur.fetchone()
            if card:
                new_balance = float(card["balance"]) + req.qty
                cur.execute(
                    "UPDATE stock_card SET qty_in=qty_in+%s, balance=%s, last_movement_date=%s WHERE id=%s",
                    (req.qty, new_balance, date.today(), card["id"])
                )
            else:
                cur.execute(
                    """INSERT INTO stock_card (product_id, branch_id, qty_in, qty_out, balance, last_movement_date)
                       VALUES (%s, %s, %s, 0, %s, %s)""",
                    (req.product_id, req.branch_id, req.qty, req.qty, date.today())
                )
            
            # Update batch qty if specified
            if req.batch_id:
                cur.execute("UPDATE product_batch SET qty = qty + %s WHERE id = %s", (req.qty, req.batch_id))
    
    return movement

# ── Stock Out ─────────────────────────────────────────────────────

class StockOutRequest(BaseModel):
    product_id: str
    branch_id: str
    qty: float
    notes: Optional[str] = None

@router.post("/stock-out")
def stock_out(req: StockOutRequest):
    card = fetch_one("SELECT * FROM stock_card WHERE product_id=%s AND branch_id=%s", (req.product_id, req.branch_id))
    if not card or float(card["balance"]) < req.qty:
        raise HTTPException(400, "Insufficient stock")
    
    doc_key = generate_doc_key("STK")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO stock_movement (doc_key, product_id, branch_id, movement_type, qty, notes)
                   VALUES (%s, %s, %s, 'out', %s, %s) RETURNING *""",
                (doc_key, req.product_id, req.branch_id, req.qty, req.notes)
            )
            movement = cur.fetchone()
            
            new_balance = float(card["balance"]) - req.qty
            cur.execute(
                "UPDATE stock_card SET qty_out=qty_out+%s, balance=%s, last_movement_date=%s WHERE id=%s",
                (req.qty, new_balance, date.today(), card["id"])
            )
    
    return movement

# ── Stock Opname ──────────────────────────────────────────────────

@router.get("/opnames")
def list_opnames(branch_id: str = "", offset: int = 0, limit: int = 50):
    extra = "WHERE so.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()
    rows = fetch_all(
        f"SELECT so.*, b.name as branch_name FROM stock_opname so LEFT JOIN branch b ON so.branch_id=b.id {extra} ORDER BY so.opname_date DESC LIMIT %s OFFSET %s",
        (*params, limit, offset)
    )
    return {"items": rows}

class OpnameItemReq(BaseModel):
    product_id: str
    system_qty: float
    actual_qty: float
    notes: Optional[str] = None

class OpnameRequest(BaseModel):
    branch_id: str
    items: list[OpnameItemReq]

@router.post("/opname")
def create_opname(req: OpnameRequest):
    doc_key = generate_doc_key("STK")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO stock_opname (doc_key, branch_id, opname_date, status) VALUES (%s, %s, %s, 'draft') RETURNING *",
                (doc_key, req.branch_id, date.today())
            )
            opname = cur.fetchone()
            for item in req.items:
                diff = item.actual_qty - item.system_qty
                cur.execute(
                    """INSERT INTO stock_opname_item (opname_id, product_id, system_qty, actual_qty, difference, notes)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (opname["id"], item.product_id, item.system_qty, item.actual_qty, diff, item.notes)
                )
    return opname

@router.put("/opname/{id}/approve")
def approve_opname(id: str):
    execute("UPDATE stock_opname SET status='approved' WHERE id=%s", (id,))
    return fetch_one("SELECT * FROM stock_opname WHERE id=%s", (id,))

# ── Low Stock ─────────────────────────────────────────────────────

@router.get("/low-stock")
def get_low_stock(threshold: float = 10, branch_id: str = ""):
    extra = "AND sc.branch_id = %s" if branch_id else ""
    params = (threshold,) + ((branch_id,) if branch_id else ())
    rows = fetch_all(
        f"""SELECT sc.*, p.name as product_name, p.sku, b.name as branch_name
            FROM stock_card sc
            JOIN product p ON sc.product_id=p.id
            LEFT JOIN branch b ON sc.branch_id=b.id
            WHERE sc.balance < %s {extra} ORDER BY sc.balance ASC""",
        params
    )
    return {"items": rows}
