"""Checkout / Transaction API router.

Handles the full POS checkout flow: create transaction, manage cart,
staff selection (with locking), payment, and checkout submission.

Persists transactions to PostgreSQL (pos_transaction / pos_transaction_item).
"""

from __future__ import annotations

import datetime
import uuid as _uuid
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import JSONResponse

from pos_erp.audit_log import AuditLog, AuditSeverity
from pos_erp.db import execute, execute_returning, fetch_all, fetch_one
from pos_erp.payment import PaymentIntent, PaymentMethod
from pos_erp.staff_lock import (
    LockReleaseReason,
    StaffAlreadyLocked,
    StaffLockManager,
)
from pos_erp.treatment import (
    ServiceCatalog,
    StaffDirectory,
    TreatmentCart,
    TreatmentStatus,
)

from pos_erp.routers.models import (
    AddItemRequest,
    ConfirmCashRequest,
    CreateTransactionRequest,
    ErrorResponse,
    QRISStatusResponse,
    RemoveItemRequest,
    SelectPaymentMethodRequest,
    SelectStaffRequest,
    StaffReplacementRequest,
    SubmitCheckoutRequest,
    TransactionLineResponse,
    TransactionResponse,
)

router = APIRouter(prefix="/api", tags=["Checkout"])

# ── In-memory stores (cart logic, locks, payment intents) ────────────────────

_carts: dict[str, TreatmentCart] = {}
_lock_manager = StaffLockManager()
_payment_intents: dict[str, PaymentIntent] = {}
_audit_log = AuditLog()

# Request metadata not stored in DB (device_id, pos_code, staff_lock_id)
_txn_meta: dict[str, dict[str, Any]] = {}

# ── Caches for DB lookups ────────────────────────────────────────────────────

_branch_cache: dict[str, str] = {}           # branch_code → branch UUID
_cashier_cache: dict[str, str] = {}          # username → app_user UUID
_payment_method_cache: dict[str, dict] = {}  # type → {id, name, type}

# ── Status mapping ────────────────────────────────────────────────────────────

_DB_TO_STATE: dict[str, str] = {
    "open": "DRAFT",
    "validated": "VALIDATED",
    "paid": "PAID",
    "cancelled": "CANCELLED",
}
_STATE_TO_DB: dict[str, str] = {v: k for k, v in _DB_TO_STATE.items()}
_STATE_TO_DB["PENDING_PAYMENT"] = "validated"  # legacy compat

# ── Dynamic catalog & staff directory (loaded from DB) ──────────────────────────

_TIER_MAP = {
    "admin": "senior",
    "manager": "senior",
    "cashier": "junior",
    "therapist": "junior",
}


def _load_catalog() -> ServiceCatalog:
    """Load treatment prices from ``treatment`` table."""
    rows = fetch_all(
        "SELECT id, price FROM treatment WHERE is_active = true"
    )
    prices = {str(r["id"]): Decimal(str(r["price"])) for r in rows}
    return ServiceCatalog(prices=prices)


def _load_staff_directory() -> StaffDirectory:
    """Load available staff from ``app_user`` table (only active POS users)."""
    rows = fetch_all(
        "SELECT username, pos_role FROM app_user WHERE is_active = true"
    )
    tiers = {}
    available = set()
    for r in rows:
        uid = r["username"]
        role = (r.get("pos_role") or "cashier").lower()
        tiers[uid] = _TIER_MAP.get(role, "junior")
        available.add(uid)
    return StaffDirectory(staff_price_tiers=tiers, available_staff=available)


_catalog = _load_catalog()
_staff_directory = _load_staff_directory()

# Refresh every 60 seconds so new users/treatments appear without restart
import time as _time
_catalog_last_load = _time.monotonic()
_staff_last_load = _time.monotonic()


def _get_catalog() -> ServiceCatalog:
    global _catalog, _catalog_last_load
    if _time.monotonic() - _catalog_last_load > 60:
        _catalog = _load_catalog()
        _catalog_last_load = _time.monotonic()
    return _catalog


def _get_staff_directory() -> StaffDirectory:
    global _staff_directory, _staff_last_load
    if _time.monotonic() - _staff_last_load > 60:
        _staff_directory = _load_staff_directory()
        _staff_last_load = _time.monotonic()
    return _staff_directory


# ═══════════════════════════════════════════════════════════════════════════════
#  Helper functions
# ═══════════════════════════════════════════════════════════════════════════════


