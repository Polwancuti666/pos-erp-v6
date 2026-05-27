
from __future__ import annotations

from enum import Enum


class DocumentKind(str, Enum):
    POS = "POS"
    TRM = "TRM"
    JRN = "JRN"
    INVENTORY_MOVEMENT = "INV-MOV"


class NumberingService:
    def __init__(self, existing_counters: dict[tuple[DocumentKind, str, str], int] | None = None):
        self._counters = dict(existing_counters or {})

    def issue(self, kind: DocumentKind, *, branch_code: str, business_date: str) -> str:
        key = (kind, branch_code, business_date)
        next_sequence = self._counters.get(key, 0) + 1
        self._counters[key] = next_sequence
        return f"{kind.value}-{branch_code}-{business_date}-{next_sequence:06d}"
