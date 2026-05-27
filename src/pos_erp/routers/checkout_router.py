"""Checkout / Transaction API router.

Handles the full POS checkout flow: create transaction, manage cart,
staff selection (with locking), payment, and checkout submission.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from pos_erp.audit_log import AuditLog, AuditSeverity
from pos_erp.payment import (
    PaymentIntent,
    PaymentMethod,
    PaymentStatus,
)
from pos_erp.staff_lock import (
    LockReleaseReason,
    LockStatus,
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
    TransactionLineResponse,
    TransactionResponse,
)

router = APIRouter(prefix="/api", tags=["Checkout"])

# ── In-memory stores ─────────────────────────────────────────────────────────

_transactions: dict[str, dict[str, Any]] = {}
_carts: dict[str, TreatmentCart] = {}
_lock_manager = StaffLockManager()
_payment_intents: dict[str, PaymentIntent] = {}
_audit_log = AuditLog()

# Mock catalog & staff directory
_catalog = ServiceCatalog(prices={
    "SVC-FACIAL": Decimal("150000"),
    "SVC-MASSAGE": Decimal("200000"),
    "SVC-HAIRSPA": Decimal("120000"),
    "SVC-PEDICURE": Decimal("80000"),
    "SVC-MANICURE": Decimal("75000"),
})

_staff_directory = StaffDirectory(
    staff_price_tiers={
        "STAFF-001": "senior",
        "STAFF-002": "senior",
        "STAFF-003": "junior",
        "STAFF-004": "junior",
        "STAFF-005": "senior",
    },
    available_staff={"STAFF-001", "STAFF-002", "STAFF-003", "STAFF-004", "STAFF-005"},
)


def _serialize_transaction(txn_id: str) -> dict[str, Any]:
    txn = _transactions[txn_id]
    cart = _carts.get(txn_id)
    lines = []
    if cart:
        for line in cart.lines:
            lines.append(TransactionLineResponse(
                line_id=line.line_id,
                service_id=line.service_id,
                staff_id=line.staff_id,
                price=str(line.price),
            ).model_dump())

    total = str(cart.total_price) if cart else "0.00"
    return TransactionResponse(
        transaction_id=txn_id,
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
        cashier_id=txn["cashier_id"],
        status=txn["status"],
        lines=lines,
        total_price=total,
        payment_method=txn.get("payment_method"),
        staff_lock_id=txn.get("staff_lock_id"),
        payment_intent_id=txn.get("payment_intent_id"),
    ).model_dump()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/transaction/{transaction_id}",
    summary="Ambil detail transaksi",
    responses={404: {"model": ErrorResponse}},
)
async def get_transaction(transaction_id: str):
    """Mengambil detail transaksi berdasarkan ID."""
    if transaction_id not in _transactions:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )
    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction",
    summary="Buat transaksi baru",
    status_code=201,
    responses={400: {"model": ErrorResponse}},
)
async def create_transaction(req: CreateTransactionRequest):
    """Membuat transaksi POS baru."""
    now = datetime.datetime.now()
    txn_id = f"TXN-{req.branch_code}-{req.device_id}-{now.strftime('%Y%m%d%H%M%S')}"

    _transactions[txn_id] = {
        "transaction_id": txn_id,
        "branch_code": req.branch_code,
        "device_id": req.device_id,
        "cashier_id": req.cashier_id,
        "status": "DRAFT",
        "payment_method": None,
        "staff_lock_id": None,
        "payment_intent_id": None,
        "created_at": now.isoformat(),
    }
    _carts[txn_id] = TreatmentCart(transaction_id=txn_id)

    _audit_log.record(
        action="TRANSACTION_CREATED",
        actor_id=req.cashier_id,
        branch_code=req.branch_code,
        device_id=req.device_id,
        reference_id=txn_id,
        severity=AuditSeverity.INFO,
        metadata={"cashier_id": req.cashier_id},
    )

    return _serialize_transaction(txn_id)


@router.post(
    "/transaction/{transaction_id}/add-item",
    summary="Tambah layanan ke keranjang",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def add_item(transaction_id: str, req: AddItemRequest):
    """Menambahkan layanan/treatment ke keranjang transaksi."""
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )
    if txn["status"] != "DRAFT":
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Transaksi sudah diproses, tidak dapat mengubah keranjang").model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message="Keranjang tidak ditemukan").model_dump(),
        )

    try:
        cart.add_service(
            req.service_id,
            staff_id=req.staff_id,
            catalog=_catalog,
            staff_directory=_staff_directory,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message=str(e)).model_dump(),
        )

    _audit_log.record(
        action="ITEM_ADDED",
        actor_id=txn["cashier_id"],
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
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
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )
    if txn["status"] != "DRAFT":
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Transaksi sudah diproses, tidak dapat mengubah keranjang").model_dump(),
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

    _audit_log.record(
        action="ITEM_REMOVED",
        actor_id=txn["cashier_id"],
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={"line_id": req.line_id},
    )

    return _serialize_transaction(transaction_id)


@router.post(
    "/transaction/{transaction_id}/select-staff",
    summary="Pilih staff (memicu lock)",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def select_staff(transaction_id: str, req: SelectStaffRequest):
    """Memilih staff untuk transaksi dan mengunci staff tersebut."""
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )

    now = datetime.datetime.now()
    try:
        lock = _lock_manager.reserve(
            staff_id=req.staff_id,
            transaction_id=transaction_id,
            branch_code=txn["branch_code"],
            device_id=txn["device_id"],
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

    txn["staff_lock_id"] = lock.lock_id

    _audit_log.record(
        action="STAFF_LOCKED",
        actor_id=req.actor_id,
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
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
async def select_payment_method(transaction_id: str, req: SelectPaymentMethodRequest):
    """Menentukan metode pembayaran untuk transaksi."""
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart or not cart.lines:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Keranjang kosong, tambahkan layanan terlebih dahulu").model_dump(),
        )

    valid_methods = {m.value for m in PaymentMethod}
    if req.payment_method not in valid_methods:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=f"Metode pembayaran '{req.payment_method}' tidak valid. Pilihan: {', '.join(sorted(valid_methods))}"
            ).model_dump(),
        )

    method = PaymentMethod(req.payment_method)
    intent = PaymentIntent(
        transaction_id=transaction_id,
        method=method,
        amount=cart.total_price,
        expected_reference=f"REF-{transaction_id}",
        online=True,
    )
    _payment_intents[transaction_id] = intent
    txn["payment_method"] = req.payment_method
    txn["payment_intent_id"] = f"PI-{transaction_id}"

    _audit_log.record(
        action="PAYMENT_METHOD_SELECTED",
        actor_id=txn["cashier_id"],
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
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
async def submit_checkout(transaction_id: str, req: SubmitCheckoutRequest | None = None):
    """Validasi dan submit checkout. Memeriksa semua prasyarat."""
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )

    cart = _carts.get(transaction_id)
    if not cart or not cart.lines:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Keranjang kosong, tidak dapat melakukan checkout").model_dump(),
        )

    if not txn.get("payment_method"):
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Pilih metode pembayaran terlebih dahulu").model_dump(),
        )

    intent = _payment_intents.get(transaction_id)
    if not intent:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Intent pembayaran tidak ditemukan").model_dump(),
        )

    txn["status"] = "PENDING_PAYMENT"

    _audit_log.record(
        action="CHECKOUT_SUBMITTED",
        actor_id=txn["cashier_id"],
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
        reference_id=transaction_id,
        severity=AuditSeverity.INFO,
        metadata={
            "total": str(cart.total_price),
            "payment_method": txn["payment_method"],
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
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
        )

    if txn.get("payment_method") != "cash":
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Metode pembayaran bukan tunai").model_dump(),
        )

    cart = _carts.get(transaction_id)
    total = cart.total_price if cart else Decimal("0.00")
    try:
        received = Decimal(req.amount_received)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Jumlah uang diterima tidak valid").model_dump(),
        )

    if received < total:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=f"Uang kurang. Total: Rp {total:,.0f}, diterima: Rp {received:,.0f}"
            ).model_dump(),
        )

    change = received - total
    txn["status"] = "PAID"
    if cart:
        cart.mark_paid()

    # Release staff lock
    lock_id = txn.get("staff_lock_id")
    if lock_id:
        try:
            _lock_manager.release(
                lock_id=lock_id,
                reason=LockReleaseReason.CANCEL,
                actor_id=txn["cashier_id"],
                now=datetime.datetime.now(),
            )
        except Exception:
            pass

    _audit_log.record(
        action="CASH_PAYMENT_CONFIRMED",
        actor_id=txn["cashier_id"],
        branch_code=txn["branch_code"],
        device_id=txn["device_id"],
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
async def request_staff_replacement(transaction_id: str, req: StaffReplacementRequest):
    """Mengganti staff yang tidak tersedia dengan alternatif."""
    txn = _transactions.get(transaction_id)
    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Transaksi '{transaction_id}' tidak ditemukan").model_dump(),
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
            staff_directory=_staff_directory,
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

    if suggestion.status == TreatmentStatus.REASSIGNMENT_SUGGESTED and suggestion.suggested_staff_id:
        if req.confirmed:
            try:
                cart.change_staff(
                    line_id=req.line_id,
                    new_staff_id=suggestion.suggested_staff_id,
                    staff_directory=_staff_directory,
                    confirmed=True,
                )
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(message=str(e)).model_dump(),
                )

            _audit_log.record(
                action="STAFF_REPLACED",
                actor_id=txn["cashier_id"],
                branch_code=txn["branch_code"],
                device_id=txn["device_id"],
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
    # Find transaction by payment_intent_id
    txn_id = payment_intent_id.replace("PI-", "") if payment_intent_id.startswith("PI-") else payment_intent_id
    txn = _transactions.get(txn_id)

    if not txn:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Payment intent '{payment_intent_id}' tidak ditemukan").model_dump(),
        )

    intent = _payment_intents.get(txn_id)
    if not intent:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(message=f"Intent pembayaran tidak ditemukan").model_dump(),
        )

    if intent.method != PaymentMethod.QRIS:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(message="Bukan pembayaran QRIS").model_dump(),
        )

    # In production, this would poll the QRIS gateway.
    # For now, return current status.
    status_map = {
        "DRAFT": "NOT_STARTED",
        "PENDING_PAYMENT": "PENDING",
        "PAID": "SETTLED",
    }

    return QRISStatusResponse(
        payment_intent_id=payment_intent_id,
        status=status_map.get(txn["status"], "UNKNOWN"),
        message=f"Status pembayaran QRIS: {txn['status']}",
    ).model_dump()
