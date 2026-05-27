
from __future__ import annotations
from decimal import Decimal
from pos_erp.audit_log import AuditLog, AuditSeverity
from pos_erp.checkout import complete_offline_checkout as domain_offline_checkout, PaymentType
from pos_erp.dashboard import BranchSnapshot, build_owner_dashboard, OwnerDashboard
from pos_erp.persistence import InMemoryRepository, UnitOfWork
from pos_erp.permissions import Action, Role, authorize_action, AuthorizationDecision

class AppService:
    def __init__(self, repository: InMemoryRepository | None = None, audit_log: AuditLog | None = None):
        self.repository = repository or InMemoryRepository()
        self.audit_log = audit_log or AuditLog()
    def complete_offline_checkout(self, *, branch_code: str, device_id: str, local_sequence: int, business_date: str, cashier_id: str, payment_type: PaymentType, gross_amount: Decimal):
        tx = domain_offline_checkout(branch_code=branch_code, device_id=device_id, local_sequence=local_sequence, business_date=business_date, cashier_id=cashier_id, payment_type=payment_type, gross_amount=gross_amount)
        with UnitOfWork(self.repository) as uow:
            uow.stage_save("transactions", tx.local_temp_id, {"status": tx.status.value, "branch_code": tx.branch_code, "gross_amount": str(tx.gross_amount)})
        return tx
    def authorize(self, *, role: Role, action_name: str, actor_id: str, branch_code: str, device_id: str, reference_id: str) -> AuthorizationDecision:
        decision = authorize_action(role, Action[action_name])
        if not decision.allowed:
            self.audit_log.record("AUTHORIZATION_DENIED", actor_id, branch_code, device_id, reference_id, AuditSeverity.WARNING, {"action": action_name, "reason": decision.denial_reason})
        return decision
    def owner_dashboard(self, *, now: str) -> OwnerDashboard:
        snapshots = []
        for item in self.repository._data.get("branch_snapshots", {}).values():
            snapshots.append(BranchSnapshot(
                branch_code=item["branch_code"],
                operational_sales=Decimal(item["operational_sales"]),
                paid_pending_posting=Decimal(item["paid_pending_posting"]),
                posted_revenue=Decimal(item["posted_revenue"]),
                unreconciled_variance=Decimal(item["unreconciled_variance"]),
                pending_sync_count=item["pending_sync_count"],
                failed_retry_count=item["failed_retry_count"],
                last_sync_at=item["last_sync_at"],
            ))
        return build_owner_dashboard(snapshots, now=now)
