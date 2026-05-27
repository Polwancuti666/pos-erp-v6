"""Exception Queue API router.

Manages system exceptions: list, view details, resolve, and escalate.
"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from pos_erp.audit_log import AuditLog, AuditSeverity
from pos_erp.exception_queue import (
    ExceptionQueue,
    ExceptionStatus,
    ExceptionType,
)

from pos_erp.routers.models import (
    ErrorResponse,
    EscalateExceptionRequest,
    ExceptionItemResponse,
    ResolveExceptionRequest,
)

router = APIRouter(prefix="/api", tags=["Exceptions"])

# ── In-memory stores ─────────────────────────────────────────────────────────

_queue = ExceptionQueue()
_audit_log = AuditLog()

# Seed some demo exceptions for development
def _seed_demo_data() -> None:
    now = datetime.datetime.now()
    _queue.add(
        ExceptionType.SYNC_FAILURE,
        reference_id="TXN-HQ-DEV-001",
        created_at=(now - datetime.timedelta(hours=1)).isoformat(),
    )
    _queue.add(
        ExceptionType.UNMAPPED_COA,
        reference_id="TXN-HQ-DEV-002",
        created_at=(now - datetime.timedelta(hours=3)).isoformat(),
    )
    _queue.add(
        ExceptionType.PAYMENT_REVIEW_REQUIRED,
        reference_id="TXN-HQ-DEV-003",
        created_at=(now - datetime.timedelta(hours=12)).isoformat(),
    )


_seed_demo_data()


def _serialize_exception(item: Any) -> dict:
    return ExceptionItemResponse(
        exception_id=item.exception_id,
        exception_type=item.exception_type.value,
        reference_id=item.reference_id,
        created_at=item.created_at,
        owner_roles=list(item.owner_roles),
        sla_hours=item.sla_hours,
        status=item.status.value,
        resolved_by=item.resolved_by,
        resolution=item.resolution,
    ).model_dump()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/exceptions",
    summary="Daftar exception",
    responses={200: {"description": "Daftar exception dengan filter opsional"}},
)
async def list_exceptions(
    exception_type: str | None = Query(None, description="Filter berdasarkan tipe exception"),
    status: str | None = Query(None, description="Filter berdasarkan status: OPEN, RESOLVED"),
    priority: str | None = Query(None, description="Filter: overdue (melampaui SLA)"),
):
    """
    Mengambil daftar exception dengan filter opsional.

    - **exception_type**: Filter berdasarkan tipe (SYNC_FAILURE, UNMAPPED_COA, dll)
    - **status**: Filter berdasarkan status (OPEN, RESOLVED)
    - **priority**: Filter 'overdue' untuk exception yang melampaui SLA
    """
    now = datetime.datetime.now().isoformat()
    items = list(_queue._items.values())

    # Filter by type
    if exception_type:
        try:
            exc_type = ExceptionType(exception_type)
            items = [i for i in items if i.exception_type is exc_type]
        except ValueError:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    message=f"Tipe exception '{exception_type}' tidak valid",
                    detail=f"Tipe yang valid: {', '.join(t.value for t in ExceptionType)}",
                ).model_dump(),
            )

    # Filter by status
    if status:
        try:
            exc_status = ExceptionStatus(status)
            items = [i for i in items if i.status is exc_status]
        except ValueError:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    message=f"Status '{status}' tidak valid",
                    detail=f"Status yang valid: OPEN, RESOLVED",
                ).model_dump(),
            )

    # Filter by priority (overdue)
    if priority == "overdue":
        overdue_ids = {i.exception_id for i in _queue.overdue_items(now=now)}
        items = [i for i in items if i.exception_id in overdue_ids]

    return {
        "total": len(items),
        "items": [_serialize_exception(i) for i in items],
    }


@router.get(
    "/exceptions/{exception_id}",
    summary="Detail exception",
    responses={404: {"model": ErrorResponse}},
)
async def get_exception(exception_id: str):
    """Mengambil detail exception berdasarkan ID."""
    try:
        item = _queue.get(exception_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Exception '{exception_id}' tidak ditemukan"
            ).model_dump(),
        )

    now = datetime.datetime.now()
    created = datetime.datetime.fromisoformat(item.created_at)
    deadline = created + datetime.timedelta(hours=item.sla_hours)
    is_overdue = now > deadline and item.status is ExceptionStatus.OPEN

    result = _serialize_exception(item)
    result["deadline"] = deadline.isoformat()
    result["is_overdue"] = is_overdue
    return result


@router.post(
    "/exceptions/{exception_id}/resolve",
    summary="Selesaikan exception",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def resolve_exception(exception_id: str, req: ResolveExceptionRequest):
    """Menandai exception sebagai selesai."""
    try:
        _queue.get(exception_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Exception '{exception_id}' tidak ditemukan"
            ).model_dump(),
        )

    try:
        item = _queue.resolve(
            exception_id,
            resolved_by=req.resolved_by,
            resolution=req.resolution,
        )
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Exception '{exception_id}' tidak ditemukan"
            ).model_dump(),
        )

    _audit_log.record(
        action="EXCEPTION_RESOLVED",
        actor_id=req.resolved_by,
        branch_code="SYSTEM",
        device_id="API",
        reference_id=exception_id,
        severity=AuditSeverity.INFO,
        metadata={"resolution": req.resolution},
    )

    return {
        "success": True,
        "message": f"Exception '{exception_id}' berhasil diselesaikan",
        "exception": _serialize_exception(item),
    }


@router.post(
    "/exceptions/{exception_id}/escalate",
    summary="Eskalasi exception",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def escalate_exception(exception_id: str, req: EscalateExceptionRequest):
    """Mengeskalasi exception ke role yang lebih tinggi."""
    try:
        item = _queue.get(exception_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Exception '{exception_id}' tidak ditemukan"
            ).model_dump(),
        )

    if item.status is ExceptionStatus.RESOLVED:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message="Tidak dapat mengeskalasi exception yang sudah diselesaikan"
            ).model_dump(),
        )

    _audit_log.record(
        action="EXCEPTION_ESCALATED",
        actor_id="system",
        branch_code="SYSTEM",
        device_id="API",
        reference_id=exception_id,
        severity=AuditSeverity.WARNING,
        metadata={
            "escalated_to": req.escalated_to,
            "reason": req.reason,
            "original_owner_roles": list(item.owner_roles),
        },
    )

    return {
        "success": True,
        "message": f"Exception '{exception_id}' berhasil dieskalasi ke {req.escalated_to}",
        "exception": _serialize_exception(item),
        "escalated_to": req.escalated_to,
        "reason": req.reason,
    }
