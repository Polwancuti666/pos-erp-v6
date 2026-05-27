"""Daily Closing API router.

Handles daily closing operations: summary for a date+branch,
submit closing with variance check, and retrieve closing reports.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from pos_erp.audit_log import AuditLog, AuditSeverity
from pos_erp.reconciliation import (
    ClosingDecision,
    ClosingStatus,
    ReconciliationPolicy,
    evaluate_shift_closing,
)

from pos_erp.routers.models import (
    ClosingReportResponse,
    ClosingSummaryResponse,
    ErrorResponse,
    SubmitClosingRequest,
    SubmitClosingResponse,
)

router = APIRouter(prefix="/api/daily-closing", tags=["Daily Closing"])

# ── In-memory stores ─────────────────────────────────────────────────────────

_reports: dict[str, dict] = {}
_next_report_id = 1
_audit_log = AuditLog()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/summary",
    summary="Ringkasan closing harian",
    responses={400: {"model": ErrorResponse}},
)
async def closing_summary(
    branch_code: str = Query(..., description="Kode cabang"),
    business_date: str = Query(..., description="Tanggal bisnis (YYYY-MM-DD)"),
    operational_sales: str = Query("0", description="Total penjualan operasional"),
    counted_cash: str = Query("0", description="Jumlah kas fisik"),
    pending_queued_transactions: int = Query(0, description="Jumlah transaksi tertunda"),
):
    """
    Mengambil ringkasan closing harian untuk cabang dan tanggal tertentu.

    Menghitung variance antara penjualan operasional dan kas fisik,
    serta status closing berdasarkan kebijakan toleransi.
    """
    try:
        sales = Decimal(operational_sales)
        cash = Decimal(counted_cash)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Format angka tidak valid untuk operational_sales atau counted_cash"
            ).model_dump(),
        )

    policy = ReconciliationPolicy()
    decision = evaluate_shift_closing(
        operational_sales=sales,
        counted_cash=cash,
        pending_queued_transactions=pending_queued_transactions,
        policy=policy,
    )

    return ClosingSummaryResponse(
        branch_code=branch_code,
        business_date=business_date,
        operational_sales=str(sales),
        counted_cash=str(cash),
        pending_queued_transactions=pending_queued_transactions,
        variance_amount=str(decision.variance_amount),
        variance_percent=str(decision.variance_percent),
        status=decision.status.value,
        reason_code=decision.reason_code,
    ).model_dump()


@router.post(
    "/submit",
    summary="Submit closing harian",
    status_code=201,
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
async def submit_closing(req: SubmitClosingRequest):
    """
    Mengajukan closing harian.

    Sistem akan mengevaluasi variance dan memutuskan apakah closing
    diizinkan, diblokir, atau memerlukan acknowledgement.
    """
    global _next_report_id

    try:
        sales = Decimal(req.operational_sales)
        cash = Decimal(req.counted_cash)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Format angka tidak valid"
            ).model_dump(),
        )

    # Validate date format
    try:
        datetime.datetime.strptime(req.business_date, "%Y-%m-%d")
    except ValueError:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Format tanggal tidak valid. Gunakan YYYY-MM-DD"
            ).model_dump(),
        )

    policy = ReconciliationPolicy(
        amount_threshold=req.acknowledge_amount,
        percent_threshold=req.acknowledge_percent,
    )
    decision = evaluate_shift_closing(
        operational_sales=sales,
        counted_cash=cash,
        pending_queued_transactions=req.pending_queued_transactions,
        policy=policy,
        pending_acknowledged=req.pending_acknowledged,
    )

    # Check if closing is blocked
    if decision.status is ClosingStatus.BLOCKED:
        _audit_log.record(
            action="CLOSING_BLOCKED",
            actor_id=req.cashier_id,
            branch_code=req.branch_code,
            device_id="API",
            reference_id=f"CLOSE-{req.branch_code}-{req.business_date}",
            severity=AuditSeverity.WARNING,
            metadata={
                "reason_code": decision.reason_code,
                "variance_amount": str(decision.variance_amount),
                "variance_percent": str(decision.variance_percent),
            },
        )

        return JSONResponse(
            status_code=409,
            content=SubmitClosingResponse(
                closing_id="",
                branch_code=req.branch_code,
                business_date=req.business_date,
                status=decision.status.value,
                variance_amount=str(decision.variance_amount),
                variance_percent=str(decision.variance_percent),
                reason_code=decision.reason_code,
                message=f"Closing diblokir: variance {decision.variance_amount} ({decision.variance_percent}%) melebihi batas toleransi. "
                        f"Alert dikirim ke: {', '.join(decision.alert_roles)}",
            ).model_dump(),
        )

    # Check if acknowledgement required
    if decision.status is ClosingStatus.ACK_REQUIRED and not req.pending_acknowledged:
        return JSONResponse(
            status_code=409,
            content=SubmitClosingResponse(
                closing_id="",
                branch_code=req.branch_code,
                business_date=req.business_date,
                status=decision.status.value,
                variance_amount=str(decision.variance_amount),
                variance_percent=str(decision.variance_percent),
                reason_code=decision.reason_code,
                message=f"Closing memerlukan acknowledgement dari: {', '.join(decision.required_acknowledgement_roles)}. "
                        f"Set pending_acknowledged=true setelah mendapat persetujuan.",
            ).model_dump(),
        )

    # Closing allowed
    report_id = f"RPT-{_next_report_id:06d}"
    _next_report_id += 1

    now = datetime.datetime.now()
    report = {
        "report_id": report_id,
        "branch_code": req.branch_code,
        "business_date": req.business_date,
        "operational_sales": str(sales),
        "counted_cash": str(cash),
        "variance_amount": str(decision.variance_amount),
        "variance_percent": str(decision.variance_percent),
        "status": decision.status.value,
        "submitted_by": req.cashier_id,
        "submitted_at": now.isoformat(),
        "reason_code": decision.reason_code,
    }
    _reports[report_id] = report

    _audit_log.record(
        action="CLOSING_SUBMITTED",
        actor_id=req.cashier_id,
        branch_code=req.branch_code,
        device_id="API",
        reference_id=report_id,
        severity=AuditSeverity.INFO,
        metadata={
            "business_date": req.business_date,
            "operational_sales": str(sales),
            "counted_cash": str(cash),
            "variance_amount": str(decision.variance_amount),
            "status": decision.status.value,
        },
    )

    return SubmitClosingResponse(
        closing_id=report_id,
        branch_code=req.branch_code,
        business_date=req.business_date,
        status=decision.status.value,
        variance_amount=str(decision.variance_amount),
        variance_percent=str(decision.variance_percent),
        reason_code=decision.reason_code,
        message=f"Closing berhasil disubmit. Report ID: {report_id}",
    ).model_dump()


@router.get(
    "/report/{report_id}",
    summary="Ambil laporan closing",
    responses={404: {"model": ErrorResponse}},
)
async def get_closing_report(report_id: str):
    """Mengambil laporan closing berdasarkan ID."""
    report = _reports.get(report_id)
    if not report:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Laporan closing '{report_id}' tidak ditemukan"
            ).model_dump(),
        )

    return ClosingReportResponse(
        report_id=report["report_id"],
        branch_code=report["branch_code"],
        business_date=report["business_date"],
        operational_sales=report["operational_sales"],
        counted_cash=report["counted_cash"],
        variance_amount=report["variance_amount"],
        variance_percent=report["variance_percent"],
        status=report["status"],
        submitted_by=report["submitted_by"],
        submitted_at=report["submitted_at"],
        reason_code=report.get("reason_code"),
    ).model_dump()
