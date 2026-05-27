# 📋 Product Requirements Document (PRD)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | PRD v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **Status** | DRAFT — Pending Stakeholder Approval |

---

## 1. Executive Summary

Beauty & Shine adalah platform premium beauty & wellness yang membutuhkan sistem POS (Point of Sale) dan ERP (Enterprise Resource Planning) terintegrasi. Tujuan utama: mengubah proses bisnis manual menjadi digital seamless — dari booking treatment sampai laporan keuangan.

**Target Users:**
- **Owner** — monitoring bisnis, laporan keuangan, keputusan strategis
- **Manager** — operasional harian, stok, jadwal staff
- **Kasir** — transaksi penjualan, shift management
- **Customer** — booking treatment, loyalty program

---

## 2. Business Goals

| # | Goal | KPI | Target |
|---|---|---|---|
| BG-1 | Automasi transaksi POS | Transaksi per hari | 50+/hari per cabang |
| BG-2 | Real-time inventory tracking | Stok akurasi | 99.5% |
| BG-3 | Integrated financial reporting | Laporan otomatis | Harian, mingguan, bulanan |
| BG-4 | Customer retention via loyalty | Repeat customer rate | 40%+ |
| BG-5 | Multi-payment support (BCA VA + Midtrans) | Payment success rate | 99%+ |
| BG-6 | Multi-branch support | Jumlah cabang | Scalable |

---

## 3. User Roles & Permissions

| Role | Level | Key Permissions |
|---|---|---|
| **Super Admin** | System | Full access, user management, system config |
| **Owner** | Business | Dashboard, reports, financial data, branch management |
| **Manager** | Branch | Staff scheduling, inventory, daily reports, approval |
| **Kasir** | Branch | POS transactions, shift start/end, receipt printing |
| **Therapist/Staff** | Branch | View schedule, treatment log, commission tracking |
| **Customer** | External | Booking, loyalty points, history, profile |

---

## 4. Functional Requirements

### 4.1 Authentication & Authorization

| ID | Requirement | Priority | Status |
|---|---|---|---|
| AUTH-01 | Login via username + password | P0 | ✅ Mock |
| AUTH-02 | JWT token-based session management | P0 | ❌ Not Built |
| AUTH-03 | Role-based access control (RBAC) | P0 | ⚠️ Partial |
| AUTH-04 | Password hashing (bcrypt) | P0 | ❌ Not Built |
| AUTH-05 | Session timeout (30 min idle) | P1 | ❌ Not Built |
| AUTH-06 | Audit trail (login/logout log) | P1 | ❌ Not Built |
| AUTH-07 | Password reset via email | P2 | ❌ Not Built |
| AUTH-08 | 2FA (optional for admin) | P3 | ❌ Not Built |

### 4.2 POS (Point of Sale)

| ID | Requirement | Priority | Status |
|---|---|---|---|
| POS-01 | Staff login via Staff ID + PIN | P0 | ✅ Mock |
| POS-02 | Shift management (start/end) | P0 | ✅ Mock |
| POS-03 | Product/service catalog display | P0 | ✅ Static |
| POS-04 | Add to cart with quantity | P0 | ✅ Client-side |
| POS-05 | Cart management (add/remove/qty) | P0 | ✅ Client-side |
| POS-06 | Tax calculation (PPN 11%) | P0 | ✅ Client-side |
| POS-07 | Payment processing (cash, QRIS, VA) | P0 | ❌ Not Built |
| POS-08 | Transaction receipt (print/PDF) | P0 | ❌ Not Built |
| POS-09 | Daily shift summary (Z-report) | P0 | ❌ Not Built |
| POS-10 | Discount/promo code support | P1 | ❌ Not Built |
| POS-11 | Split payment | P1 | ❌ Not Built |
| POS-12 | Customer membership integration | P1 | ❌ Not Built |
| POS-13 | Offline mode with sync | P2 | ❌ Not Built |
| POS-14 | Barcode scanner support | P2 | ❌ Not Built |

### 4.3 Payment Integration

| ID | Requirement | Priority | Status |
|---|---|---|---|
| PAY-01 | BCA Virtual Account generation | P0 | ❌ Not Built |
| PAY-02 | Midtrans Snap integration | P0 | ❌ Not Built |
| PAY-03 | Payment callback/webhook handling | P0 | ❌ Not Built |
| PAY-04 | Payment status tracking | P0 | ❌ Not Built |
| PAY-05 | Payment reconciliation | P1 | ❌ Not Built |
| PAY-06 | Refund processing | P1 | ❌ Not Built |
| PAY-07 | Payment method reporting | P1 | ❌ Not Built |

