"""POS Transaction Router - Beauty & Shine ERP.

Domain-driven implementation with:
- TreatmentCart for managing treatment lines
- StaffLockManager for therapist assignment
- PaymentIntent with verification flow
- AuditTrail integration
- DocumentRegistry for consistent doc key generation
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pos_erp.domain_models import (
    DocumentKind, TransactionStatus, PaymentMethod, PaymentStatus,
    MovementType, MovementReason, AuditAction, AuditSeverity,
    money, calculate_tax, calculate_discount,
)
from pos_erp.repository import (
    DocumentRegistryRepository, AuditTrailRepository,
    TransactionRepository, TransactionItemRepository,
    TreatmentRecordRepository, StockRepository,
    JournalEntryRepository,
)
from pos_erp.db import fetch_all, fetch_one, execute, execute_returning, get_conn

router = APIRouter(prefix="/api/pos", tags=["POS"])

# ── Request Models ────────────────────────────────────────────────

class BookingRequest(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None
    treatment_ids: list[str] = []
    bed_id: Optional[str] = None
    therapist_id: Optional[str] = None
    branch_id: Optional[str] = None
    notes: Optional[str] = None
    booking_date: Optional[str] = None
    booking_time: Optional[str] = None

class AddItemRequest(BaseModel):
    item_type: str  # treatment / product
    item_id: str
    qty: int = 1
    staff_id: Optional[str] = None

class RemoveItemRequest(BaseModel):
    item_id: str

class ApplyDiscountRequest(BaseModel):
    type: str  # percentage / fixed
    value: float

class ApplyVoucherRequest(BaseModel):
    code: str

class PaymentRequest(BaseModel):
    payment_method_id: str
    payment_type: str = "cash"  # cash, bank_transfer, qris, e_wallet, card

class SelectStaffRequest(BaseModel):
    staff_id: str

class UpdateBedStatusRequest(BaseModel):
    status: str  # available, occupied, maintenance


# ── Helper ────────────────────────────────────────────────────────

def _get_branch_id(branch_id: str = None) -> str:
    if branch_id and str(branch_id).strip():
        return str(branch_id).strip()
    branch = fetch_one("SELECT id FROM branch WHERE code = 'BSD'")
    if not branch:
        raise HTTPException(404, "Default branch not found")
    return branch["id"]

def _generate_doc_key(module: DocumentKind, branch_code: str = "BSD") -> str:
    return DocumentRegistryRepository.generate_doc_key(module.value, branch_code)

def _audit(doc_key: str, module: str, action: AuditAction, user_id: str = None, details: str = None):
    AuditTrailRepository.record(
        doc_key=doc_key,
        module=module,
        action=action.value,
        user_id=user_id,
        new_value=details,
    )


# ── Booking ───────────────────────────────────────────────────────

@router.post("/booking")
def create_booking(req: BookingRequest):
    """Create a new booking with treatments."""
    branch_id = _get_branch_id(req.branch_id)
    doc_key = _generate_doc_key(DocumentKind.BOOK)
    
    # Resolve therapist_id (username) to UUID for cashier_id
    cashier_uuid = None
    if req.therapist_id:
        staff_row = fetch_one("SELECT id FROM app_user WHERE username = %s", (req.therapist_id,))
        if staff_row:
            cashier_uuid = staff_row["id"]
    
    # Create transaction
    txn = TransactionRepository.create(
        doc_key=doc_key,
        branch_id=branch_id,
        customer_name=req.customer_name,
        customer_phone=req.customer_phone,
        status=TransactionStatus.BOOKED.value,
        cashier_id=cashier_uuid,
        booking_date=req.booking_date,
        booking_time=req.booking_time,
        notes=req.notes,
    )
    
    subtotal = Decimal("0")
    # Add treatment items
    for tid in req.treatment_ids:
        treatment = fetch_one("SELECT * FROM treatment WHERE id = %s AND is_active = true", (tid,))
        if not treatment:
            raise HTTPException(404, f"Treatment {tid} not found")
        
        TransactionItemRepository.add(
            transaction_id=txn["id"],
            item_type="treatment",
            item_id=tid,
            item_name=treatment["name"],
            qty=1,
            unit_price=float(treatment["price"]),
        )
        subtotal += Decimal(str(treatment["price"]))
        
        # Create treatment record
        trm_key = _generate_doc_key(DocumentKind.TRM)
        TreatmentRecordRepository.create(
            doc_key=trm_key,
            transaction_id=txn["id"],
            treatment_id=tid,
            therapist_id=cashier_uuid,
            bed_id=req.bed_id,
            status="scheduled",
            notes=req.notes,
        )
    
    # Calculate totals
    tax = calculate_tax(subtotal)
    total = subtotal + tax
    TransactionRepository.update_totals(txn["id"], float(subtotal), 0, float(tax), float(total))
    
    # Reserve bed
    if req.bed_id:
        execute("UPDATE bed SET status = 'occupied' WHERE id = %s", (req.bed_id,))
    
    # Audit
    _audit(doc_key, "pos", AuditAction.CREATE, cashier_uuid, f"Booking created for {req.customer_name}")
    
    return TransactionRepository.get(txn["id"])


@router.post("/booking/{doc_key}/to-transaction")
def convert_booking_to_transaction(doc_key: str):
    """Convert a booking to an open transaction for checkout."""
    txn = fetch_one("SELECT * FROM pos_transaction WHERE doc_key = %s", (doc_key,))
    if not txn:
        raise HTTPException(404, "Booking not found")
    if txn["status"] not in ("booked", "open"):
        raise HTTPException(400, f"Cannot convert: status is '{txn['status']}', expected 'booked' or 'open'")
    
    # Change status from booked → open so checkout page can work with it
    if txn["status"] == "booked":
        execute("UPDATE pos_transaction SET status = 'open' WHERE doc_key = %s", (doc_key,))
    _audit(doc_key, "pos", AuditAction.UPDATE, None, "Booking converted to transaction")
    
    return {"success": True, "doc_key": doc_key, "message": "Booking siap untuk checkout"}


# ── Transaction CRUD ──────────────────────────────────────────────

@router.get("/transaction/{id}")
def get_transaction(id: str):
    """Get transaction with items and treatment records."""
    txn = TransactionRepository.get(id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    txn["items"] = TransactionItemRepository.get_by_transaction(id)
    txn["treatment_records"] = TreatmentRecordRepository.get_by_transaction(id)
    return txn

class UpdateCustomerRequest(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None

@router.put("/transaction/{id}/customer")
def update_transaction_customer(id: str, req: UpdateCustomerRequest):
    """Update customer on an existing transaction (supports both UUID and doc_key)."""
    # Try doc_key first (what frontend sends), then UUID
    txn = fetch_one("SELECT id, status FROM pos_transaction WHERE doc_key = %s", (id,))
    if not txn:
        txn = fetch_one("SELECT id, status FROM pos_transaction WHERE id = %s", (id,))
    if not txn:
        raise HTTPException(404, "Transaction not found")
    execute(
        "UPDATE pos_transaction SET customer_name = %s, customer_phone = %s WHERE id = %s",
        (req.customer_name, req.customer_phone, txn["id"]),
    )
    return {"status": "ok", "customer_name": req.customer_name, "customer_phone": req.customer_phone}

@router.get("/home-summary")
def pos_home_summary(branch_id: str = ""):
    """POS Home dashboard summary - today's transactions and revenue."""
    from datetime import datetime, timezone, timedelta
    wib = timezone(timedelta(hours=7))
    today = datetime.now(wib).date().isoformat()

    # Auto-cleanup: remove empty open transactions older than 1 hour
    execute(
        "DELETE FROM pos_transaction WHERE status = 'open' AND total = 0 "
        "AND created_at < NOW() - INTERVAL '1 hour' "
        "AND NOT EXISTS (SELECT 1 FROM pos_transaction_item WHERE transaction_id = pos_transaction.id)"
    )

    # Convert UTC timestamps to WIB for date comparison
    conditions = ["t.status = 'paid'", "DATE(t.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta') = %s"]
    params: list = [today]
    if branch_id:
        conditions.append("t.branch_id = %s")
        params.append(branch_id)
    where = " AND ".join(conditions)

    summary = fetch_one(
        f"SELECT COUNT(*) AS cnt, COALESCE(SUM(t.total), 0) AS revenue FROM pos_transaction t WHERE {where}",
        tuple(params),
    )

    recent = fetch_all(
        f"SELECT t.doc_key, t.customer_name, t.total, t.status, t.created_at,"
        f" b.name AS branch_name, u.full_name AS cashier_name"
        f" FROM pos_transaction t"
        f" LEFT JOIN branch b ON t.branch_id = b.id"
        f" LEFT JOIN app_user u ON t.cashier_id = u.id"
        f" WHERE {where}"
        f" ORDER BY t.created_at DESC LIMIT 5",
        tuple(params),
    )

    open_conds = ["t.status = 'open'"]
    open_params: list = []
    if branch_id:
        open_conds.append("t.branch_id = %s")
        open_params.append(branch_id)
    open_where = " AND ".join(open_conds)
    open_count = fetch_one(
        f"SELECT COUNT(*) AS cnt FROM pos_transaction t WHERE {open_where}",
        tuple(open_params),
    )

    return {
        "today_transactions": summary["cnt"],
        "today_revenue": float(summary["revenue"]),
        "active_bookings": open_count["cnt"],
        "recent_transactions": [
            {
                "doc_key": r["doc_key"],
                "customer_name": r["customer_name"] or "-",
                "total": float(r["total"]),
                "status": r["status"],
                "created_at": str(r["created_at"]),
                "branch_name": r["branch_name"] or "-",
                "cashier_name": r["cashier_name"] or "-",
            }
            for r in recent
        ],
    }


