# POS-ERP Integration Engine V6

> Modular monolith POS + ERP system untuk bisnis salon kecantikan & wellness (UMKM).

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Masalah yang Dipecahkan

Bisnis salon UMKM di Indonesia membutuhkan sistem POS yang terintegrasi dengan ERP, namun solusi yang ada terlalu mahal atau terlalu kompleks. POS-ERP V6 menyediakan:

- **Kasir offline** — tetap bisa transaksi walau internet mati
- **Sinkronisasi otomatis** — data tersync ke ERP begitu koneksi pulih
- **Akuntansi double-entry** — jurnal otomatis dari setiap transaksi
- **Multi-pembayaran** — Cash, QRIS, dan Bank Transfer (BCA VA + Midtrans)
- **Manajemen stok** — tracking pergerakan inventory real-time
- **Koreksi transaksi** — matrix koreksi terstruktur (void, reversal, refund)

---

## Fitur Utama

| Fitur | Deskripsi |
|---|---|
| **Offline Checkout** | Transaksi berjalan tanpa internet; PaymentType: CASH / QRIS / BANK_TRANSFER |
| **Sync Outbox** | Queue pattern dengan status PENDING → SYNCED / RETRYABLE_FAILED / ESCALATED |
| **Accounting Posting** | Double-entry journal otomatis dengan COA mapping |
| **Staff Locks** | Reservasi staff (10-min timeout) untuk menghindari konflik |
| **Treatment Editing** | Tambah/hapus layanan sebelum pembayaran, saran reassign staff |
| **Daily Closing** | Rekonsiliasi dual-threshold (Rp100k / 5%) |
| **Correction Matrix** | Keputusan koreksi: local correction, ERP void, reversal journal, refund |
| **Payment Providers** | BCA Virtual Account + Midtrans dengan verifikasi signature HMAC |
| **RBAC** | 5 roles (cashier, branch_manager, accounting_lead, it_admin, owner) × 11 actions |
| **Observability** | Health check (database/outbox/erp/payment), MetricsRegistry |
| **Exception Queue** | Manajemen pengecualian dengan SLA tracking (2h–24h) |
| **Period Lock** | Penguncian periode akuntansi |
| **Document Numbering** | Penomoran otomatis POS/TRM/JRN/INV-MOV |

---

## Tech Stack

- **Runtime:** Python 3.11
- **Framework:** FastAPI
- **Database:** PostgreSQL 16
- **Containerization:** Docker + Docker Compose
- **Networking:** Cloudflare Tunnel (subdomain: `pos.`, `erp.`, `dashboard.`, `api.`)
- **Domain:** `beautynshine.web.id`

---

## Arsitektur

Modular monolith dengan pendekatan Domain-Driven Design (DDD). Setiap domain (POS, inventory, accounting, sync, dll.) adalah module terpisah dalam satu deployment.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  POS Client  │────▶│  FastAPI App  │────▶│  PostgreSQL   │
│  (Kasir)     │◀────│  (API Layer)  │     │  16           │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────┴───────┐
                    │  App Service  │
                    │  (Orchestr.)  │
                    └──────┬───────┘
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │  POS/Auth  │   │ Inventory │   │ Accounting│
    │  Checkout  │   │ Treatment │   │ Reconcil. │
    └───────────┘   └───────────┘   └───────────┘
          │                │                │
          ▼                ▼                ▼
    ┌───────────┐   ┌───────────┐   ┌───────────┐
    │  Payment   │   │   Sync    │   │  Security │
    │  Providers │   │  Outbox   │   │  RBAC     │
    └───────────┘   └───────────┘   └───────────┘
```

---

## Struktur Folder

```
pos-erp-v6/
├── src/pos_erp/
│   ├── fastapi_app.py          # FastAPI app factory & routes
│   ├── api.py                  # AppService — application layer orchestrator
│   ├── auth.py                 # ERP login (admin/kasir)
│   ├── pos_auth.py             # POS staff PIN auth + shift management
│   ├── checkout.py             # Offline checkout (CASH/QRIS/BANK_TRANSFER)
│   ├── payment.py              # Payment verification (QRIS callback, bank transfer, manual proof)
│   ├── payment_providers.py    # BCA VA + Midtrans adapters
│   ├── inventory.py            # Stock movement & inventory policy
│   ├── treatment.py            # Treatment service editing
│   ├── accounting.py           # Journal posting (double-entry)
│   ├── reconciliation.py       # Daily closing + dual-threshold reconciliation
│   ├── permissions.py          # RBAC (5 roles × 11 actions)
│   ├── security.py             # Encryption (XOR+HMAC), SecretPolicy
│   ├── staff_lock.py           # Staff reservation locks (10-min timeout)
│   ├── sync.py                 # SyncQueue outbox pattern
│   ├── sync_control.py         # Connectivity recovery, sync approval, BranchCache
│   ├── document_finalization.py # POS/TRM/JRN document finalization
│   ├── document_numbering.py   # NumberingService
│   ├── period_lock.py          # Accounting period lock
│   ├── correction.py           # Correction decision matrix
│   ├── exception_queue.py      # Exception management + SLA tracking
│   ├── dashboard.py            # Owner dashboard (BranchSnapshot)
│   ├── beauty_ui.py            # HTML dashboard (gold/ivory theme)
│   ├── observability.py        # Health check + metrics
│   ├── persistence.py          # InMemoryRepository + UnitOfWork
│   ├── postgresql.py           # PostgreSQL settings & connection URL
│   ├── migrations.py           # Schema migration runner
│   ├── deployment.py           # DeploymentManifest validation
│   ├── adapters.py             # PaymentGatewayAdapter, ErpAdapter
│   └── config.py               # AppConfig from env vars
├── tests/                       # 27 test files
├── docker-compose.yml
├── .env.example
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
└── CHANGELOG.md
```

---

## Instalasi

### Prerequisites

- Docker & Docker Compose
- Python 3.11 (untuk development lokal)
- PostgreSQL 16 (jika tidak pakai Docker)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/pos-erp-v6.git
cd pos-erp-v6
```

