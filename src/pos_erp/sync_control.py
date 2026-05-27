
from __future__ import annotations

from dataclasses import dataclass

from pos_erp.permissions import Action, Role, authorize_action


@dataclass(frozen=True)
class ConnectivityNotice:
    recovered: bool
    queued_count: int
    requires_approval: bool


@dataclass(frozen=True)
class SyncApproval:
    batch_id: str
    approver_id: str
    approver_role: Role
    approved: bool
    queued_count: int
    retry_schedule_seconds: tuple[int, int, int] = (10, 120, 1200)


class SyncApprovalRequired(Exception):
    def __init__(self, required_roles: tuple[Role, ...]):
        super().__init__("Manual sync batch requires manager/owner/IT approval")
        self.required_roles = required_roles


@dataclass(frozen=True)
class BranchCache:
    service_catalog_version: str | None
    staff_schedule_version: str | None
    price_matrix_version: str | None
    branch_config_version: str | None

    @property
    def is_ready_for_offline(self) -> bool:
        return all([self.service_catalog_version, self.staff_schedule_version, self.price_matrix_version, self.branch_config_version])


@dataclass(frozen=True)
class DeviceBinding:
    device_id: str
    branch_code: str
    active: bool

    def allows(self, *, branch_code: str, device_id: str) -> bool:
        return self.active and self.branch_code == branch_code and self.device_id == device_id


def detect_connectivity_recovery(*, was_online: bool, is_online: bool, queued_count: int) -> ConnectivityNotice:
    recovered = not was_online and is_online
    return ConnectivityNotice(recovered=recovered, queued_count=queued_count, requires_approval=recovered and queued_count > 0)


def approve_sync_batch(*, batch_id: str, approver_role: Role, approver_id: str, queued_count: int) -> SyncApproval:
    decision = authorize_action(approver_role, Action.APPROVE_MANUAL_SYNC)
    if not decision.allowed:
        raise SyncApprovalRequired(decision.required_roles)
    return SyncApproval(batch_id=batch_id, approver_id=approver_id, approver_role=approver_role, approved=True, queued_count=queued_count)
