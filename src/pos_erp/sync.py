from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from pos_erp.checkout import OfflineTransaction


class OutboxStatus(str, Enum):
    PENDING = "PENDING"
    RETRYABLE_FAILED = "RETRYABLE_FAILED"
    SYNCED = "SYNCED"
    ESCALATED = "ESCALATED"


@dataclass
class OutboxItem:
    payload: dict[str, Any]
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    erp_document_id: str | None = None


def build_sync_payload(transaction: OfflineTransaction, *, timestamp: str) -> dict[str, str]:
    financial_basis = "|".join(
        [
            transaction.local_temp_id,
            transaction.payment_type.value,
            str(transaction.gross_amount),
        ]
    )
    financial_hash = hashlib.sha256(financial_basis.encode("utf-8")).hexdigest()

    return {
        "idempotency_key": f"{transaction.branch_code}:{transaction.device_id}:{transaction.local_temp_id}",
        "branch_code": transaction.branch_code,
        "device_id": transaction.device_id,
        "local_temp_id": transaction.local_temp_id,
        "cashier_id": transaction.cashier_id,
        "timestamp": timestamp,
        "financial_hash": financial_hash,
    }


class SyncQueue:
    def __init__(self) -> None:
        self._items: list[OutboxItem] = []

    def enqueue(self, payload: dict[str, Any]) -> OutboxItem:
        item = OutboxItem(payload=payload)
        self._items.append(item)
        return item

    def run_once(self, sender: Callable[[dict[str, Any]], dict[str, Any]]) -> list[str]:
        results: list[str] = []
        for item in self._items:
            if item.status in {OutboxStatus.SYNCED, OutboxStatus.ESCALATED}:
                continue
            try:
                response = sender(item.payload)
            except Exception as exc:  # isolate failure and continue later items
                item.attempts += 1
                item.last_error = str(exc)
                item.status = (
                    OutboxStatus.ESCALATED
                    if item.attempts >= 3
                    else OutboxStatus.RETRYABLE_FAILED
                )
                results.append("failed")
                continue

            item.status = OutboxStatus.SYNCED
            item.erp_document_id = response.get("erp_document_id")
            results.append("synced")
        return results
