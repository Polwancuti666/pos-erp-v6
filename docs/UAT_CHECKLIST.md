# Beauty & Shine POS-ERP V6 — UAT Checklist

## Phase 1: Foundation ✅
- [x] PostgreSQL database schema
- [x] JWT authentication + RBAC
- [x] Staff CRUD + PIN management
- [x] Product/Service catalog CRUD
- [x] POS transaction (persist to DB)

## Phase 2: Core Business ✅
- [x] Payment integration (Cash, QRIS, Bank Transfer)
- [x] Inventory management (stock cards, batches, BOM, opname)
- [x] Customer registration + profile
- [x] Booking system
- [x] Daily Z-report / closing
- [x] Voucher & Promo system

## Phase 3: Intelligence ✅
- [x] Real-time dashboard with charts (Recharts)
- [x] Revenue/sales/inventory reports with CSV export
- [x] Loyalty points system (earn/redeem/tier)
- [x] Staff commission tracking
- [x] Multi-branch support (branch selector, data isolation)

## Phase 4: Polish ✅
- [x] Receipt printing (58mm thermal + web print)
- [x] Offline mode with sync (Service Worker + IndexedDB)
- [x] Performance optimization (DB indexes)
- [x] Security audit (rate limiting, headers, CORS, size limits)
- [x] Production configuration

---

## Test Scenarios

### POS Flow
1. Login with Staff ID + PIN → should redirect to POS home
2. Create booking → select treatment → assign therapist
3. Process checkout → add items → apply voucher → pay
4. Print receipt → should show 58mm thermal format
5. Check loyalty points earned on receipt

### ERP Flow
1. Login with admin credentials → should show dashboard
2. Check dashboard charts (sales trend, top treatments, payment breakdown)
3. Navigate to Reports → filter by date range → export CSV
4. Navigate to Master Data → Loyalty tab → view leaderboard
5. Navigate to Reports → Commission tab → generate commissions
6. Switch branch in header → data should filter by branch

### Offline Flow
1. Disconnect network → POS should show "🔴 Offline" banner
2. Create transaction while offline → should queue for sync
3. Reconnect network → should show "🟢 Online" + sync pending
4. Verify transaction synced to server

### Security
1. Send >100 requests/min → should get 429 rate limit
2. Send >10 auth requests/min → should get 429
3. Send request >1MB body → should get 413
4. Check response headers for security headers

---

## Production Deployment

### Environment Variables
```bash
# Required
POSTGRES_USER=sa
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=pos_erp

# Security
JWT_SECRET=<random-64-char-secret>
CORS_ORIGINS=https://erp.beautynshine.web.id,https://pos.beautynshine.web.id

# Optional
LOG_LEVEL=INFO
```

### Deployment Steps
1. Run database migrations: `python apply_indexes.py`
2. Build frontend: `cd frontend && npm run build`
3. Start backend: `uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000`
4. Configure Nginx reverse proxy (see nginx.conf)
5. Setup SSL with Let's Encrypt
6. Configure systemd service (see pos-erp.service)

### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","service":"pos-erp-v6"}
```
