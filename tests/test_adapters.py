
from decimal import Decimal
from pos_erp.adapters import ErpAdapter, PaymentGatewayAdapter


def test_payment_gateway_adapter_verifies_callback_signature_and_reference():
    adapter = PaymentGatewayAdapter(webhook_secret="secret")
    payload = {"reference": "QRIS-123", "status": "settled", "amount": "100000.00"}
    signature = adapter.sign(payload)
    result = adapter.parse_callback(payload, signature=signature)
    assert result.valid_signature is True
    assert result.reference == "QRIS-123"
    assert result.amount == Decimal("100000.00")


def test_payment_gateway_adapter_rejects_invalid_signature():
    adapter = PaymentGatewayAdapter(webhook_secret="secret")
    result = adapter.parse_callback({"reference": "QRIS-123", "status": "settled", "amount": "1.00"}, signature="bad")
    assert result.valid_signature is False


def test_erp_adapter_returns_final_numbers_and_preserves_idempotency_key():
    adapter = ErpAdapter(base_url="https://erp.example.test")
    response = adapter.finalize_transaction(
        branch_code="JKT01",
        business_date="20260526",
        idempotency_key="JKT01:TMP-001",
    )
    assert response.idempotency_key == "JKT01:TMP-001"
    assert response.numbers.pos_number.startswith("POS-JKT01-20260526-")
    assert response.accepted is True