def _safe_uuid(val: str) -> str | None:
    """Return *val* if it is a valid UUID string, else ``None``."""
    try:
        _uuid.UUID(str(val))
        return str(val)
    except (ValueError, AttributeError):
        return None


def _resolve_branch_id(branch_code: str) -> str:
    """Look up branch UUID by code (cached)."""
    if branch_code in _branch_cache:
        return _branch_cache[branch_code]
    row = fetch_one("SELECT id FROM branch WHERE code = %s", (branch_code,))
    if not row:
        raise ValueError(f"Branch '{branch_code}' not found")
    _branch_cache[branch_code] = str(row["id"])
    return _branch_cache[branch_code]


def _resolve_cashier_id(username: str) -> str:
    """Look up ``app_user`` UUID by username (cached)."""
    if username in _cashier_cache:
        return _cashier_cache[username]
    row = fetch_one("SELECT id FROM app_user WHERE username = %s", (username,))
    if not row:
        raise ValueError(f"User '{username}' not found")
    _cashier_cache[username] = str(row["id"])
    return _cashier_cache[username]


def _resolve_payment_method(method_type: str) -> dict:
    """Look up payment method by *type* (cached).  Returns ``{id, name, type}``."""
    if method_type in _payment_method_cache:
        return _payment_method_cache[method_type]
    row = fetch_one(
        "SELECT id, name, type FROM payment_method WHERE type = %s AND is_active = true",
        (method_type,),
    )
    if not row:
        raise ValueError(f"Payment method '{method_type}' not found")
    _payment_method_cache[method_type] = {
        "id": str(row["id"]),
        "name": row["name"],
        "type": row["type"],
    }
    return _payment_method_cache[method_type]


def _generate_doc_key(branch_code: str) -> str:
    """Generate next ``TXN-YYYYMMDD-NNNN`` doc_key and register it."""
    # Use WIB (UTC+7) date for consistency with user's timezone
    wib_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    today = wib_now.date()
    date_str = today.strftime("%Y%m%d")

    # Use advisory lock to prevent race condition
    # Lock key based on module + date (global, not per-branch, since doc_key is global)
    lock_key = hash(f"POS-TXN-{today}") % 2147483647
    fetch_one("SELECT pg_advisory_lock(%s)", (lock_key,))
    
    try:
        # Global sequence (not per-branch) — doc_key has no branch component
        row = fetch_one(
            "SELECT COALESCE(MAX(sequence), 0) AS max_seq FROM document_registry "
            "WHERE module = 'POS' AND doc_date = %s",
            (today,),
        )
        next_seq = (row["max_seq"] if row else 0) + 1
        doc_key = f"TXN-{date_str}-{next_seq:04d}"

        execute(
            "INSERT INTO document_registry (doc_key, module, branch_code, doc_date, sequence) "
            "VALUES (%s, 'POS', %s, %s, %s)",
            (doc_key, branch_code, today, next_seq),
        )
        return doc_key
    finally:
        fetch_one("SELECT pg_advisory_unlock(%s)", (lock_key,))


_pos_code_seq: dict[str, int] = {}


def _generate_pos_code() -> str:
    """Generate next ``POS-YYYYMMDD-NNNN`` code (in-memory counter)."""
    wib_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))
    today = wib_now.date()
    date_str = today.strftime("%Y%m%d")
    key = f"POS-{date_str}"
    _pos_code_seq[key] = _pos_code_seq.get(key, 0) + 1
    return f"POS-{date_str}-{_pos_code_seq[key]:04d}"


def _sync_cart_to_db(doc_key: str, cart: TreatmentCart) -> None:
    """Persist cart lines to ``pos_transaction_item`` and recalculate totals."""
    txn_row = fetch_one("SELECT id FROM pos_transaction WHERE doc_key = %s", (doc_key,))
    if not txn_row:
        return
    txn_uuid = txn_row["id"]

    # Wipe existing items
    execute("DELETE FROM pos_transaction_item WHERE transaction_id = %s", (txn_uuid,))

    # Re-insert from cart
    for line in cart.lines:
        item_id_val = _safe_uuid(line.service_id)
        trt = None
        if item_id_val:
            trt = fetch_one("SELECT name FROM treatment WHERE id = %s", (item_id_val,))
        item_name = trt["name"] if trt else line.service_id
        execute(
            "INSERT INTO pos_transaction_item "
            "(transaction_id, item_type, item_id, item_name, qty, unit_price, discount, total) "
            "VALUES (%s, 'treatment', %s, %s, 1, %s, 0, %s)",
            (txn_uuid, item_id_val, item_name, float(line.price), float(line.price)),
        )

    # Recalculate totals
    total = float(cart.total_price)
    execute(
        "UPDATE pos_transaction SET subtotal = %s, discount = 0, tax = 0, total = %s WHERE doc_key = %s",
        (total, total, doc_key),
    )


