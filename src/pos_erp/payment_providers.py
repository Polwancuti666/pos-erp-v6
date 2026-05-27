from __future__ import annotations
import hashlib
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class PaymentProviderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"

@dataclass(frozen=True)
class ProviderIntent:
    provider: str
    reference: str
    amount: Decimal
    status: PaymentProviderStatus

@dataclass(frozen=True)
class ProviderCallback:
    provider: str
    reference: str | None
    amount: Decimal
    status: PaymentProviderStatus
    valid_signature: bool = True

@dataclass(frozen=True)
class BcaConfig:
    company_code: str
    channel_id: str
    client_id: str

class BcaVirtualAccountAdapter:
    def __init__(self, config: BcaConfig):
        self.config = config
    def create_virtual_account_intent(self, *, order_id: str, customer_number: str, amount: Decimal) -> ProviderIntent:
        return ProviderIntent("BCA", f"{self.config.company_code}{customer_number}", amount, PaymentProviderStatus.PENDING)
    def parse_callback(self, payload: dict[str, str]) -> ProviderCallback:
        status = PaymentProviderStatus.PAID if payload.get("payment_flag_status") == "00" else PaymentProviderStatus.FAILED
        return ProviderCallback("BCA", payload.get("virtual_account"), Decimal(payload.get("amount", "0.00")), status)

@dataclass(frozen=True)
class MidtransConfig:
    server_key: str
    merchant_id: str

class MidtransAdapter:
    def __init__(self, config: MidtransConfig):
        self.config = config
    def create_qris_charge(self, *, order_id: str, amount: Decimal, customer_name: str) -> dict[str, object]:
        return {"payment_type": "qris", "transaction_details": {"order_id": order_id, "gross_amount": int(amount)}, "customer_details": {"first_name": customer_name}}
    def sign_notification(self, notification: dict[str, str]) -> str:
        raw = notification["order_id"] + notification["status_code"] + notification["gross_amount"] + self.config.server_key
        return hashlib.sha512(raw.encode()).hexdigest()
    def parse_notification(self, notification: dict[str, str]) -> ProviderCallback:
        valid = notification.get("signature_key") == self.sign_notification(notification)
        status = PaymentProviderStatus.PAID if valid and notification.get("transaction_status") in {"settlement", "capture"} else PaymentProviderStatus.PENDING
        return ProviderCallback("MIDTRANS", notification.get("order_id"), Decimal(notification.get("gross_amount", "0.00")), status, valid)
