
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class AuditSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

@dataclass(frozen=True)
class AuditEntry:
    audit_id: str
    action: str
    actor_id: str
    branch_code: str
    device_id: str
    reference_id: str
    severity: AuditSeverity
    metadata: dict[str, object]

class AuditLog:
    def __init__(self):
        self._entries: list[AuditEntry] = []
    def record(self, action: str, actor_id: str, branch_code: str, device_id: str, reference_id: str, severity: AuditSeverity, metadata: dict[str, object]) -> AuditEntry:
        entry = AuditEntry(f"AUD-{len(self._entries)+1:06d}", action, actor_id, branch_code, device_id, reference_id, severity, dict(metadata))
        self._entries.append(entry)
        return entry
    def for_reference(self, reference_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.reference_id == reference_id]
    def by_severity(self, severity: AuditSeverity) -> list[AuditEntry]:
        return [e for e in self._entries if e.severity is severity]
