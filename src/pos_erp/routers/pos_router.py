"""POS Transaction Router - Beauty & Shine ERP."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from datetime import date, datetime, timezone, timedelta
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

WIB = timezone(timedelta(hours=7))

def _wib_today() -> date:
    """Return today's date in WIB (UTC+7)."""
    return datetime.now(WIB).date()

router = APIRouter(prefix="/api/pos", tags=["POS"])

# ── Helper: Generate Doc Key ──────────────────────────────────────

def generate_doc_key(module: str, branch_code: str = "BSD") -> str:
    """Generate unique doc key: MODULE-BRANCH-YYYYMMDD-NNNN"""
    today = _wib_today().strftime("%Y%m%d")
    seq_key = f"SEQ-{module}-{branch_code}-2026"
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE document_registry SET sequence = sequence + 1 WHERE doc_key = %s RETURNING sequence",
                (seq_key,)
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence) VALUES (%s, %s, %s, %s, 1) RETURNING sequence",
                    (seq_key, module, branch_code, _wib_today())
                )
                row = cur.fetchone()
            seq = row["sequence"]
    
    return f"{module}-{branch_code}-{today}-{seq:04d}"

# ── Booking ───────────────────────────────────────────────────────

class BookingRequest(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    treatment_ids: list[str]
    bed_id: Optional[str] = None
    therapist_id: Optional[str] = None
    branch_id: Optional[str] = None
    booking_date: Optional[str] = None
    booking_time: Optional[str] = None
    notes: Optional[str] = None

@router.post("/booking")
def create_booking(req: BookingRequest):
    doc_key = generate_doc_key("BOOK")
    branch_id = req.branch_id or fetch_one("SELECT id FROM branch WHERE code = 'BSD'")["id"]
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Create transaction
            cur.execute(
                """INSERT INTO pos_transaction (doc_key, branch_id, customer_name, customer_phone, status, cashier_id, booking_date, booking_time, notes)
                   VALUES (%s, %s, %s, %s, 'booked', %s, %s, %s, %s) RETURNING *""",
                (doc_key, branch_id, req.customer_name, req.customer_phone, req.therapist_id,
                 req.booking_date or None, req.booking_time or None, req.notes or None)
            )
            txn = cur.fetchone()
            
            subtotal = 0
            # Add treatment items
            for tid in req.treatment_ids:
                cur.execute("SELECT * FROM treatment WHERE id = %s", (tid,))
                treatment = cur.fetchone()
                if not treatment:
                    raise HTTPException(404, f"Treatment {tid} not found")
                
                cur.execute(
                    """INSERT INTO pos_transaction_item (transaction_id, item_type, item_id, item_name, qty, unit_price, total)
                       VALUES (%s, 'treatment', %s, %s, 1, %s, %s)""",
                    (txn["id"], tid, treatment["name"], treatment["price"], treatment["price"])
                )
                subtotal += treatment["price"]
                
                # Create treatment record
                trm_key = generate_doc_key("TRM")
                cur.execute(
                    """INSERT INTO treatment_record (doc_key, transaction_id, treatment_id, therapist_id, bed_id, status)
                       VALUES (%s, %s, %s, %s, %s, 'scheduled')""",
                    (trm_key, txn["id"], tid, req.therapist_id, req.bed_id)
                )
            
            # Update transaction totals
            tax = subtotal * 0.11
            total = subtotal + tax
            cur.execute(
                "UPDATE pos_transaction SET subtotal=%s, tax=%s, total=%s WHERE id=%s",
                (subtotal, tax, total, txn["id"])
            )
            
            # Reserve bed if specified
            if req.bed_id:
                cur.execute("UPDATE bed SET status = 'occupied' WHERE id = %s", (req.bed_id,))
    
    return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (txn["id"],))

# ── Transaction ───────────────────────────────────────────────────

@router.get("/transaction/{id}")
def get_transaction(id: str):
    txn = fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    items = fetch_all("SELECT * FROM pos_transaction_item WHERE transaction_id = %s", (id,))
    txn["items"] = items
    return txn