def _load_txn(doc_key: str) -> dict | None:
    """Load transaction row with joined branch / user / payment info."""
    return fetch_one(
        "SELECT t.*, b.code AS branch_code, b.name AS branch_name, b.address AS branch_address, " 
        "       u.username AS cashier_username, "
        "       pm.name AS pm_name, pm.type AS pm_type "
        "FROM pos_transaction t "
        "LEFT JOIN branch b ON t.branch_id = b.id "
        "LEFT JOIN app_user u ON t.cashier_id = u.id "
        "LEFT JOIN payment_method pm ON t.payment_method_id = pm.id "
        "WHERE t.doc_key = %s",
        (doc_key,),
    )


def _meta(transaction_id: str) -> dict[str, Any]:
    """Shortcut for ``_txn_meta.get(transaction_id, {})``."""
    return _txn_meta.get(transaction_id, {})


# ═══════════════════════════════════════════════════════════════════════════════
#  Serialization  (the critical function — must match frontend Transaction iface)
# ═══════════════════════════════════════════════════════════════════════════════


def _serialize_transaction(doc_key: str) -> dict[str, Any]:
    """Serialize a transaction to match the frontend ``Transaction`` interface.

    Frontend shape::

        { id, state, branchCode, deviceId, cashierId, customer, items,
          subtotal, discount, total, paymentMethod, paymentIntent, posCode,
          staffLock, createdAt, updatedAt }

    Each item::

        { id, service: {id, code, name, price, duration, category},
          staff: {id, name, role}, price, discount, total }
    """
    txn = _load_txn(doc_key)
    if not txn:
        raise ValueError(f"Transaction '{doc_key}' not found")

    # ── Items ──────────────────────────────────────────────────────────────
    db_items = fetch_all(
        "SELECT * FROM pos_transaction_item WHERE transaction_id = %s ORDER BY id",
        (txn["id"],),
    )

    cart = _carts.get(doc_key)
    items: list[dict[str, Any]] = []

    for item in db_items:
        item_uuid = str(item["item_id"]) if item["item_id"] else ""

        # Treatment details
        trt = None
        if item_uuid:
            trt = fetch_one(
                "SELECT t.name, t.price, t.duration_minutes, tc.name AS cat_name "
                "FROM treatment t "
                "LEFT JOIN treatment_category tc ON t.category_id = tc.id "
                "WHERE t.id = %s",
                (item_uuid,),
            )

        service: dict[str, Any] = {
            "id": item_uuid,
            "code": item_uuid[:8] if item_uuid else "",
            "name": trt["name"] if trt else (item.get("item_name") or ""),
            "price": float(trt["price"]) if trt else float(item["unit_price"]),
            "duration": trt["duration_minutes"] if trt else 60,
            "category": (trt.get("cat_name") or "") if trt else "",
        }

        # Staff info (only available while cart is in memory)
        staff_info: dict[str, Any] | None = None
        if cart:
            for line in cart.lines:
                line_item_id = _safe_uuid(line.service_id) or line.service_id
                if line_item_id == item_uuid or (not item_uuid and line.service_id == item.get("item_name")):
                    sid = line.staff_id
                    usr = fetch_one(
                        "SELECT username, full_name FROM app_user WHERE username = %s",
                        (sid,),
                    )
                    if usr:
                        staff_info = {
                            "id": usr["username"],
                            "name": usr["full_name"] or usr["username"],
                            "role": "cashier",
                        }
                    else:
                        from pos_erp.pos_auth import STAFF_DB
                        rec = STAFF_DB.get(sid, {})
                        staff_info = {
                            "id": sid,
                            "name": rec.get("name", sid),
                            "role": rec.get("role", "cashier"),
                        }
                    break

        items.append({
            "id": str(item["id"]),
            "service": service,
            "staff": staff_info,
            "price": float(item["unit_price"]),
            "discount": float(item["discount"]),
            "total": float(item["total"]),
        })

    # ── Header ─────────────────────────────────────────────────────────────
    state = _DB_TO_STATE.get(txn.get("status", "open"), "DRAFT")
    m = _meta(doc_key)

    customer = None
    if txn.get("customer_name"):
        customer = {"name": txn["customer_name"], "phone": txn.get("customer_phone")}

    created = txn["created_at"].isoformat() if txn.get("created_at") else ""
    payment_method = txn.get("pm_name") or txn.get("pm_type") or None

    return {
        "id": doc_key,
        "state": state,
        "branchCode": txn.get("branch_code") or m.get("branch_code", "HQ"),
        "branchName": txn.get("branch_name") or "Beauty & Shine",
        "branchAddress": txn.get("branch_address") or "",
        "deviceId": m.get("device_id", "POS-01"),
        "cashierId": txn.get("cashier_username") or m.get("cashier_id", ""),
        "customer": customer,
        "items": items,
        "subtotal": float(txn.get("subtotal", 0)),
        "discount": float(txn.get("discount", 0)),
        "total": float(txn.get("total", 0)),
        "paymentMethod": payment_method,
        "paymentIntent": None,
        "posCode": m.get("pos_code"),
        "staffLock": None,
        "createdAt": created,
        "updatedAt": created,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/transaction/{transaction_id}",
    summary="Ambil detail transaksi",
    responses={404: {"model": ErrorResponse}},
)
async def get_transaction(transaction_id: str):
    """Mengambil detail transaksi berdasarkan ID (doc_key)."""
    txn = fetch_one(
        "SELECT doc_key FROM pos_transaction WHERE doc_key = %s",
        (transaction_id,),
    )
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )
    return _serialize_transaction(transaction_id)


