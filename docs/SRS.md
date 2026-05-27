# 📐 Software Requirements Specification (SRS)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | SRS v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **IEEE Reference** | IEEE 830-1998 |
| **Reference** | BRD v1.0, FRD v1.0, TRD v1.0, ERD v1.0 |
| **Status** | DRAFT — Pending Stakeholder Approval |

---

## 1. Introduction

### 1.1 Purpose
Dokumen ini mendefinisikan spesifikasi lengkap kebutuhan perangkat lunak untuk sistem POS-ERP Beauty & Shine. SRS menjadi kontrak antara stakeholder dan development team.

### 1.2 Scope
**Nama Sistem:** Beauty & Shine POS-ERP Integration Engine V6
**Tujuan:** Mengelola operasional bisnis beauty & wellness secara digital — dari booking sampai laporan keuangan.
**User:** Owner, Manager, Kasir, Therapist, Customer

### 1.3 Definitions

| Term | Definition |
|---|---|
| POS | Point of Sale — sistem kasir |
| ERP | Enterprise Resource Planning |
| VA | Virtual Account |
| QRIS | Quick Response Code Indonesian Standard |
| PPN | Pajak Pertambahan Nilai (VAT 11%) |
| COA | Chart of Accounts |
| JWT | JSON Web Token |
| RBAC | Role-Based Access Control |
| CRUD | Create, Read, Update, Delete |
| Z-Report | End-of-day shift sales summary |

### 1.4 References

| Document | Version | Description |
|---|---|---|
| BRD | 1.0 | Business Requirements |
| FRD | 1.0 | Functional Requirements |
| TRD | 1.0 | Technical Requirements |
| ERD | 1.0 | Entity Relationship Diagram |
| PRD | 1.0 | Product Requirements |

---

## 2. Overall Description

### 2.1 Product Perspective