### 4.4 Inventory Management

| ID | Requirement | Priority | Status |
|---|---|---|---|
| INV-01 | Product/service catalog CRUD | P0 | ❌ Not Built |
| INV-02 | Stock tracking (qty-based products) | P0 | ❌ Not Built |
| INV-03 | Low stock alerts | P1 | ❌ Not Built |
| INV-04 | Stock opname / stock take | P1 | ❌ Not Built |
| INV-05 | Supplier management | P1 | ❌ Not Built |
| INV-06 | Purchase order | P2 | ❌ Not Built |
| INV-07 | Stock movement history | P1 | ❌ Not Built |

### 4.5 Staff Management

| ID | Requirement | Priority | Status |
|---|---|---|---|
| STF-01 | Staff CRUD (create, read, update, delete) | P0 | ❌ Not Built |
| STF-02 | Staff PIN management | P0 | ⚠️ Mock |
| STF-03 | Role assignment | P0 | ❌ Not Built |
| STF-04 | Shift scheduling | P1 | ❌ Not Built |
| STF-05 | Commission tracking | P1 | ❌ Not Built |
| STF-06 | Performance metrics | P2 | ❌ Not Built |
| STF-07 | Attendance tracking | P1 | ❌ Not Built |

### 4.6 Treatment & Booking

| ID | Requirement | Priority | Status |
|---|---|---|---|
| TRT-01 | Service catalog (treatment types) | P0 | ✅ Static |
| TRT-02 | Staff availability check | P0 | ⚠️ Domain logic |
| TRT-03 | Booking calendar | P0 | ❌ Not Built |
| TRT-04 | Booking confirmation (SMS/WA) | P1 | ❌ Not Built |
| TRT-05 | Staff auto-assignment | P1 | ⚠️ Domain logic |
| TRT-06 | Treatment history per customer | P1 | ❌ Not Built |
| TRT-07 | Room/resource scheduling | P2 | ❌ Not Built |

### 4.7 Customer & Loyalty

| ID | Requirement | Priority | Status |
|---|---|---|---|
| CUS-01 | Customer registration | P0 | ❌ Not Built |
| CUS-02 | Customer profile management | P0 | ❌ Not Built |
| CUS-03 | Loyalty points system | P1 | ❌ Not Built |
| CUS-04 | Tier membership (Silver/Gold/Platinum) | P1 | ❌ Not Built |
| CUS-05 | Visit history & preferences | P1 | ❌ Not Built |
| CUS-06 | Birthday/anniversary rewards | P2 | ❌ Not Built |
| CUS-07 | Referral program | P2 | ❌ Not Built |

### 4.8 Financial & Accounting

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FIN-01 | Chart of Accounts (COA) | P0 | ⚠️ Domain logic |
| FIN-02 | Journal entry (auto from POS) | P0 | ⚠️ Domain logic |
| FIN-03 | Revenue reporting (daily/weekly/monthly) | P0 | ❌ Not Built |
| FIN-04 | Expense tracking | P1 | ❌ Not Built |
| FIN-05 | Profit & Loss statement | P1 | ❌ Not Built |
| FIN-06 | Period lock (prevent backdate) | P1 | ⚠️ Domain logic |
| FIN-07 | Tax reporting (PPN) | P1 | ❌ Not Built |
| FIN-08 | Cash flow statement | P2 | ❌ Not Built |

### 4.9 Dashboard & Reporting

| ID | Requirement | Priority | Status |
|---|---|---|---|
| RPT-01 | Owner dashboard (revenue, transactions) | P0 | ⚠️ Static |
| RPT-02 | Real-time transaction monitoring | P0 | ❌ Not Built |
| RPT-03 | Sales by service/product report | P0 | ❌ Not Built |
| RPT-04 | Staff performance report | P1 | ❌ Not Built |
| RPT-05 | Customer analytics | P1 | ❌ Not Built |
| RPT-06 | Inventory report | P1 | ❌ Not Built |
| RPT-07 | Export to Excel/PDF | P1 | ❌ Not Built |
| RPT-08 | Custom date range filtering | P1 | ❌ Not Built |

