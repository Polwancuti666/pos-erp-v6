// ═══════════════════════════════════════════════════════════
// POS-ERP V6 — TypeScript Type Definitions
// ═══════════════════════════════════════════════════════════

// ── Transaction States (PRD Section 10) ──────────────────────
export type TransactionState =
  | 'DRAFT'
  | 'RESERVED'
  | 'VALIDATED'
  | 'PAYMENT_PENDING'
  | 'PAID'
  | 'EXPIRED'
  | 'CANCELLED'
  | 'VOIDED';

export const STATE_LABELS: Record<TransactionState, string> = {
  DRAFT: 'Sedang Dibuat',
  RESERVED: 'Staff Terkunci',
  VALIDATED: 'Siap Bayar',
  PAYMENT_PENDING: 'Menunggu Pembayaran',
  PAID: 'Lunas',
  EXPIRED: 'Waktu Habis — Mulai Ulang',
  CANCELLED: 'Dibatalkan',
  VOIDED: 'Dibatalkan Setelah Bayar',
};

// ── Payment ──────────────────────────────────────────────────
export type PaymentMethod = 'CASH' | 'QRIS' | 'BANK_TRANSFER';
export type PaymentStatus = 'PAYMENT_PENDING' | 'PAYMENT_REVIEW_REQUIRED' | 'PAID';

export interface PaymentIntent {
  id: string;
  transactionId: string;
  method: PaymentMethod;
  amount: number;
  expectedReference: string;
  online: boolean;
  status: PaymentStatus;
  createdAt: string;
}

// ── Staff ────────────────────────────────────────────────────
export interface Staff {
  id: string;
  name: string;
  role: string;
  branch: string;
  skills: string[];
  available: boolean;
}

export interface StaffLock {
  lockId: string;
  staffId: string;
  transactionId: string;
  lockedAt: string;
  lockedUntil: string;
  status: 'ACTIVE' | 'RELEASED';
}

// ── Customer ─────────────────────────────────────────────────
export interface Customer {
  id: string;
  name: string;
  phone: string;
  isGuest: boolean;
}

// ── Service / Cart ───────────────────────────────────────────
export interface Service {
  id: string;
  code: string;
  name: string;
  price: number;
  duration: number; // minutes
  category: string;
}

export interface CartItem {
  id: string;
  service: Service;
  staff: Staff | null;
  price: number;
  discount: number;
  total: number;
}

// ── Transaction ──────────────────────────────────────────────
export interface Transaction {
  id: string;
  state: TransactionState;
  branchCode: string;
  deviceId: string;
  cashierId: string;
  customer: Customer | null;
  items: CartItem[];
  subtotal: number;
  discount: number;
  total: number;
  paymentMethod: PaymentMethod | null;
  paymentIntent: PaymentIntent | null;
  posCode: string | null;
  staffLock: StaffLock | null;
  createdAt: string;
  updatedAt: string;
}

// ── Audit ────────────────────────────────────────────────────
export interface AuditEvent {
  transactionId: string;
  from: TransactionState;
  to: TransactionState;
  actor: string;
  timestamp: string;
  reason?: string;
  metadata?: Record<string, unknown>;
}

// ── Exceptions ───────────────────────────────────────────────
export type ExceptionType =
  | 'SYNC_FAILURE'
  | 'UNMAPPED_COA'
  | 'PAYMENT_REVIEW_REQUIRED'
  | 'RECONCILIATION_MISMATCH'
  | 'DUPLICATE_EVENT'
  | 'PAYLOAD_VALIDATION';

export type ExceptionStatus = 'OPEN' | 'IN_REVIEW' | 'RESOLVED' | 'ESCALATED';

export type ExceptionPriority = 'critical' | 'high' | 'medium';

export interface ExceptionItem {
  exceptionId: string;
  exceptionType: ExceptionType;
  referenceId: string;
  posCode: string | null;
  priority: ExceptionPriority;
  status: ExceptionStatus;
  ownerRoles: string[];
  slaHours: number;
  createdAt: string;
  resolvedBy: string | null;
  resolution: string | null;
  isOverdue: boolean;
}

