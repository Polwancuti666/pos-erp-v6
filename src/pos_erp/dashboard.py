
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True)
class BranchSnapshot:
    branch_code: str
    operational_sales: Decimal
    paid_pending_posting: Decimal
    posted_revenue: Decimal
    unreconciled_variance: Decimal
    pending_sync_count: int
    failed_retry_count: int
    last_sync_at: str


@dataclass(frozen=True)
class BranchDashboardRow(BranchSnapshot):
    is_stale: bool
    queue_alert: bool
    sla_alert: bool


@dataclass(frozen=True)
class OwnerDashboard:
    branches: list[BranchDashboardRow]
    total_operational_sales: Decimal
    total_posted_revenue: Decimal
    total_pending_sync_count: int


def build_owner_dashboard(snapshots: list[BranchSnapshot], *, now: str, stale_after_minutes: int = 30) -> OwnerDashboard:
    current = datetime.fromisoformat(now)
    rows = []
    for s in snapshots:
        is_stale = datetime.fromisoformat(s.last_sync_at) + timedelta(minutes=stale_after_minutes) < current
        rows.append(BranchDashboardRow(**s.__dict__, is_stale=is_stale, queue_alert=s.pending_sync_count > 50, sla_alert=s.failed_retry_count >= 3))
    return OwnerDashboard(
        branches=rows,
        total_operational_sales=sum((r.operational_sales for r in rows), Decimal("0.00")),
        total_posted_revenue=sum((r.posted_revenue for r in rows), Decimal("0.00")),
        total_pending_sync_count=sum(r.pending_sync_count for r in rows),
    )