class UpdateCustomerRequest(BaseModel):
    customer_name: str
    customer_phone: Optional[str] = None

@router.put(
    "/transaction/{transaction_id}/customer",
    summary="Ganti pelanggan transaksi",
    responses={404: {"model": ErrorResponse}},
)
async def update_transaction_customer(transaction_id: str, req: UpdateCustomerRequest):
    """Mengganti pelanggan pada transaksi yang sudah ada."""
    txn = fetch_one(
        "SELECT id, status FROM pos_transaction WHERE doc_key = %s",
        (transaction_id,),
    )
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )
    if txn["status"] not in ("draft", "open"):
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Hanya transaksi draft/open yang bisa ganti pelanggan").model_dump(),
        )
    execute_returning(
        "UPDATE pos_transaction SET customer_name=%s, customer_phone=%s WHERE doc_key=%s RETURNING *",
        (req.customer_name, req.customer_phone, transaction_id),
    )
    return _serialize_transaction(transaction_id)


class ApplyVoucherRequest(BaseModel):
    code: str

@router.post(
    "/transaction/{transaction_id}/apply-voucher",
    summary="Terapkan voucher ke transaksi",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def apply_voucher(transaction_id: str, req: ApplyVoucherRequest):
    """Menerapkan voucher diskon ke transaksi."""
    txn = fetch_one(
        "SELECT id, status, subtotal FROM pos_transaction WHERE doc_key = %s",
        (transaction_id,),
    )
    if not txn:
        return JSONResponse(status_code=404, content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump())
    if txn["status"] not in ("draft", "open"):
        return JSONResponse(status_code=400, content=ErrorResponse(message="Hanya transaksi draft/open yang bisa apply voucher").model_dump())

    voucher = fetch_one("SELECT * FROM voucher WHERE code = %s AND is_active = true", (req.code.upper(),))
    if not voucher:
        return JSONResponse(status_code=400, content=ErrorResponse(message="Voucher tidak ditemukan atau tidak aktif").model_dump())

    from datetime import date as _date
    today = _date.today()
    if voucher.get("valid_from") and voucher["valid_from"] > today:
        return JSONResponse(status_code=400, content=ErrorResponse(message=f"Voucher berlaku mulai {voucher['valid_from']}").model_dump())
    if voucher.get("valid_until") and voucher["valid_until"] < today:
        return JSONResponse(status_code=400, content=ErrorResponse(message="Voucher sudah expired").model_dump())
    if voucher.get("usage_limit") and voucher.get("used_count", 0) >= voucher["usage_limit"]:
        return JSONResponse(status_code=400, content=ErrorResponse(message="Voucher sudah mencapai batas penggunaan").model_dump())

    subtotal = float(txn["subtotal"] or 0)
    if voucher.get("min_purchase") and subtotal < float(voucher["min_purchase"]):
        return JSONResponse(status_code=400, content=ErrorResponse(message=f"Minimal pembelian Rp {float(voucher['min_purchase']):,.0f}").model_dump())

    voucher_type = voucher.get("type", "fixed")
    voucher_value = float(voucher.get("value", 0))
    discount = subtotal * voucher_value / 100 if voucher_type == "percentage" else min(voucher_value, subtotal)
    new_total = max(0, subtotal - discount)

    execute_returning("UPDATE pos_transaction SET discount = %s, total = %s, voucher_code = %s WHERE doc_key = %s RETURNING *", (discount, new_total, voucher["code"], transaction_id))
    execute("UPDATE voucher SET used_count = used_count + 1 WHERE id = %s", (voucher["id"],))

    return _serialize_transaction(transaction_id)


class ApplyDiscountRequest(BaseModel):
    discount_type: str
    value: float
    reason: Optional[str] = None

@router.post("/transaction/{transaction_id}/apply-discount", summary="Terapkan diskon manual")
async def apply_manual_discount(transaction_id: str, req: ApplyDiscountRequest):
    """Menerapkan diskon manual ke transaksi."""
    txn = fetch_one("SELECT id, status, subtotal FROM pos_transaction WHERE doc_key = %s", (transaction_id,))
    if not txn:
        return JSONResponse(status_code=404, content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump())
    if txn["status"] not in ("draft", "open"):
        return JSONResponse(status_code=400, content=ErrorResponse(message="Hanya transaksi draft/open yang bisa apply diskon").model_dump())

    subtotal = float(txn["subtotal"] or 0)
    discount = subtotal * req.value / 100 if req.discount_type == "percentage" else min(req.value, subtotal)
    new_total = max(0, subtotal - discount)
    execute_returning("UPDATE pos_transaction SET discount = %s, total = %s WHERE doc_key = %s RETURNING *", (discount, new_total, transaction_id))

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction",
    summary="Buat transaksi baru",
    status_code=201,
    responses={400: {"model": ErrorResponse}},
)
async def create_transaction(req: CreateTransactionRequest):
    """Membuat transaksi POS baru — persists to PostgreSQL."""
    # Resolve FK values — accept branch_id (UUID) or branch_code (string)
    try:
        if req.branch_id:
            # Direct UUID provided — verify it exists and get code
            row = fetch_one("SELECT id, code FROM branch WHERE id = %s", (req.branch_id,))
            if not row:
                return JSONResponse(status_code=400, content=ErrorResponse(message=f"Branch '{req.branch_id}' not found").model_dump())
            branch_id = str(row["id"])
            branch_code = row["code"]
        elif req.branch_code:
            branch_id = _resolve_branch_id(req.branch_code)
            branch_code = req.branch_code
        else:
            # Fallback: default to HQ
            branch_id = _resolve_branch_id("HQ")
            branch_code = "HQ"
        cashier_id = _resolve_cashier_id(req.cashier_id)
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message=str(e)).model_dump(),
        )

    # Generate doc_key and register in document_registry
    doc_key = _generate_doc_key(branch_code)

    # Insert into pos_transaction
    shift_id = req.shift_id if req.shift_id else None
    execute(
        "INSERT INTO pos_transaction "
        "(doc_key, branch_id, cashier_id, shift_id, status, subtotal, discount, tax, total) "
        "VALUES (%s, %s, %s, %s, 'open', 0, 0, 0, 0)",
        (doc_key, branch_id, cashier_id, shift_id),
    )

    # In-memory cart + metadata
    _carts[doc_key] = TreatmentCart(transaction_id=doc_key)
    _txn_meta[doc_key] = {
        "branch_code": req.branch_code,
        "device_id": req.device_id,
        "cashier_id": req.cashier_id,
    }

    _audit_log.record(
        action="TRANSACTION_CREATED",
        actor_id=req.cashier_id,
        branch_code=req.branch_code,
        device_id=req.device_id,
        reference_id=doc_key,
        severity=AuditSeverity.INFO,
        metadata={"cashier_id": req.cashier_id},
    )

    return _serialize_transaction(doc_key)