export const EXCEPTION_TYPE_LABELS: Record<ExceptionType, string> = {
  SYNC_FAILURE: 'Gagal Sinkronisasi',
  UNMAPPED_COA: 'COA Belum Di-mapping',
  PAYMENT_REVIEW_REQUIRED: 'Pembayaran Perlu Review',
  RECONCILIATION_MISMATCH: 'Ketidakcocokan Rekonsiliasi',
  DUPLICATE_EVENT: 'Duplikat Event',
  PAYLOAD_VALIDATION: 'Validasi Payload Gagal',
};

// ── Dashboard ────────────────────────────────────────────────
export interface DashboardSummary {
  operationalSales: number;
  postedRevenue: number;
  unpostedPaidSales: number;
  settlementPending: { count: number; total: number };
  unreconciledVariance: { count: number };
  treatmentStats: { scheduled: number; completed: number; cancelled: number; noShow: number };
  cashPosition: { expected: number; counted: number; variance: number };
  topServices: { name: string; revenue: number; count: number }[];
  transactionCounts: { total: number; cash: number; qris: number; bankTransfer: number };
  lastUpdatedAt: string;
}

export interface DashboardAlert {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  count: number;
  actionUrl: string | null;
}

// ── COA Mapping ──────────────────────────────────────────────
export type MappingType = 'SERVICE' | 'PAYMENT_METHOD' | 'DISCOUNT' | 'ROUNDING';

export interface CoaMapping {
  id: string;
  mappingType: MappingType;
  itemCode: string;
  itemName: string;
  accountCode: string;
  accountName: string;
  isActive: boolean;
  createdAt: string;
}

export interface CoaAccount {
  code: string;
  name: string;
  type: 'Asset' | 'Liability' | 'Equity' | 'Revenue' | 'Expense';
  isActive: boolean;
}

export interface MappingStatusSummary {
  service: { total: number; unmapped: number };
  paymentMethod: { total: number; unmapped: number };
  discount: { total: number; unmapped: number };
  rounding: { total: number; unmapped: number };
}

// ── Daily Closing ────────────────────────────────────────────
export interface DailyClosingSummary {
  date: string;
  branchCode: string;
  totalTransactions: number;
  totalNominal: number;
  byMethod: { cash: number; qris: number; bankTransfer: number };
  unpostedCount: number;
  openExceptionCount: number;
  criticalExceptionCount: number;
  cashExpected: number;
}

export interface ClosingReport {
  id: string;
  date: string;
  branchCode: string;
  managerName: string;
  totalTransactions: number;
  totalNominal: number;
  byMethod: { cash: number; qris: number; bankTransfer: number };
  cashExpected: number;
  cashCounted: number;
  variance: number;
  varianceReason: string | null;
  varianceNote: string | null;
  openExceptionCount: number;
  unpostedCount: number;
  closedAt: string;
  approvedBy: string | null;
}

// ── Error Messages (Exact text from spec) ────────────────────
export const ERROR_MESSAGES = {
  PRICE_EXPIRED: 'Harga layanan telah berubah. Silakan ulangi pemilihan layanan.',
  PROMO_EXPIRED: 'Promo sudah tidak berlaku. Lanjutkan checkout tanpa promo?',
  PAYMENT_METHOD_INACTIVE: 'Metode pembayaran tidak tersedia. Pilih metode lain.',
  NO_STAFF_AVAILABLE: 'Tidak ada staff tersedia saat ini. Transaksi dibatalkan.',
  STAFF_REPLACED: (name: string) => `Staff diganti ke ${name}. Transaksi dilanjutkan.`,
  PAYMENT_REVIEW: 'Transaksi dibatalkan. Jika customer sudah bayar, hubungi manager.',
} as const;

// ── API Response ─────────────────────────────────────────────
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ErrorResponse {
  success: false;
  message: string;
  code?: string;
}
