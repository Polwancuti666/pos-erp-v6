# Changelog

Semua perubahan signifikan pada project POS-ERP Integration Engine V6 akan didokumentasikan di file ini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2025-05-27

### Initial Release

Release pertama POS-ERP Integration Engine V6 — modular monolith untuk bisnis salon kecantikan.

### Implemented Slices

**Slice 1 — Offline Checkout & Payment Types**
- `checkout.py` — Offline checkout dengan PaymentType (CASH, QRIS, BANK_TRANSFER) dan TransactionStatus
- `OfflineTransaction` dataclass untuk transaksi tanpa koneksi

**Slice 2 — Payment Verification & Providers**
- `payment.py` — Verifikasi pembayaran: QRIS callback, bank transfer, manual proof upload
- `payment_providers.py` — BCA Virtual Account + Midtrans adapter dengan HMAC signature verification
- `PaymentIntent` dan `VerificationResult` domain models

**Slice 3 — Sync Outbox Pattern**
- `sync.py` — SyncQueue dengan status PENDING → RETRYABLE_FAILED → SYNCED → ESCALATED
- `sync_control.py` — Connectivity recovery detection, sync approval, BranchCache, DeviceBinding

**Slice 4 — Accounting & Reconciliation**
- `accounting.py` — Double-entry journal posting dengan COA mapping (COAMapping, JournalLine, Journal)
- `reconciliation.py` — Daily closing dengan dual-threshold reconciliation (Rp100k / 5%)
- `period_lock.py` — Evaluasi penguncian periode akuntansi
- `document_numbering.py` — Penomoran dokumen POS/TRM/JRN/INV-MOV

**Slice 5 — Inventory & Treatment Management**
- `inventory.py` — StockMovement, MovementType (IN/OUT), MovementReason, InventoryPolicy, InventoryService
- `treatment.py` — TreatmentService editing: tambah/hapus layanan, saran reassign staff
- `staff_lock.py` — Staff reservation locks (10-min timeout) dengan audit logging

**Slice 6 — Auth, RBAC & Security**
- `auth.py` — ERP login (admin/kasir users)
- `pos_auth.py` — POS staff PIN auth dengan shift management
- `permissions.py` — RBAC: 5 roles (cashier, branch_manager, accounting_lead, it_admin, owner) × 11 actions
- `security.py` — EncryptionService (XOR+HMAC), SecretPolicy, production security verification

**Slice 7 — Dashboard, Observability & Infrastructure**
- `dashboard.py` — Owner dashboard dengan BranchSnapshot
- `beauty_ui.py` — HTML dashboard renderer (gold/ivory theme)
- `observability.py` — Health check (database/outbox/erp/payment), MetricsRegistry
- `correction.py` — Correction decision matrix: local correction, ERP void, reversal journal, refund
- `exception_queue.py` — Exception management dengan SLA tracking (2h–24h)
- `document_finalization.py` — ERP finalization untuk POS/TRM/JRN document numbers

### Infrastructure
- `fastapi_app.py` — FastAPI app factory dengan routes: `/`, `/login`, `/pos`, `/health`, `/dashboard`, `/payments/providers`
- `api.py` — AppService class sebagai application layer orchestrator
- `persistence.py` — InMemoryRepository + UnitOfWork pattern
- `postgresql.py` — PostgreSQL 16 settings dan connection URL builder
- `migrations.py` — MigrationRunner untuk schema migrations
- `deployment.py` — DeploymentManifest validation
- `adapters.py` — PaymentGatewayAdapter (HMAC webhook), ErpAdapter
- `config.py` — AppConfig dari environment variables
- `docker-compose.yml` — postgres:16-alpine + api service

### Testing
- 27 test files mencakup seluruh modul

### Documentation
- README.md — Project overview, instalasi, dan roadmap
- CONTRIBUTING.md — Panduan kontribusi
- CODE_OF_CONDUCT.md — Contributor Covenant v2.1
- SECURITY.md — Kebijakan keamanan dan pelaporan vulnerability