```
┌─────────────────────────────────────────────────────────┐
│                  BEAUTY & SHINE ECOSYSTEM                │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ LANDING  │    │   POS    │    │  ERP     │          │
│  │ (Public) │    │ (Kasir)  │    │ (Admin)  │          │
│  └────┬─────┘    └────┬─────┘    └────┬─────┘          │
│       │               │               │                 │
│       └───────────────┼───────────────┘                 │
│                       │                                 │
│              ┌────────┴────────┐                        │
│              │   FASTAPI API   │                        │
│              │   (Backend)     │                        │
│              └────────┬────────┘                        │
│                       │                                 │
│       ┌───────────────┼───────────────┐                │
│       │               │               │                │
│  ┌────┴─────┐   ┌─────┴────┐   ┌─────┴────┐          │
│  │PostgreSQL│   │ Payment  │   │ Cloudflare│          │
│  │(Database)│   │ Gateways │   │ (Tunnel)  │          │
│  └──────────┘   └──────────┘   └──────────┘          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 User Classes

| User Class | Technical Level | Frequency | Priority |
|---|---|---|---|
| Owner | Low-Medium | Daily (dashboard) | High |
| Manager | Medium | Daily (operations) | High |
| Kasir | Low | Continuous (POS) | Critical |
| Therapist | Low | Occasional (schedule) | Medium |
| Customer | Low | Weekly (booking) | Medium |

### 2.3 Operating Environment

| Component | Environment |
|---|---|
| Server OS | Ubuntu 24.04 LTS |
| Runtime | Python 3.12 in Docker |
| Database | PostgreSQL 16 in Docker |
| Web Server | Uvicorn (ASGI) |
| **Web Browser** | Chrome, Safari, Firefox, Edge (latest 2 versions) |
| **Mobile Browser** | Chrome Mobile, Safari Mobile (latest 2 versions) |
| **Android App** | PWA (Progressive Web App) — installable via browser |
| **Android Devices** | Smartphone (5"+), Tablet (7-10") |
| **iPad** | iPad Air, iPad Pro (planned Phase 2) |
| Network | Internet required (offline mode future) |

### 2.4 Supported Platforms & Devices

| Platform | Access Method | Device | Status | Priority |
|---|---|---|---|---|
| **Desktop Web** | Browser (Chrome, Safari, Firefox, Edge) | PC/Laptop | ✅ Supported | P0 |
| **Mobile Web** | Browser (Chrome Mobile, Safari Mobile) | Android Phone | ✅ Supported | P0 |
| **Mobile Web** | Browser (Chrome Mobile, Safari Mobile) | iPhone | ✅ Supported | P0 |
| **Android App** | PWA (installable from browser) | Android Phone | ✅ Supported | P0 |
| **Android App** | PWA (installable from browser) | Android Tablet | ✅ Supported | P0 |
| **iPad** | Browser (Safari) | iPad Air/Pro | 🔜 Planned | P1 |
| **iPad App** | PWA (installable from Safari) | iPad Air/Pro | 🔜 Planned | P1 |

### 2.5 Responsive Breakpoints

| Breakpoint | Width | Target Device | Layout |
|---|---|---|---|
| Mobile S | 320px | Small phone (SE, Mini) | Single column, stacked |
| Mobile M | 375px | Standard phone (iPhone 14, Pixel) | Single column, optimized |
| Mobile L | 425px | Large phone (iPhone Pro Max, Samsung S) | Single column, spacious |
| Tablet | 768px | Android tablet, iPad Mini | 2-column, side cart |
| Desktop | 1024px+ | PC, Laptop, iPad Pro | Full layout, grid products |

### 2.6 PWA (Progressive Web App) Requirements

| Requirement | Description |
|---|---|
| **Installable** | User can "Add to Home Screen" from browser |
| **App Shell** | Native app-like experience (no browser chrome) |
| **Offline Cache** | Static assets cached (HTML, CSS, JS, images) |
| **Splash Screen** | Custom splash with Beauty & Shine branding |
| **App Icon** | 192x192 and 512x512 PNG icons |
| **Manifest** | Web App Manifest with theme_color, display: standalone |
| **Service Worker** | Cache-first for static, network-first for API |

### 2.7 Constraints

| Constraint | Impact |
|---|---|
| VPS: 1 vCPU, 961 MB RAM | Need upgrade before production |
| Single developer | Timeline: 8 weeks for MVP |
| PWA instead of native app | Faster development, single codebase |
| iPad native app deferred | Phase 2 — PWA works on iPad via Safari |
| Cloudflare Free plan | Limited WAF rules, no custom SSL |
| Indonesian market | Bahasa Indonesia primary, PPN 11% |

### 2.5 Assumptions

1. Internet connectivity available at all times
2. Staff will be trained before system goes live
3. Payment gateway accounts (BCA, Midtrans) will be approved
4. VPS will be upgraded to 2 vCPU / 4 GB RAM minimum

---

## 3. System Features

### 3.1 Feature List

| # | Feature | Module | Priority | Description |
|---|---|---|---|---|
| F-01 | User Authentication | AUTH | P0 | Login, JWT, RBAC |
| F-02 | POS Transactions | POS | P0 | Cart, checkout, receipt, print, WhatsApp |
| F-03 | Payment Processing | PAYMENT | P0 | Cash, BCA VA, Midtrans |
| F-04 | Booking Management | BOOKING | P0 | Create, confirm, cancel |
| F-05 | Staff Management | STAFF | P0 | CRUD, roles, shift |
| F-06 | Product/Service Catalog | CATALOG | P0 | CRUD, pricing |
| F-07 | Customer Management | CUSTOMER | P0 | Registration, profile |
| F-08 | Inventory Tracking | INVENTORY | P0 | Stock, movement, alerts |
| F-09 | Financial Accounting | FINANCE | P0 | Journal, COA, reports |
| F-10 | Dashboard & Reports | DASHBOARD | P0 | KPI, analytics, export |
| F-11 | Loyalty Program | LOYALTY | P1 | Points, tiers, rewards |
| F-12 | Audit Logging | AUDIT | P0 | Track all changes |

### 3.2 Feature Detail: POS Transactions (F-02)

**Description:** Sistem kasir digital untuk memproses penjualan produk dan layanan.

**Functional Requirements:**
- FR-02.1: Kasir dapat login dengan Staff ID + PIN
- FR-02.2: Kasir dapat memulai dan mengakhiri shift
- FR-02.3: Sistem menampilkan katalog produk dan layanan
- FR-02.4: Kasir dapat menambah item ke keranjang
- FR-02.5: Kasir dapat mengubah quantity dan menghapus item
- FR-02.6: Sistem menghitung subtotal, PPN 11%, dan total secara otomatis
- FR-02.7: Kasir dapat memilih metode pembayaran
- FR-02.8: Sistem memproses pembayaran dan menghasilkan receipt
- FR-02.9: Sistem menyimpan transaksi ke database
- FR-02.10: Sistem mengupdate stok produk setelah transaksi
- FR-02.11: Sistem generate receipt (HTML + PDF + ESC/POS)
- FR-02.12: Kasir dapat mencetak receipt ke thermal printer
- FR-02.13: Kasir dapat mengirim receipt ke customer via WhatsApp
- FR-02.14: Receipt tersimpan di ATTACHMENT table untuk riwayat

**Use Case: UC-02 — Process POS Transaction**

```
Actor:    Kasir
Precondition: Kasir sudah login dan shift aktif
Trigger:  Customer ingin membayar