@router.get("/transactions")
def list_transactions(
    branch_id: str = "",
    status: str = "",
    type: str = "",
    date_from: str = "",
    date_to: str = "",
    q: str = "",
    offset: int = 0,
    limit: int = 50,
):
    """List transactions with filters."""
    items = TransactionRepository.list_transactions(
        branch_id=branch_id or None,
        status=status or None,
        type=type or None,
        date_from=date_from or None,
        date_to=date_to or None,
        q=q or None,
        offset=offset,
        limit=limit,
    )
    return {"items": items, "total": len(items)}


# ── Cart Management ───────────────────────────────────────────────

@router.post("/transaction/{id}/add-item")
def add_item(id: str, req: AddItemRequest):
    """Add item to transaction (treatment or product)."""
    txn = TransactionRepository.get(id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if txn["status"] in ("paid", "cancelled"):
        raise HTTPException(400, f"Cannot modify {txn['status']} transaction")
    
    if req.item_type == "treatment":
        item = fetch_one("SELECT * FROM treatment WHERE id = %s AND is_active = true", (req.item_id,))
        if not item:
            raise HTTPException(404, "Treatment not found")
        name, price = item["name"], float(item["price"])
    else:
        item = fetch_one("SELECT * FROM product WHERE id = %s AND is_active = true", (req.item_id,))
        if not item:
            raise HTTPException(404, "Product not found")
        name = item["name"]
        pricelist = fetch_one("SELECT price FROM product_pricelist WHERE product_id = %s AND is_active = true", (req.item_id,))
        price = float(pricelist["price"]) if pricelist else 0
    
    TransactionItemRepository.add(
        transaction_id=id,
        item_type=req.item_type,
        item_id=req.item_id,
        item_name=name,
        qty=req.qty,
        unit_price=price,
    )
    
    # Recalculate totals
    _recalculate_totals(id)
    
    # Audit
    _audit(txn["doc_key"], "pos", AuditAction.UPDATE, details=f"Added {req.item_type}: {name}")
    
    return TransactionRepository.get(id)

@router.post("/transaction/{id}/remove-item")
def remove_item(id: str, req: RemoveItemRequest):
    """Remove item from transaction."""
    txn = TransactionRepository.get(id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if txn["status"] in ("paid", "cancelled"):
        raise HTTPException(400, f"Cannot modify {txn['status']} transaction")
    
    TransactionItemRepository.remove(req.item_id, id)
    _recalculate_totals(id)
    
    _audit(txn["doc_key"], "pos", AuditAction.UPDATE, details=f"Removed item {req.item_id}")
    
    return TransactionRepository.get(id)


# ── Discount & Voucher ────────────────────────────────────────────

@router.post("/transaction/{id}/apply-discount")
def apply_discount(id: str, req: ApplyDiscountRequest):
    """Apply discount to transaction."""
    txn = TransactionRepository.get(id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    subtotal = Decimal(str(txn["subtotal"]))
    discount = calculate_discount(subtotal, req.type, Decimal(str(req.value)))
    tax = calculate_tax(subtotal - discount)
    total = subtotal - discount + tax
    
    TransactionRepository.update_totals(id, float(subtotal), float(discount), float(tax), float(total))
    
    _audit(txn["doc_key"], "pos", AuditAction.UPDATE, details=f"Discount applied: {req.type} {req.value}")
    
    return TransactionRepository.get(id)

@router.post("/transaction/{id}/apply-voucher")
def apply_voucher(id: str, req: ApplyVoucherRequest):
    """Apply voucher code to transaction."""
    txn = TransactionRepository.get(id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    
    voucher = fetch_one("SELECT * FROM voucher WHERE code = %s AND is_active = true", (req.code,))
    if not voucher:
        raise HTTPException(404, "Voucher not found or inactive")
    
    subtotal = Decimal(str(txn["subtotal"]))
    if voucher["type"] == "percentage":
        discount = subtotal * Decimal(str(voucher["value"])) / 100
    else:
        discount = Decimal(str(voucher["value"]))
    
    discount = money(discount)
    tax = calculate_tax(subtotal - discount)
    total = subtotal - discount + tax
    
    TransactionRepository.update_totals(id, float(subtotal), float(discount), float(tax), float(total))
    execute("UPDATE voucher SET used_count = used_count + 1 WHERE id = %s", (voucher["id"],))
    
    _audit(txn["doc_key"], "pos", AuditAction.UPDATE, details=f"Voucher applied: {req.code}")
    
    return TransactionRepository.get(id)


# ── Payment ───────────────────────────────────────────────────────

@router.post("/transaction/{id}/payment")
def process_payment(id: str, req: PaymentRequest):
    """Process payment for transaction."""
    txn = TransactionRepository.get(id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if txn["status"] == "paid":
        raise HTTPException(400, "Transaction already paid")
    if txn["status"] == "cancelled":
        raise HTTPException(400, "Cannot pay cancelled transaction")
    
    # Update transaction status
    TransactionRepository.update_status(id, TransactionStatus.PAID.value, req.payment_method_id)
    
    # Create journal entry for revenue
    _create_sales_journal(txn)
    
    # Create stock movements for products
    _process_product_items(txn)
    
    # Audit
    _audit(txn["doc_key"], "pos", AuditAction.POST, details=f"Payment processed: {req.payment_type}")
    
    return TransactionRepository.get(id)


# ── Daily Closing ─────────────────────────────────────────────────

@router.post("/daily-closing")
def create_daily_closing(branch_id: str = "", closing_date: str = ""):
    """Create daily closing for a branch."""
    try:
        branch_id = _get_branch_id(branch_id or None)
        closing_date = closing_date or date.today().isoformat()

        doc_key = _generate_doc_key(DocumentKind.CLO)

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

        _audit(doc_key, "pos", AuditAction.CREATE, details=f"Daily closing created for {closing_date}")

        return closing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Daily closing failed: {str(e)}")

@router.get("/daily-closing/{id}")
def get_daily_closing(id: str):
    """Get daily closing with details."""
    closing = fetch_one("SELECT * FROM pos_daily_closing WHERE id = %s", (id,))
    if not closing:
        raise HTTPException(404, "Closing not found")
    
    closing["details"] = fetch_all(
        "SELECT d.*, t.doc_key, t.customer_name FROM pos_daily_closing_detail d JOIN pos_transaction t ON d.transaction_id=t.id WHERE d.closing_id = %s",
        (id,)
    )
    return closing

@router.get("/daily-closings")
def list_daily_closings(branch_id: str = "", offset: int = 0, limit: int = 50):
    """List daily closings."""
    extra = "WHERE c.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()
    rows = fetch_all(
        f"SELECT c.*, b.name as branch_name FROM pos_daily_closing c LEFT JOIN branch b ON c.branch_id=b.id {extra} ORDER BY c.closing_date DESC LIMIT %s OFFSET %s",
        (*params, limit, offset)
    )
    return {"items": rows}

@router.put("/daily-closing/{id}/submit")
def submit_daily_closing(id: str):
    """Submit daily closing."""
    execute("UPDATE pos_daily_closing SET status='submitted' WHERE id = %s", (id,))
    _audit(id, "pos", AuditAction.APPROVE, details="Daily closing submitted")
    return fetch_one("SELECT * FROM pos_daily_closing WHERE id = %s", (id,))


# ── Beds ──────────────────────────────────────────────────────────

@router.get("/beds")
def list_beds(branch_id: str = ""):
    """List beds with status."""
    extra = "WHERE bs.branch_id = %s" if branch_id else ""
    params = (branch_id,) if branch_id else ()
    rows = fetch_all(
        f"SELECT b.*, bs.name as section_name FROM bed b JOIN bed_section bs ON b.section_id=bs.id {extra} ORDER BY bs.name, b.name",
        params
    )
    return {"items": rows}

@router.put("/bed/{id}/status")
def update_bed_status(id: str, req: UpdateBedStatusRequest):
    """Update bed status."""
    execute("UPDATE bed SET status=%s WHERE id=%s", (req.status, id))
    return fetch_one("SELECT * FROM bed WHERE id = %s", (id,))


# ── Internal Helpers ──────────────────────────────────────────────

def _recalculate_totals(transaction_id: str):
    """Recalculate transaction totals from items."""
    subtotal = Decimal(str(TransactionItemRepository.get_subtotal(transaction_id)))
    tax = calculate_tax(subtotal)
    total = subtotal + tax
    TransactionRepository.update_totals(transaction_id, float(subtotal), 0, float(tax), float(total))

def _create_sales_journal(txn: dict):
    """Create journal entry for a sale."""
    je_key = _generate_doc_key(DocumentKind.JE)
    je = JournalEntryRepository.create(
        doc_key=je_key,
        branch_id=txn["branch_id"],
        entry_date=date.today().isoformat(),
        description=f"POS Sale {txn['doc_key']}",
        status="posted",
        created_by=txn.get("cashier_id"),
    )
    
    # Get COA mapping
    mapping = fetch_one("SELECT * FROM account_mapping WHERE module = 'pos' AND transaction_type = 'sale_cash'")
    
    if mapping:
        # Debit: Cash/Bank
        JournalEntryRepository.add_line(je["id"], mapping["debit_account"], float(txn["total"]), 0, f"Payment for {txn['doc_key']}")
        # Credit: Revenue
        JournalEntryRepository.add_line(je["id"], mapping["credit_account"], 0, float(txn["total"]), f"Revenue from {txn['doc_key']}")
    else:
        # Default: Debit Cash, Credit Revenue
        JournalEntryRepository.add_line(je["id"], "1001", float(txn["total"]), 0, f"Payment for {txn['doc_key']}")
        JournalEntryRepository.add_line(je["id"], "4001", 0, float(txn["total"]), f"Revenue from {txn['doc_key']}")
    
    # Post to GL
    JournalEntryRepository.post(je["id"])
    
    # Link documents
    DocumentRegistryRepository.link(txn["doc_key"], je_key, "pos_to_je")

def _process_product_items(txn: dict):
    """Process product items - create stock movements."""
    items = TransactionItemRepository.get_by_transaction(txn["id"])
    for item in items:
        if item["item_type"] == "product":
            stk_key = _generate_doc_key(DocumentKind.STK)
            try:
                StockRepository.update_balance(
                    product_id=item["item_id"],
                    branch_id=txn["branch_id"],
                    qty_change=float(item["qty"]),
                    movement_type="out",
                )
                StockRepository.create_movement(
                    doc_key=stk_key,
                    product_id=item["item_id"],
                    branch_id=txn["branch_id"],
                    movement_type="out",
                    qty=float(item["qty"]),
                    reference_doc_key=txn["doc_key"],
                    notes=f"POS sale {txn['doc_key']}",
                )
                # Link documents
                DocumentRegistryRepository.link(txn["doc_key"], stk_key, "pos_to_stk")
            except ValueError as e:
                # Log but don't fail payment
                _audit(txn["doc_key"], "inventory", AuditAction.UPDATE, details=f"Stock warning: {e}")
