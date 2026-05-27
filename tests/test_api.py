
from decimal import Decimal
from pos_erp.api import AppService
from pos_erp.checkout import PaymentType, TransactionStatus
from pos_erp.permissions import Role


def test_service_creates_offline_cash_checkout_and_persists_transaction():
    service = AppService()
    result = service.complete_offline_checkout(
        branch_code="JKT01", device_id="POSA", local_sequence=1, business_date="20260526", cashier_id="cashier-1", payment_type=PaymentType.CASH, gross_amount=Decimal("100000.00")
    )
    assert result.status is TransactionStatus.OFFLINE_CASH_CONFIRMED
    assert service.repository.get("transactions", result.local_temp_id)["status"] == "OFFLINE_CASH_CONFIRMED"


def test_service_denies_unauthorized_refund_and_audits_denial():
    service = AppService()
    decision = service.authorize(role=Role.CASHIER, action_name="REFUND_AFTER_POSTING", actor_id="cashier-1", branch_code="JKT01", device_id="POSA", reference_id="TRX-001")
    assert decision.allowed is False
    assert service.audit_log.for_reference("TRX-001")[0].action == "AUTHORIZATION_DENIED"


def test_service_builds_dashboard_from_repository_snapshots():
    service = AppService()
    service.repository.save("branch_snapshots", "JKT01", {
        "branch_code":"JKT01", "operational_sales":"100.00", "paid_pending_posting":"10.00", "posted_revenue":"90.00", "unreconciled_variance":"0.00", "pending_sync_count":1, "failed_retry_count":0, "last_sync_at":"2026-05-26T10:00:00+07:00"
    })
    dashboard = service.owner_dashboard(now="2026-05-26T10:00:00+07:00")
    assert dashboard.total_operational_sales == Decimal("100.00")
