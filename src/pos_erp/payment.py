from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum


class PaymentMethod(str, Enum):
    QRIS = "qris"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, Enum):
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_REVIEW_REQUIRED = "PAYMENT_REVIEW_REQUIRED"
    PAID = "PAID"


@dataclass(frozen=True)
class PaymentIntent:
    transaction_id: str
    method: PaymentMethod
    amount: Decimal
    expected_reference: str
    online: bool
    status: PaymentStatus = PaymentStatus.PAYMENT_PENDING


@dataclass(frozen=True)
class VerificationResult:
    transaction_id: str
    method: PaymentMethod
    amount: Decimal
    status: PaymentStatus
    reason_code: str
    verified_reference: str | None = None
    proof_document_id: str | None = None
    uploaded_by: str | None = None
    reviewed_by: str | None = None


def verify_qris_callback(
    intent: PaymentIntent,
    *,
    gateway_reference: str,
    gateway_status: str,
    amount: Decimal,
) -> VerificationResult:
    if not intent.online:
        return _pending(intent, reason_code="QRIS_OFFLINE_CANNOT_VERIFY")

    if gateway_reference != intent.expected_reference:
        return _pending(intent, reason_code="QRIS_REFERENCE_MISMATCH")

    if _normalized_status(gateway_status) != "settled":
        return _pending(intent, reason_code="QRIS_GATEWAY_NOT_SETTLED")

    if amount != intent.amount:
        return _pending(intent, reason_code="QRIS_AMOUNT_MISMATCH")

    return VerificationResult(
        transaction_id=intent.transaction_id,
        method=intent.method,
        amount=intent.amount,
        status=PaymentStatus.PAID,
        verified_reference=gateway_reference,
        reason_code="QRIS_GATEWAY_VERIFIED",
    )


def verify_bank_transfer(
    intent: PaymentIntent,
    *,
    bank_reference: str,
    bank_status: str,
    amount: Decimal,
) -> VerificationResult:
    if bank_reference != intent.expected_reference:
        return _pending(intent, reason_code="BANK_REFERENCE_MISMATCH")

    if _normalized_status(bank_status) != "confirmed":
        return _pending(intent, reason_code="BANK_TRANSFER_NOT_CONFIRMED")

    if amount != intent.amount:
        return _pending(intent, reason_code="BANK_AMOUNT_MISMATCH")

    return VerificationResult(
        transaction_id=intent.transaction_id,
        method=intent.method,
        amount=intent.amount,
        status=PaymentStatus.PAID,
        verified_reference=bank_reference,
        reason_code="BANK_TRANSFER_VERIFIED",
    )


def submit_manual_proof(
    intent: PaymentIntent,
    *,
    proof_document_id: str,
    uploaded_by: str,
) -> VerificationResult:
    return VerificationResult(
        transaction_id=intent.transaction_id,
        method=intent.method,
        amount=intent.amount,
        status=PaymentStatus.PAYMENT_REVIEW_REQUIRED,
        proof_document_id=proof_document_id,
        uploaded_by=uploaded_by,
        reason_code="MANUAL_PROOF_REVIEW_REQUIRED",
    )


def approve_manual_payment(
    review_result: VerificationResult,
    *,
    reviewer_id: str,
    verified_reference: str,
) -> VerificationResult:
    return replace(
        review_result,
        status=PaymentStatus.PAID,
        reviewed_by=reviewer_id,
        verified_reference=verified_reference,
        reason_code="MANUAL_PAYMENT_APPROVED",
    )


def _pending(intent: PaymentIntent, *, reason_code: str) -> VerificationResult:
    return VerificationResult(
        transaction_id=intent.transaction_id,
        method=intent.method,
        amount=intent.amount,
        status=PaymentStatus.PAYMENT_PENDING,
        reason_code=reason_code,
    )


def _normalized_status(value: str) -> str:
    return value.strip().lower()
