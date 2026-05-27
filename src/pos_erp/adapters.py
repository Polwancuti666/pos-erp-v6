
from __future__ import annotations
import hashlib, hmac, json
from dataclasses import dataclass
from decimal import Decimal
from pos_erp.document_finalization import DocumentNumbers
from pos_erp.document_numbering import DocumentKind, NumberingService

@dataclass(frozen=True)
class GatewayCallback:
    reference: str | None
    status: str | None
    amount: Decimal
    valid_signature: bool

class PaymentGatewayAdapter:
    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
    def sign(self, payload: dict[str, str]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    def parse_callback(self, payload: dict[str, str], *, signature: str) -> GatewayCallback:
        valid = hmac.compare_digest(self.sign(payload), signature)
        return GatewayCallback(payload.get("reference"), payload.get("status"), Decimal(payload.get("amount", "0.00")), valid)

@dataclass(frozen=True)
class ErpFinalizationResponse:
    accepted: bool
    idempotency_key: str
    numbers: DocumentNumbers

class ErpAdapter:
    def __init__(self, base_url: str, numbering: NumberingService | None = None):
        self.base_url = base_url
        self.numbering = numbering or NumberingService()
    def finalize_transaction(self, *, branch_code: str, business_date: str, idempotency_key: str) -> ErpFinalizationResponse:
        return ErpFinalizationResponse(True, idempotency_key, DocumentNumbers(
            pos_number=self.numbering.issue(DocumentKind.POS, branch_code=branch_code, business_date=business_date),
            trm_number=self.numbering.issue(DocumentKind.TRM, branch_code=branch_code, business_date=business_date),
            journal_number=self.numbering.issue(DocumentKind.JRN, branch_code=branch_code, business_date=business_date),
        ))