@router.get("/transactions")
def list_transactions(branch_id: str = "", status: str = "", date_from: str = "", date_to: str = "", q: str = "", offset: int = 0, limit: int = 50):
    conditions = []
    params = []
    if branch_id:
        conditions.append("t.branch_id = %s")
        params.append(branch_id)
    if status:
        conditions.append("t.status = %s")
        params.append(status)
    if date_from:
        conditions.append("t.created_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("t.created_at <= %s")
        params.append(date_to + " 23:59:59")
    if q:
        conditions.append("(t.customer_name ILIKE %s OR t.doc_key ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    
    rows = fetch_all(
        f"SELECT t.*, b.name as branch_name FROM pos_transaction t LEFT JOIN branch b ON t.branch_id=b.id {where} ORDER BY t.created_at DESC LIMIT %s OFFSET %s",
        tuple(params)
    )
    count = fetch_one(f"SELECT count(*) as total FROM pos_transaction t {where}", tuple(params[:-2]) if params else ())
    return {"items": rows, "total": count["total"] if count else 0}

# ── Add/Remove Item ───────────────────────────────────────────────

class AddItemRequest(BaseModel):
    item_type: str  # treatment / product
    item_id: str
    qty: int = 1

@router.post("/transaction/{id}/add-item")
def add_item(id: str, req: AddItemRequest):
    txn = fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    if req.item_type == "treatment":
        item = fetch_one("SELECT * FROM treatment WHERE id = %s", (req.item_id,))
        if not item:
            raise HTTPException(404, "Treatment not found")
        name, price = item["name"], item["price"]
    else:
        item = fetch_one("SELECT * FROM product WHERE id = %s", (req.item_id,))
        if not item:
            raise HTTPException(404, "Product not found")
        name = item["name"]
        pricelist = fetch_one("SELECT price FROM product_pricelist WHERE product_id = %s AND is_active = true", (req.item_id,))
        price = pricelist["price"] if pricelist else 0
    
    total = price * req.qty
    
    execute_returning(
        """INSERT INTO pos_transaction_item (transaction_id, item_type, item_id, item_name, qty, unit_price, total)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
        (id, req.item_type, req.item_id, name, req.qty, price, total)
    )
    
    # Recalculate totals
    items = fetch_all("SELECT SUM(total) as subtotal FROM pos_transaction_item WHERE transaction_id = %s", (id,))
    subtotal = float(items[0]["subtotal"] or 0)
    tax = subtotal * 0.11
    total = subtotal + tax
    execute("UPDATE pos_transaction SET subtotal=%s, tax=%s, total=%s WHERE id=%s", (subtotal, tax, total, id))
    
    return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))

class RemoveItemRequest(BaseModel):
    item_id: str

@router.post("/transaction/{id}/remove-item")
def remove_item(id: str, req: RemoveItemRequest):
    execute("DELETE FROM pos_transaction_item WHERE id = %s AND transaction_id = %s", (req.item_id, id))
    
    items = fetch_all("SELECT SUM(total) as subtotal FROM pos_transaction_item WHERE transaction_id = %s", (id,))
    subtotal = float(items[0]["subtotal"] or 0)
    tax = subtotal * 0.11
    total = subtotal + tax
    execute("UPDATE pos_transaction SET subtotal=%s, tax=%s, total=%s WHERE id=%s", (subtotal, tax, total, id))
    
    return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))

# ── Discount ──────────────────────────────────────────────────────

class DiscountRequest(BaseModel):
    type: str  # percentage / fixed
    value: float

@router.post("/transaction/{id}/apply-discount")
def apply_discount(id: str, req: DiscountRequest):
    txn = fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    if req.type == "percentage":
        discount = float(txn["subtotal"]) * req.value / 100
    else:
        discount = req.value
    
    total = float(txn["subtotal"]) - discount + float(txn["tax"])
    execute("UPDATE pos_transaction SET discount=%s, total=%s WHERE id=%s", (discount, total, id))
    return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))

# ── Voucher ───────────────────────────────────────────────────────

class VoucherRequest(BaseModel):
    code: str

@router.post("/transaction/{id}/apply-voucher")
def apply_voucher(id: str, req: VoucherRequest):
    voucher = fetch_one("SELECT * FROM voucher WHERE code = %s AND is_active = true", (req.code,))
    if not voucher:
        raise HTTPException(404, "Voucher not found or inactive")
    
    txn = fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    if voucher["type"] == "percentage":
        discount = float(txn["subtotal"]) * float(voucher["value"]) / 100
    else:
        discount = float(voucher["value"])
    
    total = float(txn["subtotal"]) - discount + float(txn["tax"])
    execute("UPDATE pos_transaction SET discount=%s, total=%s WHERE id=%s", (discount, total, id))
    execute("UPDATE voucher SET used_count = used_count + 1 WHERE id = %s", (voucher["id"],))
    
    return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))

# ── Payment ───────────────────────────────────────────────────────

class PaymentRequest(BaseModel):
    payment_method_id: str

@router.post("/transaction/{id}/payment")
def process_payment(id: str, req: PaymentRequest):
    txn = fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if txn["status"] == "paid":
        raise HTTPException(400, "Transaction already paid")
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pos_transaction SET status='paid', payment_method_id=%s WHERE id=%s",
                (req.payment_method_id, id)
            )
            
            # Create journal entry for revenue
            je_key = generate_doc_key("JE")
            cur.execute(
                """INSERT INTO journal_entry (doc_key, branch_id, entry_date, description, status, total_debit, total_credit, created_by)
                   VALUES (%s, %s, %s, %s, 'posted', %s, %s, %s) RETURNING id""",
                (je_key, txn["branch_id"], _wib_today(), f"POS Sale {txn['doc_key']}", float(txn["total"]), float(txn["total"]), txn.get("cashier_id"))
            )
            je = cur.fetchone()
            
            # Debit: Cash/Bank
            cur.execute(
                """INSERT INTO journal_entry_line (journal_entry_id, account_code, debit, credit, description)
                   VALUES (%s, '1001', %s, 0, %s)""",
                (je["id"], float(txn["total"]), f"Payment for {txn['doc_key']}")
            )
            # Credit: Revenue
            cur.execute(
                """INSERT INTO journal_entry_line (journal_entry_id, account_code, debit, credit, description)
                   VALUES (%s, '4001', 0, %s, %s)""",
                (je["id"], float(txn["total"]), f"Revenue from {txn['doc_key']}")
            )
    
    return fetch_one("SELECT * FROM pos_transaction WHERE id = %s", (id,))

# ── Daily Closing ─────────────────────────────────────────────────

@router.post("/daily-closing")
def create_daily_closing(branch_id: str = "", closing_date: str = ""):
    if not branch_id:
        branch_id = fetch_one("SELECT id FROM branch WHERE code = 'BSD'")["id"]
    if not closing_date:
        closing_date = _wib_today().isoformat()
    
    doc_key = generate_doc_key("CLO")
    
    # Get all paid transactions for the day
    txns = fetch_all(
        """SELECT t.*, pm.type as payment_type FROM pos_transaction t
           LEFT JOIN payment_method pm ON t.payment_method_id = pm.id
           WHERE t.branch_id = %s AND t.status = 'paid' AND DATE(t.created_at) = %s""",
        (branch_id, closing_date)
    )
    
    total_cash = sum(float(t["total"]) for t in txns if t.get("payment_type") == "cash")
    total_card = sum(float(t["total"]) for t in txns if t.get("payment_type") == "card")
    total_transfer = sum(float(t["total"]) for t in txns if t.get("payment_type") == "bank_transfer")
    total_other = sum(float(t["total"]) for t in txns if t.get("payment_type") not in ("cash", "card", "bank_transfer"))
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO pos_daily_closing (doc_key, branch_id, closing_date, total_cash, total_card, total_transfer, total_other, total_transactions, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft') RETURNING *""",
                (doc_key, branch_id, closing_date, total_cash, total_card, total_transfer, total_other, len(txns))
            )
            closing = cur.fetchone()
            
            for txn in txns:
                cur.execute(
                    "INSERT INTO pos_daily_closing_detail (closing_id, transaction_id, amount) VALUES (%s, %s, %s)",
                    (closing["id"], txn["id"], txn["total"])
                )
    
    return closing

@router.get("/daily-closing/{id}")
def get_daily_closing(id: str):
    closing = fetch_one("SELECT * FROM pos_daily_closing WHERE id = %s", (id,))
    if not closing:
        raise HTTPException(404, "Closing not found")
    details = fetch_all(
        "SELECT d.*, t.doc_key, t.customer_name FROM pos_daily_closing_detail d JOIN pos_transaction t ON d.transaction_id=t.id WHERE d.closing_id = %s",
        (id,)
    )
    closing["details"] = details
    return closing

@router.get("/daily-closings")
def list_daily_closings(branch_id: str = "", offset: int = 0, limit: int = 50):
    extra = "WHERE c.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()
    rows = fetch_all(
        f"SELECT c.*, b.name as branch_name FROM pos_daily_closing c LEFT JOIN branch b ON c.branch_id=b.id {extra} ORDER BY c.closing_date DESC LIMIT %s OFFSET %s",
        (*params, limit, offset)
    )
    return {"items": rows}

@router.put("/daily-closing/{id}/submit")
def submit_daily_closing(id: str):
    execute("UPDATE pos_daily_closing SET status='submitted' WHERE id = %s", (id,))
    return fetch_one("SELECT * FROM pos_daily_closing WHERE id = %s", (id,))

# ── Beds ──────────────────────────────────────────────────────────

@router.get("/beds")
def list_beds(branch_id: str = ""):
    extra = "WHERE bs.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()
    rows = fetch_all(
        f"SELECT b.*, bs.name as section_name FROM bed b JOIN bed_section bs ON b.section_id=bs.id {extra} ORDER BY bs.name, b.name",
        params
    )
    return {"items": rows}

@router.put("/bed/{id}/status")
def update_bed_status(id: str, status: str = "available"):
    execute("UPDATE bed SET status=%s WHERE id=%s", (status, id))
    return fetch_one("SELECT * FROM bed WHERE id = %s", (id,))
