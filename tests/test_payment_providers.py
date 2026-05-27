from decimal import Decimal
from pos_erp.payment_providers import BcaConfig, BcaVirtualAccountAdapter, MidtransAdapter, MidtransConfig, PaymentProviderStatus


def test_bca_virtual_account_adapter_builds_payment_intent_payload():
    adapter = BcaVirtualAccountAdapter(BcaConfig(company_code="12345", channel_id="95051", client_id="bca-client"))
    payload = adapter.create_virtual_account_intent(order_id="TRX-001", customer_number="000123", amount=Decimal("250000.00"))
    assert payload.provider == "BCA"
    assert payload.reference == "12345000123"
    assert payload.amount == Decimal("250000.00")
    assert payload.status is PaymentProviderStatus.PENDING


def test_bca_callback_maps_paid_status_when_reference_and_amount_match():
    adapter = BcaVirtualAccountAdapter(BcaConfig(company_code="12345", channel_id="95051", client_id="bca-client"))
    result = adapter.parse_callback({"virtual_account": "12345000123", "amount": "250000.00", "payment_flag_status": "00"})
    assert result.reference == "12345000123"
    assert result.status is PaymentProviderStatus.PAID


def test_midtrans_adapter_builds_qris_charge_payload():
    adapter = MidtransAdapter(MidtransConfig(server_key="server", merchant_id="merchant"))
    payload = adapter.create_qris_charge(order_id="TRX-002", amount=Decimal("175000.00"), customer_name="Dipa")
    assert payload["payment_type"] == "qris"
    assert payload["transaction_details"]["order_id"] == "TRX-002"
    assert payload["transaction_details"]["gross_amount"] == 175000
    assert payload["customer_details"]["first_name"] == "Dipa"


def test_midtrans_notification_verifies_signature_and_settlement_status():
    adapter = MidtransAdapter(MidtransConfig(server_key="server", merchant_id="merchant"))
    notification = {"order_id": "TRX-002", "status_code": "200", "gross_amount": "175000.00", "transaction_status": "settlement"}
    notification["signature_key"] = adapter.sign_notification(notification)
    result = adapter.parse_notification(notification)
    assert result.valid_signature is True
    assert result.reference == "TRX-002"
    assert result.status is PaymentProviderStatus.PAID
