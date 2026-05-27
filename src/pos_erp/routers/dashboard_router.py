"""Dashboard API router.

Provides owner/manager dashboard metrics and active system alerts.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter

from pos_erp.dashboard import (
    BranchDashboardRow,
    BranchSnapshot,
    build_owner_dashboard,
)
from pos_erp.exception_queue import ExceptionQueue, ExceptionStatus

from pos_erp.routers.models import (
    AlertItem,
    BranchSnapshotResponse,
    DashboardAlertsResponse,
    DashboardSummaryResponse,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# ── Demo data (in-memory) ────────────────────────────────────────────────────


def _build_demo_snapshots() -> list[BranchSnapshot]:
    now = datetime.datetime.now()
    return [
        BranchSnapshot(
            branch_code="HQ",
            operational_sales=Decimal("15000000"),
            paid_pending_posting=Decimal("3000000"),
            posted_revenue=Decimal("12000000"),
            unreconciled_variance=Decimal("25000"),
            pending_sync_count=5,
            failed_retry_count=0,
            last_sync_at=(now - datetime.timedelta(minutes=10)).isoformat(),
        ),
        BranchSnapshot(
            branch_code="BDG-01",
            operational_sales=Decimal("8500000"),
            paid_pending_posting=Decimal("1200000"),
            posted_revenue=Decimal("7300000"),
            unreconciled_variance=Decimal("0"),
            pending_sync_count=62,
            failed_retry_count=3,
            last_sync_at=(now - datetime.timedelta(minutes=45)).isoformat(),
        ),
    ]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/summary",
    summary="Ringkasan dashboard",
    responses={200: {"model": DashboardSummaryResponse}},
)
async def dashboard_summary():
    """
    Mengambil ringkasan metrik dashboard untuk semua cabang.

    Termasuk total penjualan operasional, revenue yang sudah diposting,
    jumlah sync tertanda, serta flag alert untuk setiap cabang.
    """
    snapshots = _build_demo_snapshots()
    now = datetime.datetime.now().isoformat()
    dashboard = build_owner_dashboard(snapshots, now=now)

    branches = []
    for row in dashboard.branches:
        branches.append(BranchSnapshotResponse(
            branch_code=row.branch_code,
            operational_sales=str(row.operational_sales),
            paid_pending_posting=str(row.paid_pending_posting),
            posted_revenue=str(row.posted_revenue),
            unreconciled_variance=str(row.unreconciled_variance),
            pending_sync_count=row.pending_sync_count,
            failed_retry_count=row.failed_retry_count,
            last_sync_at=row.last_sync_at,
            is_stale=row.is_stale,
            queue_alert=row.queue_alert,
            sla_alert=row.sla_alert,
        ))

    return DashboardSummaryResponse(
        branches=branches,
        total_operational_sales=str(dashboard.total_operational_sales),
        total_posted_revenue=str(dashboard.total_posted_revenue),
        total_pending_sync_count=dashboard.total_pending_sync_count,
    ).model_dump()


@router.get(
    "/alerts",
    summary="Alert aktif",
    responses={200: {"model": DashboardAlertsResponse}},
)
async def dashboard_alerts():
    """
    Mengambil daftar alert aktif yang memerlukan perhatian.

    Alert mencakup:
    - Cabang yang stale (tidak sync > 30 menit)
    - Queue overflow (> 50 transaksi pending)
    - SLA breach (retry count >= 3)
    - Exception yang overdue
    """
    snapshots = _build_demo_snapshots()
    now = datetime.datetime.now().isoformat()
    dashboard = build_owner_dashboard(snapshots, now=now)

    alerts: list[AlertItem] = []

    for row in dashboard.branches:
        if row.is_stale:
            alerts.append(AlertItem(
                alert_type="STALE_SYNC",
                severity="WARNING",
                message=f"Cabang {row.branch_code} tidak melakukan sinkronisasi lebih dari 30 menit",
                branch_code=row.branch_code,
            ))

        if row.queue_alert:
            alerts.append(AlertItem(
                alert_type="QUEUE_OVERFLOW",
                severity="CRITICAL",
                message=f"Cabang {row.branch_code} memiliki {row.pending_sync_count} transaksi pending (threshold: 50)",
                branch_code=row.branch_code,
            ))

        if row.sla_alert:
            alerts.append(AlertItem(
                alert_type="SLA_BREACH",
                severity="CRITICAL",
                message=f"Cabang {row.branch_code} mengalami {row.failed_retry_count} kegagalan sinkronisasi berturut-turut",
                branch_code=row.branch_code,
            ))

    # Check for overdue exceptions (would need shared queue in production)
    # For demo, add a sample exception alert
    alerts.append(AlertItem(
        alert_type="EXCEPTION_OVERDUE",
        severity="WARNING",
        message="Terdapat exception yang melewati batas SLA. Periksa halaman Exception Queue.",
        branch_code="SYSTEM",
    ))

    return DashboardAlertsResponse(alerts=alerts).model_dump()
