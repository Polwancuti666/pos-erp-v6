"""Pydantic request/response models for all POS-ERP API endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Checkout / Transaction Models ────────────────────────────────────────────


class CreateTransactionRequest(BaseModel):
    branch_code: str = Field("", description="Kode cabang (e.g. BSD, HQ)")
    branch_id: str = Field("", description="Branch UUID — alternative to branch_code")
    device_id: str = Field(..., description="ID perangkat POS")
    cashier_id: str = Field(..., description="ID kasir")
    shift_id: Optional[str] = Field(None, description="ID shift cashier")


class TransactionLineResponse(BaseModel):
    line_id: str
    service_id: str
    staff_id: str
    price: str


class TransactionResponse(BaseModel):
    transaction_id: str
    branch_code: str
    device_id: str
    cashier_id: str
    status: str
    lines: list[TransactionLineResponse]
    total_price: str
    payment_method: str | None = None
    staff_lock_id: str | None = None
    payment_intent_id: str | None = None


class AddItemRequest(BaseModel):
    service_id: str = Field(..., description="ID layanan/treatment")
    staff_id: str = Field(..., description="ID staff yang ditugaskan")


class RemoveItemRequest(BaseModel):
    line_id: str = Field(..., description="ID baris treatment")


class SelectStaffRequest(BaseModel):
    staff_id: str = Field(..., description="ID staff yang dipilih")
    actor_id: str = Field("system", description="ID pelaku aksi")


class SelectPaymentMethodRequest(BaseModel):
    payment_method: str = Field(..., description="Metode pembayaran: cash, qris, bank_transfer")


class SubmitCheckoutRequest(BaseModel):
    pass


class ConfirmCashRequest(BaseModel):
    amount_received: str = Field(..., description="Jumlah uang diterima dari pelanggan")


class StaffReplacementRequest(BaseModel):
    line_id: str = Field(..., description="ID baris treatment")
    confirmed: bool = Field(True, description="Konfirmasi penggantian staff")


class QRISStatusResponse(BaseModel):
    payment_intent_id: str
    status: str
    message: str


# ── Exception Models ─────────────────────────────────────────────────────────


class ExceptionItemResponse(BaseModel):
    exception_id: str
    exception_type: str
    reference_id: str
    created_at: str
    owner_roles: list[str]
    sla_hours: int
    status: str
    resolved_by: str | None = None
    resolution: str | None = None


class ResolveExceptionRequest(BaseModel):
    resolved_by: str = Field(..., description="ID penyelesai")
    resolution: str = Field(..., description="Catatan penyelesaian")


class EscalateExceptionRequest(BaseModel):
    escalated_to: str = Field(..., description="Role tujuan eskalasi")
    reason: str = Field("", description="Alasan eskalasi")


# ── Dashboard Models ─────────────────────────────────────────────────────────


class BranchSnapshotResponse(BaseModel):
    branch_code: str
    operational_sales: str
    paid_pending_posting: str
    posted_revenue: str
    unreconciled_variance: str
    pending_sync_count: int
    failed_retry_count: int
    last_sync_at: str
    is_stale: bool
    queue_alert: bool
    sla_alert: bool


class DashboardSummaryResponse(BaseModel):
    branches: list[BranchSnapshotResponse]
    total_operational_sales: str
    total_posted_revenue: str
    total_pending_sync_count: int


class AlertItem(BaseModel):
    alert_type: str
    severity: str
    message: str
    branch_code: str


class DashboardAlertsResponse(BaseModel):
    alerts: list[AlertItem]


# ── COA Mapping Models ───────────────────────────────────────────────────────


class COAMappingItem(BaseModel):
    mapping_id: str
    mapping_type: str
    source_key: str
    account_code: str
    account_name: str | None = None


class CreateCOAMappingRequest(BaseModel):
    mapping_type: str = Field(..., description="Tipe mapping: service_revenue, cash_account, dll")
    source_key: str = Field(..., description="Kunci sumber (ID service, tipe akun, dll)")
    account_code: str = Field(..., description="Kode akun COA")
    account_name: str = Field("", description="Nama akun COA")


class UpdateCOAMappingRequest(BaseModel):
    account_code: str = Field(..., description="Kode akun COA baru")
    account_name: str = Field("", description="Nama akun COA baru")


class BulkValidateRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., description="Baris CSV untuk validasi")


class BulkValidateRowResult(BaseModel):
    row_index: int
    valid: bool
    errors: list[str] = []
    data: dict[str, Any] = {}


class BulkValidateResponse(BaseModel):
    total_rows: int
    valid_count: int
    invalid_count: int
    results: list[BulkValidateRowResult]


class BulkApplyRequest(BaseModel):
    rows: list[dict[str, Any]] = Field(..., description="Baris data yang sudah tervalidasi")


class BulkApplyResult(BaseModel):
    row_index: int
    success: bool
    mapping_id: str | None = None
    error: str | None = None


class BulkApplyResponse(BaseModel):
    total_rows: int
    success_count: int
    failure_count: int
    results: list[BulkApplyResult]


class COAAccountItem(BaseModel):
    account_code: str
    account_name: str
    account_type: str


class COAAccountSearchResponse(BaseModel):
    accounts: list[COAAccountItem]


class MappingStatusItem(BaseModel):
    mapping_type: str
    total_mappings: int
    unmapped_count: int


class MappingStatusSummaryResponse(BaseModel):
    summary: list[MappingStatusItem]


# ── Daily Closing Models ─────────────────────────────────────────────────────


class ClosingSummaryResponse(BaseModel):
    branch_code: str
    business_date: str
    operational_sales: str
    counted_cash: str
    pending_queued_transactions: int
    variance_amount: str
    variance_percent: str
    status: str
    reason_code: str | None = None


class SubmitClosingRequest(BaseModel):
    branch_code: str = Field(..., description="Kode cabang")
    business_date: str = Field(..., description="Tanggal bisnis (YYYY-MM-DD)")
    counted_cash: str = Field(..., description="Jumlah kas fisik yang dihitung")
    operational_sales: str = Field(..., description="Total penjualan operasional")
    pending_queued_transactions: int = Field(0, description="Jumlah transaksi tertunda")
    pending_acknowledged: bool = Field(False, description="Apakah transaksi tertunda sudah di-ack")
    cashier_id: str = Field(..., description="ID kasir yang melakukan closing")
    acknowledge_amount: Decimal = Field(Decimal("100000.00"), description="Batas toleransi nominal")
    acknowledge_percent: Decimal = Field(Decimal("5.00"), description="Batas toleransi persen")


class SubmitClosingResponse(BaseModel):
    closing_id: str
    branch_code: str
    business_date: str
    status: str
    variance_amount: str
    variance_percent: str
    reason_code: str | None = None
    message: str


class ClosingReportResponse(BaseModel):
    report_id: str
    branch_code: str
    business_date: str
    operational_sales: str
    counted_cash: str
    variance_amount: str
    variance_percent: str
    status: str
    submitted_by: str
    submitted_at: str
    reason_code: str | None = None


# ── Generic Error Model ──────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: str | None = None