### 4.10 Multi-Branch

| ID | Requirement | Priority | Status |
|---|---|---|---|
| BRN-01 | Branch CRUD | P1 | ❌ Not Built |
| BRN-02 | Per-branch inventory | P1 | ❌ Not Built |
| BRN-03 | Per-branch staff assignment | P1 | ❌ Not Built |
| BRN-04 | Consolidated reporting | P1 | ❌ Not Built |
| BRN-05 | Inter-branch stock transfer | P2 | ❌ Not Built |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | API response time | < 200ms (p95) |
| NFR-02 | Page load time | < 2 seconds |
| NFR-03 | Concurrent users per branch | 50+ |
| NFR-04 | Database query time | < 50ms (p95) |

### 5.2 Security

| ID | Requirement | Target |
|---|---|---|
| NFR-05 | HTTPS everywhere | Cloudflare SSL |
| NFR-06 | Password hashing | bcrypt, min 12 rounds |
| NFR-07 | SQL injection prevention | ORM/parameterized queries |
| NFR-08 | XSS prevention | Input sanitization, CSP headers |
| NFR-09 | Rate limiting | 100 req/min per IP |
| NFR-10 | Sensitive data encryption | AES-256 at rest |

### 5.3 Reliability

| ID | Requirement | Target |
|---|---|---|
| NFR-11 | Uptime | 99.5% |
| NFR-12 | Database backup | Daily automated |
| NFR-13 | Disaster recovery | RPO 24h, RTO 4h |
| NFR-14 | Error logging | Structured logging to file |

### 5.4 Scalability

| ID | Requirement | Target |
|---|---|---|
| NFR-15 | Horizontal scaling | Stateless API design |
| NFR-16 | Database connection pooling | pgbouncer |
| NFR-16 | Static asset CDN | Cloudflare |

---

## 6. Technical Architecture

### 6.1 Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | HTML/CSS/JS (vanilla) | Landing, POS, Dashboard |
| Backend | Python 3.12 + FastAPI | REST API |
| Database | PostgreSQL 16 | Data persistence |
| Cache | Redis (future) | Session, rate limiting |
| Payment | BCA VA + Midtrans | Payment gateway |
| Proxy | Cloudflare Tunnel | HTTPS, CDN |
| Container | Docker + Docker Compose | Deployment |

### 6.2 API Endpoints (Current + Planned)

```
# Auth
POST   /auth/login              → Login (username + password)
POST   /auth/logout             → Logout (invalidate token)
POST   /auth/refresh            → Refresh JWT token

# POS
POST   /pos/auth                → Staff login (Staff ID + PIN)
POST   /pos/end-shift           → End shift
GET    /pos/shifts              → List active shifts
POST   /pos/transactions        → Create transaction
GET    /pos/transactions/:id    → Get transaction detail
GET    /pos/z-report            → Daily shift summary

# Products & Services
GET    /products                → List products
POST   /products                → Create product (admin)
PUT    /products/:id            → Update product
DELETE /products/:id            → Delete product
GET    /services                → List services
POST   /services                → Create service (admin)

# Customers
GET    /customers               → List customers
POST   /customers               → Register customer
GET    /customers/:id           → Customer profile
PUT    /customers/:id           → Update customer
GET    /customers/:id/history   → Visit history

# Bookings
GET    /bookings                → List bookings
POST   /bookings                → Create booking
PUT    /bookings/:id            → Update booking
DELETE /bookings/:id            → Cancel booking

# Staff
GET    /staff                   → List staff
POST   /staff                   → Create staff
PUT    /staff/:id               → Update staff
GET    /staff/:id/schedule      → Staff schedule

# Inventory
GET    /inventory               → Stock list
POST   /inventory/adjust        → Stock adjustment
GET    /inventory/alerts        → Low stock alerts

# Payments
POST   /payments/bca-va         → Generate BCA VA
POST   /payments/midtrans       → Create Midtrans transaction
POST   /payments/callback       → Payment webhook
GET    /payments/:id/status     → Check payment status

# Reports
GET    /reports/revenue         → Revenue report
GET    /reports/sales           → Sales report
GET    /reports/staff           → Staff performance
GET    /reports/inventory       → Inventory report

# Dashboard
GET    /dashboard/summary       → Dashboard summary data
GET    /dashboard/realtime      → Real-time metrics
```

---

## 7. Data Flow

