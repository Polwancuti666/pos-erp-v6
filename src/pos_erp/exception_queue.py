
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum


class ExceptionType(str, Enum):
    SYNC_FAILURE = "SYNC_FAILURE"
    UNMAPPED_COA = "UNMAPPED_COA"
    PAYMENT_REVIEW_REQUIRED = "PAYMENT_REVIEW_REQUIRED"
    RECONCILIATION_MISMATCH = "RECONCILIATION_MISMATCH"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    PAYLOAD_VALIDATION = "PAYLOAD_VALIDATION"


class ExceptionStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True)
class ExceptionItem:
    exception_id: str
    exception_type: ExceptionType
    reference_id: str
    created_at: str
    owner_roles: tuple[str, ...]
    sla_hours: int
    status: ExceptionStatus = ExceptionStatus.OPEN
    resolved_by: str | None = None
    resolution: str | None = None


_SLA = {
    ExceptionType.SYNC_FAILURE: (("IT_ADMIN", "BRANCH_MANAGER"), 2),
    ExceptionType.UNMAPPED_COA: (("ACCOUNTING_LEAD",), 24),
    ExceptionType.PAYMENT_REVIEW_REQUIRED: (("BRANCH_MANAGER", "ACCOUNTING_LEAD"), 2),
    ExceptionType.RECONCILIATION_MISMATCH: (("ACCOUNTING_LEAD", "OWNER"), 24),
    ExceptionType.DUPLICATE_EVENT: (("SYSTEM_ADMIN",), 4),
    ExceptionType.PAYLOAD_VALIDATION: (("IT_ADMIN",), 2),
}


class ExceptionQueue:
    def __init__(self):
        self._items: dict[str, ExceptionItem] = {}

    def add(self, exception_type: ExceptionType, *, reference_id: str, created_at: str) -> ExceptionItem:
        owners, hours = _SLA[exception_type]
        item = ExceptionItem(
            exception_id=f"EXC-{len(self._items) + 1:06d}",
            exception_type=exception_type,
            reference_id=reference_id,
            created_at=created_at,
            owner_roles=owners,
            sla_hours=hours,
        )
        self._items[item.exception_id] = item
        return item

    def get(self, exception_id: str) -> ExceptionItem:
        return self._items[exception_id]

    def resolve(self, exception_id: str, *, resolved_by: str, resolution: str) -> ExceptionItem:
        item = replace(self._items[exception_id], status=ExceptionStatus.RESOLVED, resolved_by=resolved_by, resolution=resolution)
        self._items[exception_id] = item
        return item

    def overdue_items(self, *, now: str) -> list[ExceptionItem]:
        current = datetime.fromisoformat(now)
        overdue = []
        for item in self._items.values():
            if item.status is ExceptionStatus.OPEN and datetime.fromisoformat(item.created_at) + timedelta(hours=item.sla_hours) < current:
                overdue.append(item)
        return overdue
