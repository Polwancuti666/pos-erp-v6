from decimal import Decimal

from pos_erp.checkout import PaymentType, complete_offline_checkout
from pos_erp.sync import OutboxStatus, SyncQueue, build_sync_payload


def test_sync_payload_includes_required_idempotency_and_financial_hash():
    transaction = complete_offline_checkout(
        branch_code="JKT01",
        device_id="POSA",
        local_sequence=7,
        business_date="20260526",
        cashier_id="cashier-1",
        payment_type=PaymentType.CASH,
        gross_amount=Decimal("250000.00"),
    )

    payload = build_sync_payload(transaction, timestamp="2026-05-26T09:00:00Z")

    assert payload["idempotency_key"] == "JKT01:POSA:TMP-JKT01-POSA-20260526-000007"
    assert payload["branch_code"] == "JKT01"
    assert payload["device_id"] == "POSA"
    assert payload["local_temp_id"] == "TMP-JKT01-POSA-20260526-000007"
    assert payload["cashier_id"] == "cashier-1"
    assert payload["timestamp"] == "2026-05-26T09:00:00Z"
    assert payload["financial_hash"]


def test_sync_worker_isolates_failed_item_and_continues_later_items():
    queue = SyncQueue()
    failed = queue.enqueue({"idempotency_key": "fail-1"})
    valid = queue.enqueue({"idempotency_key": "ok-1"})

    def sender(payload):
        if payload["idempotency_key"] == "fail-1":
            raise ValueError("ERP validation failed")
        return {"erp_document_id": "POS-JKT01-20260526-000001"}

    results = queue.run_once(sender)

    assert results == ["failed", "synced"]
    assert failed.status is OutboxStatus.RETRYABLE_FAILED
    assert failed.attempts == 1
    assert failed.last_error == "ERP validation failed"
    assert valid.status is OutboxStatus.SYNCED
    assert valid.erp_document_id == "POS-JKT01-20260526-000001"


def test_sync_item_escalates_after_three_failed_attempts():
    queue = SyncQueue()
    item = queue.enqueue({"idempotency_key": "bad-1"})

    def sender(payload):
        raise RuntimeError("network timeout")

    queue.run_once(sender)
    queue.run_once(sender)
    queue.run_once(sender)

    assert item.status is OutboxStatus.ESCALATED
    assert item.attempts == 3
    assert item.last_error == "network timeout"
