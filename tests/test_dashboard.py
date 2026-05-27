
from decimal import Decimal

from pos_erp.dashboard import BranchSnapshot, build_owner_dashboard


def test_dashboard_separates_operational_paid_pending_posted_and_variance_metrics():
    dashboard = build_owner_dashboard([
        BranchSnapshot(
            branch_code="JKT01",
            operational_sales=Decimal("1000000.00"),
            paid_pending_posting=Decimal("250000.00"),
            posted_revenue=Decimal("750000.00"),
            unreconciled_variance=Decimal("50000.00"),
            pending_sync_count=3,
            failed_retry_count=1,
            last_sync_at="2026-05-26T09:55:00+07:00",
        )
    ], now="2026-05-26T10:00:00+07:00")
    branch = dashboard.branches[0]
    assert branch.branch_code == "JKT01"
    assert branch.operational_sales == Decimal("1000000.00")
    assert branch.paid_pending_posting == Decimal("250000.00")
    assert branch.posted_revenue == Decimal("750000.00")
    assert branch.unreconciled_variance == Decimal("50000.00")
    assert branch.is_stale is False


def test_dashboard_flags_stale_branch_data_and_queue_alerts():
    dashboard = build_owner_dashboard([
        BranchSnapshot(
            branch_code="BDG01",
            operational_sales=Decimal("0.00"),
            paid_pending_posting=Decimal("0.00"),
            posted_revenue=Decimal("0.00"),
            unreconciled_variance=Decimal("0.00"),
            pending_sync_count=51,
            failed_retry_count=4,
            last_sync_at="2026-05-26T08:00:00+07:00",
        )
    ], now="2026-05-26T10:00:00+07:00", stale_after_minutes=30)
    branch = dashboard.branches[0]
    assert branch.is_stale is True
    assert branch.queue_alert is True
    assert branch.sla_alert is True


def test_dashboard_rolls_up_multi_branch_totals():
    dashboard = build_owner_dashboard([
        BranchSnapshot("JKT01", Decimal("100.00"), Decimal("20.00"), Decimal("80.00"), Decimal("1.00"), 1, 0, "2026-05-26T10:00:00+07:00"),
        BranchSnapshot("BDG01", Decimal("300.00"), Decimal("30.00"), Decimal("270.00"), Decimal("2.00"), 2, 0, "2026-05-26T10:00:00+07:00"),
    ], now="2026-05-26T10:00:00+07:00")
    assert dashboard.total_operational_sales == Decimal("400.00")
    assert dashboard.total_posted_revenue == Decimal("350.00")
    assert dashboard.total_pending_sync_count == 3