@router.post(
    "/transaction/{transaction_id}/add-item",
    summary="Tambah layanan ke keranjang",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def add_item(transaction_id: str, req: AddItemRequest):
    """Menambahkan layanan/treatment ke keranjang transaksi."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )
    if _DB_TO_STATE.get(txn["status"], "DRAFT") != "DRAFT":
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Transaksi sudah diproses, tidak dapat mengubah keranjang"
            ).model_dump(),
        )

    # Get or create cart
    cart = _carts.get(transaction_id)
    if not cart:
        cart = TreatmentCart(transaction_id=transaction_id)
        _carts[transaction_id] = cart

    try:
        cart.add_service(
            req.service_id,
            staff_id=req.staff_id,
            catalog=_get_catalog(),
            staff_directory=_get_staff_directory(),
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message=str(e)).model_dump(),
        )

    # Persist to DB
    _sync_cart_to_db(transaction_id, cart)

    m = _meta(transaction_id)
    _audit_log.record(
        action="ITEM_ADDED",
        actor_id=m.get("cashier_id", txn.get("cashier_username", "system")),
        branch_code=m.get("branch_code", txn.get("branch_code", "")),
        device_id=m.get("device_id", ""),
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={"service_id": req.service_id, "staff_id": req.staff_id},
    )

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction/{transaction_id}/remove-item",
    summary="Hapus layanan dari keranjang",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def remove_item(transaction_id: str, req: RemoveItemRequest):
    """Menghapus layanan dari keranjang transaksi."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )
    if _DB_TO_STATE.get(txn["status"], "DRAFT") != "DRAFT":
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Transaksi sudah diproses, tidak dapat mengubah keranjang"
            ).model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message="Keranjang tidak ditemukan").model_dump(),
        )

    try:
        cart.remove_service(req.line_id)
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message=str(e)).model_dump(),
        )

    # Persist to DB
    _sync_cart_to_db(transaction_id, cart)

    m = _meta(transaction_id)
    _audit_log.record(
        action="ITEM_REMOVED",
        actor_id=m.get("cashier_id", txn.get("cashier_username", "system")),
        branch_code=m.get("branch_code", txn.get("branch_code", "")),
        device_id=m.get("device_id", ""),
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={"line_id": req.line_id},
    )

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction/{transaction_id}/select-staff",
    summary="Pilih staff (memicu lock)",
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def select_staff(transaction_id: str, req: SelectStaffRequest):
    """Memilih staff untuk transaksi dan mengunci staff tersebut."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )

    m = _meta(transaction_id)
    branch_code = m.get("branch_code", txn.get("branch_code", "HQ"))
    device_id = m.get("device_id", "POS-01")

    now = datetime.datetime.now()
    try:
        lock = _lock_manager.reserve(
            staff_id=req.staff_id,
            transaction_id=transaction_id,
            branch_code=branch_code,
            device_id=device_id,
            actor_id=req.actor_id,
            now=now,
        )
    except StaffAlreadyLocked as e:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                message=f"Staff '{req.staff_id}' sedang digunakan transaksi lain",
                detail=str(e),
            ).model_dump(),
        )

    _txn_meta.setdefault(transaction_id, {})["staff_lock_id"] = lock.lock_id

    _audit_log.record(
        action="STAFF_LOCKED",
        actor_id=req.actor_id,
        branch_code=branch_code,
        device_id=device_id,
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={"staff_id": req.staff_id, "lock_id": lock.lock_id},
    )

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction/{transaction_id}/select-payment-method",
    summary="Pilih metode pembayaran",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def select_payment_method(
    transaction_id: str, req: SelectPaymentMethodRequest
):
    """Menentukan metode pembayaran untuk transaksi."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart or not cart.lines:
        # Cart lost (server restart or booking conversion) — check if DB has items
        db_items = fetch_all(
            "SELECT COUNT(*) as cnt FROM pos_transaction_item WHERE transaction_id = %s",
            (txn["id"],),
        )
        if not db_items or db_items[0]["cnt"] == 0:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    message="Keranjang kosong, tambahkan layanan terlebih dahulu"
                ).model_dump(),
            )

    # Prevent Rp 0 transactions — check DB total (covers bookings with items but no in-memory cart)
    db_total = Decimal(str(txn.get("total", 0)))
    if cart and cart.lines:
        cart_total = cart.total_price
    else:
        cart_total = float(db_total)
    if cart_total <= 0:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Total transaksi Rp 0 — tambahkan layanan terlebih dahulu"
            ).model_dump(),
        )

    # Validate against DB payment_method table
    try:
        pm = _resolve_payment_method(req.payment_method)
    except ValueError:
        valid_rows = fetch_all(
            "SELECT type FROM payment_method WHERE is_active = true"
        )
        valid_types = sorted(r["type"] for r in valid_rows)
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=(
                    f"Metode pembayaran '{req.payment_method}' tidak valid. "
                    f"Pilihan: {', '.join(valid_types)}"
                )
            ).model_dump(),
        )

    # Persist payment_method_id to DB
    execute(
        "UPDATE pos_transaction SET payment_method_id = %s WHERE doc_key = %s",
        (pm["id"], transaction_id),
    )

    # Create PaymentIntent for online methods (QRIS / bank transfer)
    if req.payment_method in {m.value for m in PaymentMethod}:
        intent = PaymentIntent(
            transaction_id=transaction_id,
            method=PaymentMethod(req.payment_method),
            amount=cart.total_price,
            expected_reference=f"REF-{transaction_id}",
            online=True,
        )
        _payment_intents[transaction_id] = intent

    m = _meta(transaction_id)
    _audit_log.record(
        action="PAYMENT_METHOD_SELECTED",
        actor_id=m.get("cashier_id", txn.get("cashier_username", "system")),
        branch_code=m.get("branch_code", txn.get("branch_code", "")),
        device_id=m.get("device_id", ""),
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={"payment_method": req.payment_method},
    )

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction/{transaction_id}/submit-checkout",
    summary="Validasi & submit checkout",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def submit_checkout(
    transaction_id: str, req: SubmitCheckoutRequest | None = None
):
    """Validasi dan submit checkout. Memeriksa semua prasyarat."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart or not cart.lines:
        # Cart lost (server restart?) — check if DB has items
        db_items = fetch_all(
            "SELECT COUNT(*) as cnt FROM pos_transaction_item WHERE transaction_id = %s",
            (txn["id"],),
        )
        if not db_items or db_items[0]["cnt"] == 0:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    message="Keranjang kosong, tidak dapat melakukan checkout"
                ).model_dump(),
            )
    else:
        # Sync cart to DB (ensures items & total survive server restart)
        _sync_cart_to_db(transaction_id, cart)

    # Re-load txn after potential sync for accurate total
    txn = _load_txn(transaction_id)
    db_total = Decimal(str(txn.get("total", 0)))

    if db_total <= 0:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Total transaksi harus lebih dari Rp 0"
            ).model_dump(),
        )

    if not txn.get("payment_method_id"):
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Pilih metode pembayaran terlebih dahulu"
            ).model_dump(),
        )

    # Advance status to 'validated'
    execute(
        "UPDATE pos_transaction SET status = 'validated' WHERE doc_key = %s",
        (transaction_id,),
    )

    m = _meta(transaction_id)
    _audit_log.record(
        action="CHECKOUT_SUBMITTED",
        actor_id=m.get("cashier_id", txn.get("cashier_username", "system")),
        branch_code=m.get("branch_code", txn.get("branch_code", "")),
        device_id=m.get("device_id", ""),
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={
            "total": str(cart.total_price if cart else db_total),
            "payment_method": txn.get("pm_type", ""),
        },
    )

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction/{transaction_id}/confirm-cash",
    summary="Konfirmasi pembayaran tunai",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def confirm_cash(transaction_id: str, req: ConfirmCashRequest):
    """Konfirmasi penerimaan uang tunai dari pelanggan."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )

    if txn.get("pm_type") != "cash":
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Metode pembayaran bukan tunai"
            ).model_dump(),
        )

    cart = _carts.get(transaction_id)

    # Always sync cart to DB first (ensures items & total survive server restart)
    if cart and cart.lines:
        _sync_cart_to_db(transaction_id, cart)

    # Use DB total as source of truth (after sync)
    txn = _load_txn(transaction_id)  # Re-load after sync
    total = Decimal(str(txn.get("total", 0)))
    try:
        received = Decimal(req.amount_received)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Jumlah uang diterima tidak valid"
            ).model_dump(),
        )

    # Prevent Rp 0 transactions
    if total <= 0:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Tidak bisa proses pembayaran Rp 0 — pilih treatment dulu"
            ).model_dump(),
        )

    if received < total:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=f"Uang kurang. Total: Rp {total:,.0f}, diterima: Rp {received:,.0f}"
            ).model_dump(),
        )

    change = received - total

    # Mark paid in DB
    cash_pm = _resolve_payment_method("cash")
    pos_code = _generate_pos_code()
    execute(
        "UPDATE pos_transaction SET status = 'paid', payment_method_id = %s WHERE doc_key = %s",
        (cash_pm["id"], transaction_id),
    )

    if cart:
        cart.mark_paid()

    # Store POS code in meta
    _txn_meta.setdefault(transaction_id, {})["pos_code"] = pos_code

    # Release staff lock
    lock_id = _meta(transaction_id).get("staff_lock_id")
    if lock_id:
        try:
            _lock_manager.release(
                lock_id=lock_id,
                reason=LockReleaseReason.CANCEL,
                actor_id=_meta(transaction_id).get("cashier_id", "system"),
                now=datetime.datetime.now(),
            )
        except Exception:
            pass

    m = _meta(transaction_id)
    _audit_log.record(
        action="CASH_PAYMENT_CONFIRMED",
        actor_id=m.get("cashier_id", txn.get("cashier_username", "system")),
        branch_code=m.get("branch_code", txn.get("branch_code", "")),
        device_id=m.get("device_id", ""),
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={"amount_received": str(received), "change": str(change)},
    )

    result = _serialize_transaction(transaction_id)
    result["payment_details"] = {
        "amount_received": str(received),
        "total": str(total),
        "change": str(change),
    }
    return result


