# Local Development Setup

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 15+
- Git

## 1. Clone the Repository

```bash
git clone https://github.com/your-org/pos-erp-v6.git
cd pos-erp-v6
```

## 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your local values (see .env.example for all options)
```

Minimum required variables:
- `POS_ERP_DATABASE_URL` — PostgreSQL connection string
- `POS_ERP_SECRET_KEY` — Random secret for JWT signing

## 3. Database Setup

```bash
# Create the database
createdb pos_erp

# Or via psql
psql -U postgres -c "CREATE DATABASE pos_erp;"
psql -U postgres -c "CREATE USER erp WITH PASSWORD 'your_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE pos_erp TO erp;"
```

## 4. Backend (Python)

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn psycopg pydantic python-jose passlib bcrypt

# Run database migrations (auto-applied on first start)
python -m pos_erp.migrations

# Start development server
uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000 --reload
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

## 5. Frontend (React + TypeScript)

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs at `http://localhost:5173` (proxies API to port 8000).

## 6. Verify Everything

| Service  | URL                          | Expected Response              |
|----------|------------------------------|--------------------------------|
| Backend  | http://localhost:8000/health | `{"status":"ok"}`              |
| Frontend | http://localhost:5173        | Login page                     |
| API Docs | http://localhost:8000/docs   | Swagger UI                     |

## Running Tests

```bash
# Backend tests
pytest tests/ -v

# Frontend type check
cd frontend && npx tsc --noEmit
```

## Common Development Commands

```bash
# Watch backend logs
tail -f /tmp/pos-erp.log

# Reset database
dropdb pos_erp && createdb pos_erp

# Build frontend for production
cd frontend && npm run build

# Run with Docker
docker-compose up -d
```