### 2. Setup Environment

```bash
cp .env.example .env
# Edit .env sesuai kebutuhan (lihat bagian .env di bawah)
```

### 3. Jalankan dengan Docker Compose

```bash
docker compose up -d
```

Service akan tersedia di:
- **API:** `http://localhost:8000`
- **Dashboard:** `http://localhost:8000/dashboard`
- **Health Check:** `http://localhost:8000/health`

### 4. Jalankan Secara Lokal (tanpa Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Pastikan PostgreSQL berjalan dan .env terkonfigurasi
python -m pos_erp.fastapi_app
```

---

## Konfigurasi `.env`

```env
# Database
DATABASE_URL=postgresql://pos_erp:secret@localhost:5432/pos_erp

# Security
ENCRYPTION_KEY=your-encryption-key-here
HMAC_SECRET=your-hmac-secret-here

# Payment Providers
MIDTRANS_SERVER_KEY=your-midtrans-key
MIDTRANS_CLIENT_KEY=your-midtrans-client-key
BCA_VIRTUAL_ACCOUNT_KEY=your-bca-va-key

# ERP
ERP_BASE_URL=https://erp.beautynshine.web.id
ERP_API_KEY=your-erp-api-key

# Application
APP_ENV=development
BRANCH_ID=branch-001
SYNC_INTERVAL_SECONDS=30
```

Lihat `src/pos_erp/config.py` untuk daftar lengkap environment variables.

---

## Testing

```bash
# Jalankan semua test
pytest

# Dengan coverage
pytest --cov=src/pos_erp --cov-report=html

# Jalankan test tertentu
pytest tests/test_checkout.py -v
```

Tersedia **27 test files** yang mencakup seluruh modul.

---

## Deployment

### Production dengan Docker Compose + Cloudflare Tunnel

```bash
# Build dan jalankan
docker compose -f docker-compose.yml up -d --build

# Jalankan migrations
docker compose exec api python -m pos_erp.migrations

# Pastikan cloudflared tunnel aktif untuk:
# - pos.beautynshine.web.id
# - erp.beautynshine.web.id
# - dashboard.beautynshine.web.id
# - api.beautynshine.web.id
```

---

## Roadmap

### Phase 1 — Core POS *(saat ini, v0.1.0)*
- [x] Offline checkout (CASH/QRIS/Bank Transfer)
- [x] Payment verification & providers (BCA VA, Midtrans)
- [x] Sync outbox pattern
- [x] Staff PIN auth + shift management
- [x] RBAC permissions
- [x] Accounting journal posting
- [x] Daily closing & reconciliation

### Phase 2 — Full ERP Integration *(planned)*
- [ ] Full ERP document sync (invoices, purchase orders)
- [ ] Customer loyalty & membership
- [ ] Payroll integration
- [ ] Tax reporting (PPN)
- [ ] Branch inventory transfer

### Phase 3 — Multi-Branch + iPad *(planned)*
- [ ] Native iPad POS app
- [ ] Real-time cross-branch inventory
- [ ] Centralized reporting dashboard
- [ ] Franchise management module
- [ ] API v2 dengan GraphQL

> Fitur yang ditandai *(planned)* belum diimplementasikan dan akan dikembangkan di versi mendatang.

---

## Kontribusi

Kami welcome kontribusi! Silakan baca [CONTRIBUTING.md](CONTRIBUTING.md) untuk panduan lengkap.

---

## License

[MIT](LICENSE) — bebas digunakan, dimodifikasi, dan didistribusikan.

---

## Kontak

- **Domain:** beautynshine.web.id
- **Issues:** GitHub Issues untuk bug report dan feature request
- **Security:** Lihat [SECURITY.md](SECURITY.md) untuk pelaporan vulnerability
