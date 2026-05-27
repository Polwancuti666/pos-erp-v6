from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class PaymentType(str, Enum):
    CASH = "cash"
    QRIS = "qris"
    BANK_TRANSFER = "bank_transfer"


class TransactionStatus(str, Enum):
    PAYMENT_PENDING = "PAYMENT_PENDING"
    OFFLINE_CASH_CONFIRMED = "OFFLINE_CASH_CONFIRMED"


@dataclass(frozen=True)
class OfflineTransaction:
    local_temp_id: str
    branch_code: str
    device_id: str
    cashier_id: str
    payment_type: PaymentType
    gross_amount: Decimal
    status: TransactionStatus
    final_pos_code: str | None = None


class OfflinePaymentNotAllowed(Exception):
    def __init__(self, message: str, pending_transaction: OfflineTransaction):
        super().__init__(message)
        self.pending_transaction = pending_transaction


def build_local_temp_id(
    *,
    branch_code: str,
    device_id: str,
    business_date: str,
    local_sequence: int,
) -> str:
    return f"TMP-{branch_code}-{device_id}-{business_date}-{local_sequence:06d}"


def complete_offline_checkout(
    *,
    branch_code: str,
    device_id: str,
    local_sequence: int,
    business_date: str,
    cashier_id: str,
    payment_type: PaymentType,
    gross_amount: Decimal,
) -> OfflineTransaction:
    local_temp_id = build_local_temp_id(
        branch_code=branch_code,
        device_id=device_id,
        business_date=business_date,
        local_sequence=local_sequence,
    )

    if payment_type is PaymentType.CASH:
        return OfflineTransaction(
            local_temp_id=local_temp_id,
            branch_code=branch_code,
            device_id=device_id,
            cashier_id=cashier_id,
            payment_type=payment_type,
            gross_amount=gross_amount,
            status=TransactionStatus.OFFLINE_CASH_CONFIRMED,
        )

    pending = OfflineTransaction(
        local_temp_id=local_temp_id,
        branch_code=branch_code,
        device_id=device_id,
        cashier_id=cashier_id,
        payment_type=payment_type,
        gross_amount=gross_amount,
        status=TransactionStatus.PAYMENT_PENDING,
    )
    raise OfflinePaymentNotAllowed(
        f"{payment_type.value} cannot become PAID while offline; transaction remains PAYMENT_PENDING.",
        pending,
    )
