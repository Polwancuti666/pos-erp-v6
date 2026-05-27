"""COA (Chart of Accounts) Mapping API router.

Manages chart of accounts mappings: CRUD operations, bulk import/validation,
account search, and unmapped status summary.
"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from pos_erp.accounting import COAMapping
from pos_erp.audit_log import AuditLog, AuditSeverity

from pos_erp.routers.models import (
    BulkApplyRequest,
    BulkApplyResponse,
    BulkApplyResult,
    BulkValidateRequest,
    BulkValidateResponse,
    BulkValidateRowResult,
    COAAccountItem,
    COAAccountSearchResponse,
    COAMappingItem,
    CreateCOAMappingRequest,
    ErrorResponse,
    MappingStatusItem,
    MappingStatusSummaryResponse,
    UpdateCOAMappingRequest,
)

router = APIRouter(prefix="/api/coa", tags=["COA Mapping"])

# ── In-memory stores ─────────────────────────────────────────────────────────

_mappings: dict[str, dict[str, Any]] = {}
_next_id = 1
_audit_log = AuditLog()

# Mock COA accounts for search
_COA_ACCOUNTS: list[dict[str, str]] = [
    {"account_code": "1100", "account_name": "Kas", "account_type": "ASSET"},
    {"account_code": "1101", "account_name": "Kas Kecil", "account_type": "ASSET"},
    {"account_code": "1110", "account_name": "Bank BCA", "account_type": "ASSET"},
    {"account_code": "1111", "account_name": "Bank Mandiri", "account_type": "ASSET"},
    {"account_code": "1120", "account_name": "Piutang Usaha", "account_type": "ASSET"},
    {"account_code": "4100", "account_name": "Pendapatan Jasa", "account_type": "REVENUE"},
    {"account_code": "4101", "account_name": "Pendapatan Treatment Wajah", "account_type": "REVENUE"},
    {"account_code": "4102", "account_name": "Pendapatan Treatment Rambut", "account_type": "REVENUE"},
    {"account_code": "4103", "account_name": "Pendapatan Treatment Tubuh", "account_type": "REVENUE"},
    {"account_code": "4104", "account_name": "Pendapatan Treatment Kuku", "account_type": "REVENUE"},
    {"account_code": "4105", "account_name": "Pendapatan Lain-lain", "account_type": "REVENUE"},
    {"account_code": "5100", "account_name": "Biaya Gaji", "account_type": "EXPENSE"},
    {"account_code": "5101", "account_name": "Biaya Sewa", "account_type": "EXPENSE"},
    {"account_code": "5102", "account_name": "Biaya Utilitas", "account_type": "EXPENSE"},
    {"account_code": "2100", "account_name": "Utang Usaha", "account_type": "LIABILITY"},
]

# Mapping types and their source key descriptions
_MAPPING_TYPES = {
    "service_revenue": "Pendapatan jasa per layanan",
    "cash_account": "Akun kas per cabang",
    "bank_account": "Akun bank per cabang",
    "staff_expense": "Biaya gaji per staff",
}


def _seed_demo_data() -> None:
    global _next_id
    seeds = [
        ("service_revenue", "SVC-FACIAL", "4101", "Pendapatan Treatment Wajah"),
        ("service_revenue", "SVC-MASSAGE", "4103", "Pendapatan Treatment Tubuh"),
        ("service_revenue", "SVC-HAIRSPA", "4102", "Pendapatan Treatment Rambut"),
        ("cash_account", "HQ", "1100", "Kas"),
    ]
    for mtype, skey, code, name in seeds:
        mid = f"MAP-{_next_id:06d}"
        _mappings[mid] = {
            "mapping_id": mid,
            "mapping_type": mtype,
            "source_key": skey,
            "account_code": code,
            "account_name": name,
            "created_at": datetime.datetime.now().isoformat(),
        }
        _next_id += 1


_seed_demo_data()


def _serialize_mapping(mapping: dict[str, Any]) -> dict:
    return COAMappingItem(
        mapping_id=mapping["mapping_id"],
        mapping_type=mapping["mapping_type"],
        source_key=mapping["source_key"],
        account_code=mapping["account_code"],
        account_name=mapping.get("account_name"),
    ).model_dump()


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/mappings",
    summary="Daftar mapping COA",
    responses={200: {"description": "Daftar mapping COA"}},
)
async def list_mappings(
    mapping_type: str | None = Query(None, description="Filter berdasarkan tipe mapping"),
):
    """
    Mengambil daftar mapping COA.

    - **mapping_type**: Filter berdasarkan tipe (service_revenue, cash_account, dll)
    """
    items = list(_mappings.values())

    if mapping_type:
        items = [m for m in items if m["mapping_type"] == mapping_type]

    return {
        "total": len(items),
        "items": [_serialize_mapping(m) for m in items],
    }


@router.post(
    "/mappings",
    summary="Buat mapping COA baru",
    status_code=201,
    responses={400: {"model": ErrorResponse}},
)
async def create_mapping(req: CreateCOAMappingRequest):
    """Membuat mapping COA baru."""
    global _next_id

    # Validate mapping type
    if req.mapping_type not in _MAPPING_TYPES:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=f"Tipe mapping '{req.mapping_type}' tidak valid",
                detail=f"Tipe yang valid: {', '.join(_MAPPING_TYPES.keys())}",
            ).model_dump(),
        )

    # Validate account code exists
    valid_codes = {a["account_code"] for a in _COA_ACCOUNTS}
    if req.account_code not in valid_codes:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=f"Kode akun '{req.account_code}' tidak ditemukan di COA",
            ).model_dump(),
        )

    # Check for duplicate mapping
    for existing in _mappings.values():
        if (existing["mapping_type"] == req.mapping_type
                and existing["source_key"] == req.source_key):
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    message=f"Mapping untuk tipe '{req.mapping_type}' dan sumber '{req.source_key}' sudah ada",
                ).model_dump(),
            )

    mid = f"MAP-{_next_id:06d}"
    _next_id += 1

    mapping = {
        "mapping_id": mid,
        "mapping_type": req.mapping_type,
        "source_key": req.source_key,
        "account_code": req.account_code,
        "account_name": req.account_name or _get_account_name(req.account_code),
        "created_at": datetime.datetime.now().isoformat(),
    }
    _mappings[mid] = mapping

    _audit_log.record(
        action="COA_MAPPING_CREATED",
        actor_id="system",
        branch_code="SYSTEM",
        device_id="API",
        reference_id=mid,
        severity=AuditSeverity.INFO,
        metadata={"mapping_type": req.mapping_type, "source_key": req.source_key, "account_code": req.account_code},
    )

    return _serialize_mapping(mapping)


@router.put(
    "/mappings/{mapping_id}",
    summary="Update mapping COA",
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def update_mapping(mapping_id: str, req: UpdateCOAMappingRequest):
    """Memperbarui mapping COA yang sudah ada."""
    mapping = _mappings.get(mapping_id)
    if not mapping:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Mapping '{mapping_id}' tidak ditemukan"
            ).model_dump(),
        )

    # Validate account code exists
    valid_codes = {a["account_code"] for a in _COA_ACCOUNTS}
    if req.account_code not in valid_codes:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                message=f"Kode akun '{req.account_code}' tidak ditemukan di COA",
            ).model_dump(),
        )

    old_code = mapping["account_code"]
    mapping["account_code"] = req.account_code
    mapping["account_name"] = req.account_name or _get_account_name(req.account_code)

    _audit_log.record(
        action="COA_MAPPING_UPDATED",
        actor_id="system",
        branch_code="SYSTEM",
        device_id="API",
        reference_id=mapping_id,
        severity=AuditSeverity.INFO,
        metadata={"old_account_code": old_code, "new_account_code": req.account_code},
    )

    return _serialize_mapping(mapping)


@router.delete(
    "/mappings/{mapping_id}",
    summary="Hapus mapping COA",
    responses={404: {"model": ErrorResponse}},
)
async def delete_mapping(mapping_id: str):
    """Menghapus mapping COA."""
    mapping = _mappings.get(mapping_id)
    if not mapping:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                message=f"Mapping '{mapping_id}' tidak ditemukan"
            ).model_dump(),
        )

    del _mappings[mapping_id]

    _audit_log.record(
        action="COA_MAPPING_DELETED",
        actor_id="system",
        branch_code="SYSTEM",
        device_id="API",
        reference_id=mapping_id,
        severity=AuditSeverity.WARNING,
        metadata={
            "mapping_type": mapping["mapping_type"],
            "source_key": mapping["source_key"],
            "account_code": mapping["account_code"],
        },
    )

    return {
        "success": True,
        "message": f"Mapping '{mapping_id}' berhasil dihapus",
    }


@router.post(
    "/mappings/bulk-validate",
    summary="Validasi baris CSV bulk",
    responses={200: {"model": BulkValidateResponse}},
)
async def bulk_validate(req: BulkValidateRequest):
    """
    Memvalidasi baris-baris CSV sebelum import bulk.

    Setiap baris harus memiliki: mapping_type, source_key, account_code.
    """
    valid_codes = {a["account_code"] for a in _COA_ACCOUNTS}
    results: list[BulkValidateRowResult] = []
    valid_count = 0
    invalid_count = 0

    for idx, row in enumerate(req.rows):
        errors: list[str] = []

        mapping_type = row.get("mapping_type", "")
        source_key = row.get("source_key", "")
        account_code = row.get("account_code", "")

        if not mapping_type:
            errors.append("mapping_type wajib diisi")
        elif mapping_type not in _MAPPING_TYPES:
            errors.append(f"Tipe mapping '{mapping_type}' tidak valid")

        if not source_key:
            errors.append("source_key wajib diisi")

        if not account_code:
            errors.append("account_code wajib diisi")
        elif account_code not in valid_codes:
            errors.append(f"Kode akun '{account_code}' tidak ditemukan")

        is_valid = len(errors) == 0
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

        results.append(BulkValidateRowResult(
            row_index=idx,
            valid=is_valid,
            errors=errors,
            data=row,
        ))

    return BulkValidateResponse(
        total_rows=len(req.rows),
        valid_count=valid_count,
        invalid_count=invalid_count,
        results=results,
    ).model_dump()


@router.post(
    "/mappings/bulk-apply",
    summary="Terapkan import bulk",
    responses={200: {"model": BulkApplyResponse}, 400: {"model": ErrorResponse}},
)
async def bulk_apply(req: BulkApplyRequest):
    """
    Menerapkan mapping COA secara bulk dari data yang sudah tervalidasi.

    Setiap baris harus memiliki: mapping_type, source_key, account_code.
    """
    global _next_id

    valid_codes = {a["account_code"] for a in _COA_ACCOUNTS}
    results: list[BulkApplyResult] = []
    success_count = 0
    failure_count = 0

    for idx, row in enumerate(req.rows):
        mapping_type = row.get("mapping_type", "")
        source_key = row.get("source_key", "")
        account_code = row.get("account_code", "")
        account_name = row.get("account_name", "")

        # Validate
        if not mapping_type or mapping_type not in _MAPPING_TYPES:
            results.append(BulkApplyResult(
                row_index=idx, success=False, error="Tipe mapping tidak valid"
            ))
            failure_count += 1
            continue

        if not source_key:
            results.append(BulkApplyResult(
                row_index=idx, success=False, error="source_key wajib diisi"
            ))
            failure_count += 1
            continue

        if not account_code or account_code not in valid_codes:
            results.append(BulkApplyResult(
                row_index=idx, success=False, error="Kode akun tidak valid"
            ))
            failure_count += 1
            continue

        # Check duplicate
        duplicate = False
        for existing in _mappings.values():
            if (existing["mapping_type"] == mapping_type
                    and existing["source_key"] == source_key):
                duplicate = True
                break

        if duplicate:
            results.append(BulkApplyResult(
                row_index=idx, success=False, error="Mapping sudah ada"
            ))
            failure_count += 1
            continue

        # Create
        mid = f"MAP-{_next_id:06d}"
        _next_id += 1
        _mappings[mid] = {
            "mapping_id": mid,
            "mapping_type": mapping_type,
            "source_key": source_key,
            "account_code": account_code,
            "account_name": account_name or _get_account_name(account_code),
            "created_at": datetime.datetime.now().isoformat(),
        }
        results.append(BulkApplyResult(
            row_index=idx, success=True, mapping_id=mid
        ))
        success_count += 1

    _audit_log.record(
        action="COA_BULK_IMPORT",
        actor_id="system",
        branch_code="SYSTEM",
        device_id="API",
        reference_id=f"BULK-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        severity=AuditSeverity.INFO,
        metadata={"total": len(req.rows), "success": success_count, "failure": failure_count},
    )

    return BulkApplyResponse(
        total_rows=len(req.rows),
        success_count=success_count,
        failure_count=failure_count,
        results=results,
    ).model_dump()


@router.get(
    "/accounts",
    summary="Cari akun COA",
    responses={200: {"model": COAAccountSearchResponse}},
)
async def search_accounts(
    q: str = Query("", description="Kata kunci pencarian (kode atau nama akun)"),
    account_type: str | None = Query(None, description="Filter tipe akun: ASSET, LIABILITY, REVENUE, EXPENSE"),
):
    """
    Mencari akun COA berdasarkan kata kunci dan/atau tipe.
    """
    results = list(_COA_ACCOUNTS)

    if q:
        q_lower = q.lower()
        results = [
            a for a in results
            if q_lower in a["account_code"].lower() or q_lower in a["account_name"].lower()
        ]

    if account_type:
        results = [a for a in results if a["account_type"] == account_type.upper()]

    return COAAccountSearchResponse(
        accounts=[
            COAAccountItem(
                account_code=a["account_code"],
                account_name=a["account_name"],
                account_type=a["account_type"],
            )
            for a in results
        ]
    ).model_dump()


@router.get(
    "/mappings/status-summary",
    summary="Ringkasan status mapping (unmapped per tipe)",
    responses={200: {"model": MappingStatusSummaryResponse}},
)
async def mapping_status_summary():
    """
    Menghitung jumlah mapping dan unmapped per tipe.

    Berguna untuk menampilkan di dashboard berapa banyak
    service/akun yang belum memiliki mapping COA.
    """
    # Count mapped per type
    mapped_counts: dict[str, int] = {}
    for mapping in _mappings.values():
        mt = mapping["mapping_type"]
        mapped_counts[mt] = mapped_counts.get(mt, 0) + 1

    summary = []
    for mtype, description in _MAPPING_TYPES.items():
        total = mapped_counts.get(mtype, 0)
        # For demo: assume each type needs a certain number of mappings
        expected = {"service_revenue": 5, "cash_account": 3, "bank_account": 3, "staff_expense": 5}
        unmapped = max(0, expected.get(mtype, 0) - total)
        summary.append(MappingStatusItem(
            mapping_type=mtype,
            total_mappings=total,
            unmapped_count=unmapped,
        ))

    return MappingStatusSummaryResponse(summary=summary).model_dump()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_account_name(account_code: str) -> str:
    for a in _COA_ACCOUNTS:
        if a["account_code"] == account_code:
            return a["account_name"]
    return ""
