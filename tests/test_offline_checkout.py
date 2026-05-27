from decimal import Decimal

import pytest

from pos_erp.checkout import (
    OfflinePaymentNotAllowed,
    PaymentType,
    TransactionStatus,
    complete_offline_checkout,
)


def test_offline_cash_checkout_creates_temp_id_and_offline_confirmed_status():
    transaction = complete_offline_checkout(
        branch_code="JKT01",
        device_id="POSA",
        local_sequence=7,
        business_date="20260526",
        cashier_id="cashier-1",
        payment_type=PaymentType.CASH,
        gross_amount=Decimal("250000.00"),
    )

    assert transaction.local_temp_id == "TMP-JKT01-POSA-20260526-000007"
    assert transaction.status is TransactionStatus.OFFLINE_CASH_CONFIRMED
    assert transaction.payment_type is PaymentType.CASH
    assert transaction.branch_code == "JKT01"
    assert transaction.device_id == "POSA"
    assert transaction.cashier_id == "cashier-1"
    assert transaction.gross_amount == Decimal("250000.00")
    assert transaction.final_pos_code is None


def test_offline_qris_cannot_be_marked_paid_and_remains_payment_pending():
    with pytest.raises(OfflinePaymentNotAllowed) as exc_info:
        complete_offline_checkout(
            branch_code="JKT01",
            device_id="POSA",
            local_sequence=8,
            business_date="20260526",
            cashier_id="cashier-1",
            payment_type=PaymentType.QRIS,
            gross_amount=Decimal("250000.00"),
        )

    pending = exc_info.value.pending_transaction
    assert pending.local_temp_id == "TMP-JKT01-POSA-20260526-000008"
    assert pending.status is TransactionStatus.PAYMENT_PENDING
    assert pending.payment_type is PaymentType.QRIS
    assert "cannot become PAID while offline" in str(exc_info.value)


def test_offline_bank_transfer_cannot_be_marked_paid_and_remains_payment_pending():
    with pytest.raises(OfflinePaymentNotAllowed) as exc_info:
        complete_offline_checkout(
            branch_code="BDG01",
            device_id="POSB",
            local_sequence=12,
            business_date="20260526",
            cashier_id="cashier-2",
            payment_type=PaymentType.BANK_TRANSFER,
            gross_amount=Decimal("500000.00"),
        )

    pending = exc_info.value.pending_transaction
    assert pending.local_temp_id == "TMP-BDG01-POSB-20260526-000012"
    assert pending.status is TransactionStatus.PAYMENT_PENDING
    assert pending.payment_type is PaymentType.BANK_TRANSFER
    assert pending.final_pos_code is None