@router.post(
    "/transaction/{transaction_id}/request-staff-replacement",
    summary="Ganti staff otomatis",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def request_staff_replacement(
    transaction_id: str, req: StaffReplacementRequest
):
    """Mengganti staff yang tidak tersedia dengan alternatif."""
    txn = _load_txn(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Transaksi '{transaction_id}' tidak ditemukan"
            ).model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message="Keranjang tidak ditemukan").model_dump(),
        )

    try:
        suggestion = cart.revalidate_staff(
            line_id=req.line_id,
            staff_directory=_get_staff_directory(),
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message=str(e)).model_dump(),
        )

    if suggestion.status == TreatmentStatus.OK:
        return {
            "status": "OK",
            "message": "Staff masih tersedia, tidak perlu penggantian",
            "transaction": _serialize_transaction(transaction_id),
        }

    if (
        suggestion.status == TreatmentStatus.REASSIGNMENT_SUGGESTED
        and suggestion.suggested_staff_id
    ):
        if req.confirmed:
            try:
                cart.change_staff(
                    line_id=req.line_id,
                    new_staff_id=suggestion.suggested_staff_id,
                    staff_directory=_get_staff_directory(),
                    confirmed=True,
                )
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(message=str(e)).model_dump(),
                )

            # Sync change to DB
            _sync_cart_to_db(transaction_id, cart)

            m = _meta(transaction_id)
            _audit_log.record(
                action="STAFF_REPLACED",
                actor_id=m.get("cashier_id", txn.get("cashier_username", "system")),
                branch_code=m.get("branch_code", txn.get("branch_code", "")),
                device_id=m.get("device_id", ""),
                reference_id=transaction_id,
                severity=AuditSeverity.INFO,
                metadata={
                    "line_id": req.line_id,
                    "new_staff_id": suggestion.suggested_staff_id,
                },
            )

            return {
                "status": "REPLACED",
                "message": f"Staff berhasil diganti dengan {suggestion.suggested_staff_id}",
                "transaction": _serialize_transaction(transaction_id),
            }
        else:
            return {
                "status": "REASSIGNMENT_SUGGESTED",
                "suggested_staff_id": suggestion.suggested_staff_id,
                "requires_confirmation": True,
                "message": f"Staff disarankan: {suggestion.suggested_staff_id}. Setujui?",
            }

    if suggestion.status == TreatmentStatus.WAITLIST_OR_CANCEL:
        return {
            "status": "WAITLIST_OR_CANCEL",
            "options": list(suggestion.options),
            "message": "Tidak ada staff alternatif. Pilih WAITLIST atau CANCEL.",
        }

    return {"status": "UNKNOWN", "message": "Status tidak diketahui"}


