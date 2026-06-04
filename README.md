# POS-ERP V6 — Beauty & Shine

[![CI](https://github.com/your-org/pos-erp-v6/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/pos-erp-v6/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Node 20](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15-336791.svg)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Modular monolith POS + ERP system for salon and wellness businesses. Offline-first architecture with automatic sync, double-entry accounting, and multi-branch support.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Offline Checkout** | Process transactions without internet; auto-syncs when reconnected |
| **Treatment Management** | Service catalog, therapist assignment, staff lock with timeout |
| **Booking System** | Calendar view, customer management, bed/room assignment |
| **Daily Closing** | Dual-threshold reconciliation (Rp 100k / 5%) |
| **Inventory** | Stock cards, batch tracking, stock opname, BOM |
| **Finance** | Journal entries, general ledger, COA management, period locking |
| **Payment Providers** | Cash, QRIS, BCA Virtual Account, Midtrans (HMAC verification) |
| **RBAC** | 5 roles × 11 actions: cashier, branch_manager, accounting_lead, it_admin, owner |
| **Multi-Branch** | 4 branches (BSD, HQ, DPK, CBG) with per-branch data isolation |
| **Export** | Products export to CSV, XLSX, PDF, JSON |
| **Reporting** | Sales, inventory, and finance reports with export |

---

## Tech Stack

**Backend:** Python 3.11 · FastAPI · PostgreSQL 15+ · psycopg  
**Frontend:** React 18 · TypeScript · Tailwind CSS · Vite  
**Infrastructure:** Docker · Cloudflare Tunnel · systemd  
**Domain:** `beautynshine.web.id`

---

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  React Frontend  │────▶│  FastAPI App  │────▶│  PostgreSQL   │
│  (Vite + TS)     │◀────│  (30 routers) │     │  15+          │
└─────────────────┘     └──────┬───────┘     └──────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │    POS     │   │ Inventory │   │ Accounting│
        │  Checkout  │   │ Treatment │   │ Reconcil. │
        └───────────┘   └───────────┘   └───────────┘
              │                │                │
              ▼                ▼                ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │  Payment   │   │   Sync    │   │  Security │
        │  Providers │   │  Outbox   │   │  RBAC     │
        └───────────┘   └───────────┘   └───────────┘
```

Detailed architecture: [docs/system-architecture.md](docs/system-architecture.md)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+

### Option A: Docker

```bash
git clone https://github.com/your-org/pos-erp-v6.git
cd pos-erp-v6
cp .env.example .env
# Edit .env with your database credentials
docker-compose up -d
```

### Option B: Manual Setup

```bash
# 1. Clone
git clone https://github.com/your-org/pos-erp-v6.git
cd pos-erp-v6

# 2. Environment
cp .env.example .env

# 3. Database
createdb pos_erp

# 4. Backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn psycopg pydantic python-jose passlib bcrypt
uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

# 5. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Detailed setup: [docs/setup.md](docs/setup.md)

---

## Environment Variables

See [`.env.example`](.env.example) for all configuration options. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `POS_ERP_DATABASE_URL` | PostgreSQL connection string | Yes |
| `POS_ERP_SECRET_KEY` | JWT signing secret | Yes |
| `POSTGRES_HOST` | Database host | Yes |
| `POSTGRES_PORT` | Database port (default: 5432) | No |
| `CORS_ORIGINS` | Allowed frontend origins | No |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare tunnel token | No |

---

## Development

```bash
# Backend (with hot reload)
uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (with HMR)
cd frontend && npm run dev

# Run tests
pytest tests/ -v

# Lint
ruff check src/
```

---

## Testing

```bash
# Backend tests
pytest tests/ -v --timeout=30

# Frontend type check
cd frontend && npx tsc --noEmit

# Smoke test
python smoke_test.py
```

---

## Deployment

- **Docker:** `docker-compose up -d`
- **systemd:** `sudo systemctl start pos-erp`
- **Cloudflare Tunnel:** See [docs/deployment-guide.md](docs/deployment-guide.md)

---

## Folder Structure

```
pos-erp-v6/
├── src/pos_erp/          # Python backend
│   ├── routers/          # 30+ API route modules
│   ├── auth.py           # JWT authentication
│   ├── db.py             # Database connection pool
│   ├── config.py         # Environment configuration
│   └── fastapi_app.py    # FastAPI application entry
├── frontend/             # React + TypeScript
│   ├── src/pages/        # Page components
│   ├── src/components/   # Shared components
│   ├── src/api/          # API client
│   └── src/hooks/        # Custom React hooks
├── tests/                # pytest test suite
├── docs/                 # Documentation
├── .github/              # CI, issue templates
├── Dockerfile            # Container build
├── docker-compose.yml    # Local services
└── pyproject.toml        # Python project config
```

---

## API Documentation

- **Swagger UI:** http://localhost:8000/docs (dev mode)
- **Reference:** [docs/api-reference.md](docs/api-reference.md)

---

## Roadmap

- **v0.1** (Done): POS core, checkout, treatment, booking, closing
- **v0.2** (In Progress): Inventory, accounting, reporting
- **v0.3** (Planned): Multi-branch sync, mobile app, analytics
- **v1.0** (Target): Production-ready full ERP suite

See [docs/roadmap.md](docs/roadmap.md) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Branch naming conventions
- Commit message format
- Pull request process
- Code review checklist

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

---

## Maintainer

**Beauty & Shine Development Team**  
Domain: `beautynshine.web.id`
