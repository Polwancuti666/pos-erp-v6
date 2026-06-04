"""Unified domain models for Beauty & Shine ERP.

Consolidates all enums, value objects, and shared types.
Based on existing domain-driven patterns from checkout.py, treatment.py, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional


# ── Document Types ────────────────────────────────────────────────

class DocumentKind(str, Enum):
    """Document types per BPMN v3 specification."""
    BOOK = "BOOK"           # Booking
    POS = "POS"             # POS Transaction
    TRM = "TRM"             # Treatment Record
    STK = "STK"             # Stock Movement
    WIP = "WIP"             # Work in Progress
    AP = "AP"               # Accounts Payable
    BP = "BP"               # Bank Payment
    JE = "JE"               # Journal Entry
    FA = "FA"               # Fixed Asset
    EOP = "EOP"             # End of Period
    CLO = "CLO"             # Daily Closing
    BRC = "BRC"             # Bank Reconciliation
    INV = "INV"             # Inventory
    SO = "SO"               # Stock Opname


# ── Transaction Status ────────────────────────────────────────────

class TransactionStatus(str, Enum):
    """POS transaction lifecycle."""
    OPEN = "open"
    BOOKED = "booked"
    IN_PROGRESS = "in_progress"
    PAYMENT_PENDING = "payment_pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# ── Payment ───────────────────────────────────────────────────────

class PaymentMethod(str, Enum):
    """Supported payment methods."""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    QRIS = "qris"
    E_WALLET = "e_wallet"
    CARD = "card"


class PaymentStatus(str, Enum):
    """Payment verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class PaymentIntent:
    """Payment intent for online verification."""
    transaction_id: str
    method: PaymentMethod
    amount: Decimal
    expected_reference: str
    online: bool
    status: PaymentStatus = PaymentStatus.PENDING


@dataclass(frozen=True)
class VerificationResult:
    """Result of payment verification."""
    transaction_id: str
    method: PaymentMethod
    amount: Decimal
    status: PaymentStatus
    reason_code: str
    verified_reference: Optional[str] = None


# ── Inventory ─────────────────────────────────────────────────────

class MovementType(str, Enum):
    """Stock movement types."""
    IN = "in"
    OUT = "out"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"


class MovementReason(str, Enum):
    """Reasons for stock movement."""
    PURCHASE = "purchase"
    SALE = "sale"
    SERVICE_CONSUMPTION = "service_consumption"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    DAMAGED_STOCK = "damaged_stock"
    EXPIRED = "expired"
    RETURN = "return"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


@dataclass(frozen=True)
class InventoryPolicy:
    """Inventory control policies."""
    allow_negative: bool = False
    require_batch_tracking: bool = False
    require_expiry_tracking: bool = False
    low_stock_threshold: Decimal = Decimal("10")


class NegativeStockBlocked(Exception):
    """Raised when stock would go negative and policy blocks it."""
    def __init__(self, *, item_id: str, available: Decimal, required: Decimal):
        super().__init__(f"Insufficient stock for {item_id}: available {available}, required {required}")
        self.item_id = item_id
        self.available = available
        self.required = required


# ── Accounting ────────────────────────────────────────────────────

class AccountType(str, Enum):
    """Chart of Account types."""
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class JournalStatus(str, Enum):
    """Journal entry status."""
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


@dataclass(frozen=True)
class COAMapping:
    """Chart of Account mapping for auto-journal."""
    service_revenue: Optional[str] = None
    product_revenue: Optional[str] = None
    cash_account: Optional[str] = None
    bank_account: Optional[str] = None
    cogs_account: Optional[str] = None
    inventory_account: Optional[str] = None
    tax_account: Optional[str] = None
    ap_account: Optional[str] = None


@dataclass(frozen=True)
class JournalLine:
    """Single line in a journal entry."""
    account_code: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    description: Optional[str] = None


@dataclass(frozen=True)
class Journal:
    """Complete journal entry."""
    journal_number: str
    branch_code: str
    transaction_reference: str
    lines: tuple[JournalLine, ...]
    status: JournalStatus = JournalStatus.DRAFT

    @property
    def debit_total(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0.00"))

    @property
    def credit_total(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0.00"))

    @property
    def is_balanced(self) -> bool:
        return self.debit_total == self.credit_total


class AccountingException(Exception):
    """Raised when accounting validation fails."""
    def __init__(self, *, reason_code: str, transaction_reference: str, missing_fields: list[str]):
        super().__init__(f"{reason_code}: missing {', '.join(missing_fields)}")
        self.reason_code = reason_code
        self.transaction_reference = transaction_reference
        self.missing_fields = missing_fields


# ── Treatment ─────────────────────────────────────────────────────

class TreatmentStatus(str, Enum):
    """Treatment session status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class StaffTier(str, Enum):
    """Staff pricing tiers."""
    SENIOR = "senior"
    JUNIOR = "junior"
    TRAINEE = "trainee"


@dataclass(frozen=True)
class TreatmentLine:
    """Single treatment in a cart."""
    line_id: str
    service_id: str
    staff_id: str
    price: Decimal


@dataclass(frozen=True)
class StaffSuggestion:
    """Suggested staff for treatment."""
    status: str
    suggested_staff_id: Optional[str] = None
    requires_confirmation: bool = False
    options: tuple[str, ...] = ()


# ── Period Lock ───────────────────────────────────────────────────

class PeriodLockDecision(str, Enum):
    """Decisions for period-locked actions."""
    ALLOWED = "allowed"
    ALLOWED_CONTROLLED_ADJUSTMENT = "allowed_controlled_adjustment"
    BLOCKED_PERIOD_LOCKED = "blocked_period_locked"
    BLOCKED_ROLE_NOT_AUTHORIZED = "blocked_role_not_authorized"
    BLOCKED_REASON_REQUIRED = "blocked_reason_required"


@dataclass(frozen=True)
class PeriodLock:
    """Financial period lock state."""
    is_locked: bool
    period_id: Optional[str] = None


# ── Sync & Offline ───────────────────────────────────────────────

class SyncStatus(str, Enum):
    """Sync queue status."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"


@dataclass(frozen=True)
class ConnectivityNotice:
    """Connectivity recovery notice."""
    recovered: bool
    queued_count: int
    requires_approval: bool


@dataclass(frozen=True)
class DeviceBinding:
    """POS device binding to branch."""
    device_id: str
    branch_code: str
    active: bool

    def allows(self, *, branch_code: str, device_id: str) -> bool:
        return self.active and self.branch_code == branch_code and self.device_id == device_id


# ── Audit ─────────────────────────────────────────────────────────

class AuditSeverity(str, Enum):
    """Audit log severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    """Audit actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    POST = "post"
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"
    REFUND = "refund"
    LOCK = "lock"
    UNLOCK = "unlock"


# ── Helper Functions ──────────────────────────────────────────────

def money(value: Decimal) -> Decimal:
    """Round to 2 decimal places."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_tax(subtotal: Decimal, tax_rate: Decimal = Decimal("0.11")) -> Decimal:
    """Calculate PPN (11%)."""
    return money(subtotal * tax_rate)


def calculate_discount(subtotal: Decimal, discount_type: str, discount_value: Decimal) -> Decimal:
    """Calculate discount amount."""
    if discount_type == "percentage":
        return money(subtotal * discount_value / 100)
    return money(discount_value)