Main Flow:
1. Kasir memilih produk/layanan dari katalog
2. Item ditambahkan ke keranjang
3. Kasir menambah/mengurangi quantity jika perlu
4. Kasir menekan tombol "Bayar"
5. Sistem menampilkan total (termasuk PPN 11%)
6. Kasir memilih metode pembayaran
7. Sistem memproses pembayaran:
   a. Cash: Kasir input jumlah dibayar, sistem hitung kembalian
   b. BCA VA: Sistem generate nomor VA
   c. Midtrans: Sistem redirect ke halaman pembayaran
8. Pembayaran berhasil dikonfirmasi
9. Sistem generate receipt
10. Sistem update stok produk
11. Sistem buat journal entry otomatis
12. Sistem tambah loyalty points (jika customer member)
13. Sistem tampilkan opsi: [Print Receipt] [Send WhatsApp] [Download PDF]
14. Kasir pilih opsi receipt delivery

Alternative Flow:
6a. Customer batal → Kasir void transaksi (butuh approval manager)
7a. Pembayaran gagal → Sistem tampilkan error, minta metode lain

Postcondition:
- Transaksi tersimpan di database
- Stok produk terupdate
- Journal entry tercatat
- Loyalty points bertambah (jika applicable)
```

**UI Mockup:**
```
┌─────────────────────────────────────────────────────────┐
│ 🛍️ Beauty & Shine POS                    [Staff Name] │
├────────────────────────────┬────────────────────────────┤
│ Services & Products        │ Shopping Cart              │
│ ┌──────┐ ┌──────┐ ┌──────┐│ ┌────────────────────┐    │
│ │Facial│ │Cream │ │Hair  ││ │ 1x Facial    150k  │    │
│ │150k  │ │120k  │ │130k  ││ │ 1x Massage   200k  │    │
│ └──────┘ └──────┘ └──────││ └────────────────────┘    │
│ ┌──────┐ ┌──────┐ ┌──────┐│                            │
│ │Mani  │ │Pedi  │ │Body  ││ Subtotal     Rp 350.000   │
│ │80k   │ │90k   │ │200k  ││ PPN (11%)    Rp  38.500   │
│ └──────┘ └──────┘ └──────┘│ Total        Rp 388.500   │
│                            │                            │
│                            │ [    💳 Bayar    ]         │
└────────────────────────────┴────────────────────────────┘
```

---

## 4. External Interface Requirements

### 4.1 User Interfaces

| UI | URL | Description |
|---|---|---|
| Landing Page | beauty.beautynshine.web.id | Public marketing page |
| Login Page | erp.beautynshine.web.id/login | Admin/Manager login |
| POS Terminal | pos.beautynshine.web.id | Kasir interface |
| Dashboard | erp.beautynshine.web.id/dashboard | Owner dashboard |
| API Docs | erp.beautynshine.web.id/docs | Swagger/OpenAPI |

### 4.2 Hardware Interfaces
- Thermal printer (future): USB/Ethernet, ESC/POS protocol
- Barcode scanner (future): USB HID, reads EAN-13/QR

### 4.3 Software Interfaces

| Interface | System | Protocol | Data Format |
|---|---|---|---|
| Database | PostgreSQL 16 | TCP:5432 | SQL |
| BCA VA | BCA API | HTTPS | JSON |
| Midtrans | Midtrans Snap | HTTPS | JSON |
| Email | SMTP server | SMTP | MIME |
| WhatsApp | WA Business API (future) | HTTPS | JSON |

### 4.4 Communication Interfaces

| Interface | Protocol | Port | Encryption |
|---|---|---|---|
| Client → Server | HTTPS | 443 | TLS 1.3 |
| Server → Database | TCP | 5432 | SSL (optional) |
| Server → Payment | HTTPS | 443 | TLS 1.3 |
| Tunnel | QUIC (Cloudflare) | - | TLS |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Requirement | Metric | Target |
|---|---|---|
| NFR-P01 | API response time | < 200ms (p95) |
| NFR-P02 | Page load time | < 2 seconds |
| NFR-P03 | Database query time | < 50ms (p95) |
| NFR-P04 | Concurrent users | 50+ per branch |
| NFR-P05 | Transaction throughput | 100 tx/minute |

### 5.2 Security

| Requirement | Description |
|---|---|
| NFR-S01 | All communication via HTTPS |
| NFR-S02 | Passwords hashed with bcrypt (12 rounds) |
| NFR-S03 | JWT tokens with 30-min expiry |
| NFR-S04 | RBAC for all endpoints |
| NFR-S05 | SQL injection prevention (ORM) |
| NFR-S06 | XSS prevention (sanitization) |
| NFR-S07 | Rate limiting per IP |
| NFR-S08 | Audit log for all mutations |
| NFR-S09 | Secrets in environment variables only |
| NFR-S10 | CORS restricted to known origins |

### 5.3 Reliability

| Requirement | Metric | Target |
|---|---|---|
| NFR-R01 | Uptime | 99.5% |
| NFR-R02 | Recovery Point Objective | 24 hours |
| NFR-R03 | Recovery Time Objective | 4 hours |
| NFR-R04 | Backup frequency | Daily |
| NFR-R05 | Error rate | < 0.1% |

### 5.4 Usability

| Requirement | Description |
|---|---|
| NFR-U01 | POS checkout in ≤ 3 clicks |
| NFR-U02 | Dashboard loads key metrics in ≤ 1 second |
| NFR-U03 | Mobile-responsive (320px minimum) |
| NFR-U04 | Consistent brand identity (Playfair + Inter) |
| NFR-U05 | Error messages in Bahasa Indonesia |
| NFR-U06 | Keyboard shortcuts for POS (future) |

### 5.5 Scalability

| Requirement | Description |
|---|---|
| NFR-SC01 | Stateless API design (horizontal scaling ready) |
| NFR-SC02 | Database connection pooling |
| NFR-SC03 | Static assets via CDN (Cloudflare) |
| NFR-SC04 | Multi-branch data isolation ready |

### 5.6 Maintainability

| Requirement | Description |
|---|---|
| NFR-M01 | Code documentation (docstrings, comments) |
| NFR-M02 | API documentation (OpenAPI/Swagger) |
| NFR-M03 | Database migrations (Alembic) |
| NFR-M04 | Structured logging |
| NFR-M05 | Environment-based configuration |

---

## 6. Data Requirements

### 6.1 Data Entities
See ERD v1.0 for complete entity definitions (16 entities).

### 6.2 Data Retention

| Data Type | Retention Period | Archive Strategy |
|---|---|---|
| Transaction data | 5 years | Compress and archive |
| Audit logs | 2 years | Archive to cold storage |
| Customer data | Active + 2 years after last visit | Anonymize after |
| Session data | 30 days | Auto-cleanup |
| Backup files | 30 days (daily), 12 months (monthly) | S3/cold storage |

### 6.3 Data Migration

| Phase | Source | Target | Method |
|---|---|---|---|
| Staff data | Manual list | STAFF table | CSV import |
| Service catalog | Manual list | SERVICE table | Seed script |
| Customer data | None (fresh start) | CUSTOMER table | Registration flow |
| Historical transactions | Bon kertas | Not migrated | Start fresh |

---

## 7. System Features Traceability

| SRS Feature | BRD Ref | FRD Ref | ERD Entity | API Endpoint |
|---|---|---|---|---|
| F-01 Auth | BR-M01 | AUTH-F01~08 | STAFF | /auth/* |
| F-02 POS | BR-M01 | POS-F01~14 | TRANSACTION, SHIFT, ATTACHMENT | /pos/* |
| F-03 Payment | BR-M02 | PAY-F01~06 | PAYMENT | /payments/* |
| F-04 Booking | BR-S01 | BK-F01~08 | BOOKING | /bookings/* |
| F-05 Staff | BR-M05 | STF-F01~09 | STAFF | /staff/* |
| F-06 Catalog | BR-M05 | PS-F01~08 | PRODUCT, SERVICE | /products, /services |
| F-07 Customer | BR-M06 | CUS-F01~09 | CUSTOMER | /customers/* |
| F-08 Inventory | BR-M08 | INV-F01~06 | INVENTORY_MOVEMENT | /inventory/* |
| F-09 Finance | BR-M07 | FIN-F01~08 | JOURNAL_ENTRY, COA | /finance/* |
| F-10 Dashboard | BR-M03 | RPT-F01~08 | (aggregated) | /dashboard/*, /reports/* |
| F-11 Loyalty | BR-S02 | CUS-F05~09 | LOYALTY_TRANSACTION | /loyalty/* |
| F-12 Audit | - | AUD-F01~04 | AUDIT_LOG | (automatic) |

---

## 8. Verification

### 8.1 Test Strategy

| Level | Scope | Tool | Target |
|---|---|---|---|
| Unit | Individual functions | pytest | 80% coverage |
| Integration | Module interactions | pytest + httpx | Critical paths |
| System | End-to-end flows | pytest + TestClient | All use cases |
| Acceptance | Business scenarios | Manual + scripts | All BRD requirements |

### 8.2 Acceptance Criteria

| Feature | Acceptance Criteria |
|---|---|
| F-01 Auth | Login → JWT token → Access protected endpoint |
| F-02 POS | Add items → Cart → Payment → Receipt → Print/WA → DB record |
| F-03 Payment | Generate VA → Customer pays → Callback → Status update |
| F-04 Booking | Select service → Choose time → Confirm → Notification |
| F-05 Dashboard | View revenue → Filter by date → Export PDF |

---

## 9. Appendices

### 9.1 Glossary
See Section 1.3

### 9.2 Analysis Models
- ERD: See ERD v1.0
- Data Flow: See FRD Section 3
- BPMN: See BRD Section 5

### 9.3 Issues List

| # | Issue | Status | Owner |
|---|---|---|---|
| I-01 | VPS needs upgrade | Open | Owner |
| I-02 | BCA VA account not yet approved | Open | Owner |
| I-03 | Midtrans account pending | Open | Owner |

---

*Document ini harus di-review dan di-approve oleh stakeholder sebelum development phase dimulai.*