@router.get(
    "/payment/qris-status/{payment_intent_id}",
    summary="Polling status QRIS",
    responses={404: {"model": ErrorResponse}},
)
async def qris_status(payment_intent_id: str):
    """Memeriksa status pembayaran QRIS (polling)."""
    txn_id = (
        payment_intent_id.replace("PI-", "")
        if payment_intent_id.startswith("PI-")
        else payment_intent_id
    )
    txn = _load_txn(txn_id)

    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Payment intent '{payment_intent_id}' tidak ditemukan"
            ).model_dump(),
        )

    intent = _payment_intents.get(txn_id)
    if not intent:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message="Intent pembayaran tidak ditemukan"
            ).model_dump(),
        )

    if intent.method != PaymentMethod.QRIS:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Bukan pembayaran QRIS").model_dump(),
        )

    state = _DB_TO_STATE.get(txn.get("status", "open"), "DRAFT")
    status_map = {
        "DRAFT": "NOT_STARTED",
        "VALIDATED": "PENDING",
        "PENDING_PAYMENT": "PENDING",
        "PAID": "SETTLED",
    }

    return QRISStatusResponse(
        payment_intent_id=payment_intent_id,
        status=status_map.get(state, "UNKNOWN"),
        message=f"Status pembayaran QRIS: {state}",
    ).model_dump()
