from decimal import Decimal

from pos_erp.payment import (
    PaymentIntent,
    PaymentMethod,
    PaymentStatus,
    VerificationResult,
    approve_manual_payment,
    submit_manual_proof,
    verify_bank_transfer,
    verify_qris_callback,
)


def test_online_qris_becomes_paid_only_after_valid_gateway_callback():
    intent = PaymentIntent(
        transaction_id="TRX-001",
        method=PaymentMethod.QRIS,
        amount=Decimal("150000.00"),
        expected_reference="QRIS-REF-123",
        online=True,
    )

    result = verify_qris_callback(
        intent,
        gateway_reference="QRIS-REF-123",
        gateway_status="settled",
        amount=Decimal("150000.00"),
    )

    assert result.status is PaymentStatus.PAID
    assert result.verified_reference == "QRIS-REF-123"
    assert result.reason_code == "QRIS_GATEWAY_VERIFIED"


def test_online_qris_with_wrong_reference_remains_payment_pending():
    intent = PaymentIntent(
        transaction_id="TRX-002",
        method=PaymentMethod.QRIS,
        amount=Decimal("150000.00"),
        expected_reference="QRIS-REF-123",
        online=True,
    )

    result = verify_qris_callback(
        intent,
        gateway_reference="QRIS-REF-WRONG",
        gateway_status="settled",
        amount=Decimal("150000.00"),
    )

    assert result.status is PaymentStatus.PAYMENT_PENDING
    assert result.verified_reference is None
    assert result.reason_code == "QRIS_REFERENCE_MISMATCH"


def test_offline_qris_cannot_become_paid_and_remains_pending():
    intent = PaymentIntent(
        transaction_id="TRX-003",
        method=PaymentMethod.QRIS,
        amount=Decimal("150000.00"),
        expected_reference="QRIS-REF-123",
        online=False,
    )

    result = verify_qris_callback(
        intent,
        gateway_reference="QRIS-REF-123",
        gateway_status="settled",
        amount=Decimal("150000.00"),
    )

    assert result.status is PaymentStatus.PAYMENT_PENDING
    assert result.reason_code == "QRIS_OFFLINE_CANNOT_VERIFY"


def test_bank_transfer_requires_bank_reference_and_amount_match_before_paid():
    intent = PaymentIntent(
        transaction_id="TRX-004",
        method=PaymentMethod.BANK_TRANSFER,
        amount=Decimal("275000.00"),
        expected_reference="BNK-REF-987",
        online=True,
    )

    result = verify_bank_transfer(
        intent,
        bank_reference="BNK-REF-987",
        bank_status="confirmed",
        amount=Decimal("275000.00"),
    )

    assert result.status is PaymentStatus.PAID
    assert result.verified_reference == "BNK-REF-987"
    assert result.reason_code == "BANK_TRANSFER_VERIFIED"


def test_manual_proof_upload_stays_payment_review_required_until_verified():
    intent = PaymentIntent(
        transaction_id="TRX-005",
        method=PaymentMethod.BANK_TRANSFER,
        amount=Decimal("350000.00"),
        expected_reference="MANUAL-REF-1",
        online=True,
    )

    result = submit_manual_proof(
        intent,
        proof_document_id="proof-img-001",
        uploaded_by="cashier-1",
    )

    assert result.status is PaymentStatus.PAYMENT_REVIEW_REQUIRED
    assert result.proof_document_id == "proof-img-001"
    assert result.verified_reference is None
    assert result.reason_code == "MANUAL_PROOF_REVIEW_REQUIRED"


def test_approved_manual_payment_becomes_paid_with_reviewer_audit():
    review_result = VerificationResult(
        transaction_id="TRX-006",
        method=PaymentMethod.BANK_TRANSFER,
        amount=Decimal("350000.00"),
        status=PaymentStatus.PAYMENT_REVIEW_REQUIRED,
        proof_document_id="proof-img-002",
        reason_code="MANUAL_PROOF_REVIEW_REQUIRED",
    )

    approved = approve_manual_payment(
        review_result,
        reviewer_id="finance-lead-1",
        verified_reference="BNK-MANUAL-002",
    )

    assert approved.status is PaymentStatus.PAID
    assert approved.reviewed_by == "finance-lead-1"
    assert approved.verified_reference == "BNK-MANUAL-002"
    assert approved.reason_code == "MANUAL_PAYMENT_APPROVED"