### 7.1 POS Transaction Flow
```
Customer arrives
    ↓
Kasir starts shift (Staff ID + PIN)
    ↓
Select services/products → Add to cart
    ↓
Apply discount (optional)
    ↓
Calculate tax (PPN 11%)
    ↓
Select payment method
    ├─ Cash → Confirm amount → Change calculation
    ├─ BCA VA → Generate VA → Customer pays → Callback confirm
    └─ Midtrans (QRIS/Card) → Redirect → Callback confirm
    ↓
Payment confirmed → Generate receipt
    ↓
Auto-generate journal entry (debit cash/revenue credit)
    ↓
Update inventory (if product)
    ↓
Add loyalty points (if member)
    ↓
Transaction complete
```

### 7.2 Booking Flow
```
Customer books (web/WA/walk-in)
    ↓
Select service + preferred staff
    ↓
Check staff availability
    ↓
Select date & time slot
    ↓
Confirm booking → Send notification
    ↓
Customer arrives → Check-in
    ↓
Treatment → POS transaction
    ↓
Loyalty points → Review request
```

---

## 8. UI/UX Requirements (per Brief)

### 8.1 Brand Identity
- **Visual Direction:** High-end, sophisticated, ethereal
- **Color Palette:** Ivory `#FDFBF7`, Soft Gold `#C9A96E`, Deep Charcoal `#1C1C1E`, Rose `#C08081`
- **Typography:** Playfair Display (headings), Inter (body)
- **Effects:** Shimmer animation, scroll-triggered transitions, soft shadows

### 8.2 Pages Required

| Page | URL | Description | Status |
|---|---|---|---|
| Landing Page | `beauty.beautynshine.web.id` | Hero + Services + Testimonials + CTA | ✅ Built |
| Login Page | `erp.beautynshine.web.id/login` | Split-screen elegant login | ✅ Built |
| POS Terminal | `pos.beautynshine.web.id` | Staff login → Product grid → Cart → Checkout | ✅ Mock |
| Owner Dashboard | `erp.beautynshine.web.id/dashboard` | Revenue, metrics, activity, quick actions | ⚠️ Static |
| Customer Portal (future) | `book.beautynshine.web.id` | Booking + loyalty + history | ❌ Not Built |

---

## 9. Milestones & Phases

### Phase 1 — Foundation (Week 1-2)
- [ ] Database schema implementation (PostgreSQL migrations)
- [ ] JWT authentication + RBAC
- [ ] Staff CRUD + PIN management
- [ ] Product/Service catalog CRUD
- [ ] POS transaction (persist to DB)

### Phase 2 — Core Business (Week 3-4)
- [ ] Payment integration (BCA VA + Midtrans)
- [ ] Inventory management
- [ ] Customer registration + profile
- [ ] Booking system
- [ ] Daily Z-report

### Phase 3 — Intelligence (Week 5-6)
- [ ] Real-time dashboard with live data
- [ ] Revenue/sales/inventory reports
- [ ] Loyalty points system
- [ ] Staff commission tracking
- [ ] Multi-branch support

### Phase 4 — Polish (Week 7-8)
- [ ] Receipt printing (thermal printer)
- [ ] Offline mode with sync
- [ ] Performance optimization
- [ ] Security audit
- [ ] UAT + production deployment

---

## 10. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| VPS resource limit (1 vCPU, 1GB RAM) | High | High | Upgrade to 2 vCPU/4GB RAM |
| Payment gateway delay | Medium | Medium | Start with manual cash, add gateway later |
| Data loss | High | Low | Daily automated backup |
| Security breach | High | Low | HTTPS + bcrypt + RBAC + rate limiting |
| Scope creep | Medium | High | Strict phase-based development |

---

## 11. Glossary

| Term | Definition |
|---|---|
| POS | Point of Sale — sistem kasir |
| ERP | Enterprise Resource Planning — sistem manajemen bisnis |
| COA | Chart of Accounts — bagan akun |
| PPN | Pajak Pertambahan Nilai (VAT) |
| VA | Virtual Account — rekening virtual |
| QRIS | Quick Response Code Indonesian Standard |
| Z-report | End-of-day sales summary report |
| RBAC | Role-Based Access Control |
| JWT | JSON Web Token |
| CRM | Customer Relationship Management |

---

*Document ini harus di-review dan di-approve oleh stakeholder sebelum development phase dimulai.*
