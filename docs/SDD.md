# 🏗️ System Design Document (SDD)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | SDD v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **Reference** | BRD v1.0, FRD v1.0, TRD v1.0, SRS v1.0, ERD v1.0, QRD v1.0 |
| **Status** | DRAFT — Pending Stakeholder Approval |

---

## 1. Document Purpose

SDD mendefinisikan desain teknis sistem Beauty & Shine secara komprehensif — arsitektur, komponen, alur data, desain pattern, dan keputusan teknis (design decisions) yang diambil. Dokumen ini menjadi panduan utama bagi developer saat implementasi.

---

## 2. Design Principles

### 2.1 Core Principles

| # | Principle | Description | Application |
|---|---|---|---|
| DP-01 | **Simplicity** | Desain sesederhana mungkin, hindari over-engineering | Monolith first, microservices later |
| DP-02 | **Separation of Concerns** | Setiap module punya tanggung jawab tunggal | Domain-driven module boundaries |
| DP-03 | **Fail Fast** | Deteksi error sedini mungkin | Input validation di edge layer |
| DP-04 | **Convention over Configuration** | Kurangi boilerplate, gunakan defaults | Naming conventions, auto-mapping |
| DP-05 | **Defense in Depth** | Multiple layers of security | Auth → RBAC → Validation → Audit |
| DP-06 | **Observable by Default** | Setiap operasi ter-log dan ter-metrik | Structured logging, health checks |
| DP-07 | **Reversible Decisions** | Pilih opsi yang mudah diubah | Feature flags, modular design |

### 2.2 Architecture Decision Records (ADR)

#### ADR-01: Monolith vs Microservices
```
Decision: Modular Monolith
Context:  Single developer, MVP timeline 8 minggu, 1-2 cabang
Options:
  A) Microservices — complex infra, overkill untuk scale ini
  B) Modular Monolith — simple deploy, clear boundaries, future split ready
  C) Simple Monolith — fast tapi sulit di-maintain
Chosen: B — Modular Monolith
Consequences:
  (+) Single deployment, simple debugging
  (+) Clear module boundaries (pos, booking, payment, finance)
  (-) Must enforce module boundaries manually
  (-) Scale-out harder (but not needed at this scale)
```

#### ADR-02: Sync vs Async Processing
```
Decision: Synchronous with async for external calls
Context:  POS needs instant response, payment callbacks are async
Options:
  A) All sync — simple, blocking
  B) Sync core + async external — balanced
  C) Full async (Celery/Redis) — complex, overkill
Chosen: B — Sync core + async for payment gateway
Consequences:
  (+) POS transactions are instant
  (+) Payment callbacks handled without blocking
  (-) Need httpx async for external calls
  (-) Background tasks via FastAPI BackgroundTasks (not Celery)
```

#### ADR-03: Database ORM vs Raw SQL
```
Decision: SQLAlchemy 2.0 ORM with selective raw SQL
Context:  Complex queries (reports) may need optimization
Options:
  A) Pure ORM — type-safe, slower for complex queries
  B) ORM + raw SQL for reports — balanced
  C) Pure raw SQL — fast, no type safety
Chosen: B — ORM for CRUD, raw SQL for reports/analytics
Consequences:
  (+) Developer productivity with ORM
  (+) Performance optimization for dashboards
  (-) Must maintain both patterns
```

#### ADR-04: Authentication Strategy
```
Decision: JWT (stateless) + bcrypt
Context:  POS terminals, web dashboard, API access
Options:
  A) Session-based (server state) — needs Redis
  B) JWT (stateless) — no server state, simple
  C) OAuth2 with external provider — overkill
Chosen: B — JWT with short-lived access + refresh tokens
Consequences:
  (+) No Redis dependency for auth
  (+) Works across multiple frontends
  (-) Cannot revoke tokens (mitigated by short expiry)
  (-) Token size larger than session ID
```

#### ADR-05: Frontend Approach
```
Decision: Server-rendered HTML + Vanilla JS (no framework)
Context:  Small team, simple UI, fast development
Options:
  A) React/Vue SPA — complex build, overkill
  B) HTMX + Jinja2 — modern, simple
  C) Vanilla HTML/JS — simplest, no build step
Chosen: C — Vanilla HTML/JS (with future HTMX option)
Consequences:
  (+) No build toolchain needed
  (+) Fast page loads, simple debugging
  (-) More manual DOM manipulation
  (-) Less reusable components
```

#### ADR-06: Payment Gateway Strategy
```
Decision: Dual gateway (BCA VA + Midtrans)
Context:  Indonesian market, need bank transfer + QRIS
Options:
  A) Single gateway (Midtrans only) — simpler
  B) Dual gateway (BCA + Midtrans) — more options
  C) Manual payment only — no integration
Chosen: B — Dual gateway for payment flexibility
Consequences:
  (+) Customer has multiple payment options
  (+) BCA VA for direct bank transfer (lower fee)
  (-) Must handle two callback formats
  (-) More complex reconciliation
```

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                  │
│                                                                         │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐    │
│   │  Landing  │    │    POS    │    │    ERP    │    │ Dashboard │    │
│   │  (Public) │    │  (Kasir)  │    │  (Admin)  │    │  (Owner)  │    │
│   │           │    │           │    │           │    │           │    │
│   │  HTML/CSS │    │ HTML/CSS/ │    │ HTML/CSS/ │    │ HTML/CSS/ │    │
│   │  Vanilla  │    │   JS      │    │   JS      │    │   JS      │    │
│   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘    │
│         │                │                │                │           │
└─────────┼────────────────┼────────────────┼────────────────┼───────────┘
          │                │                │                │
          │     HTTPS (Cloudflare Tunnel - QUIC)             │
          │                │                │                │
┌─────────┼────────────────┼────────────────┼────────────────┼───────────┐
│         ▼                ▼                ▼                ▼           │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    GATEWAY / ROUTER LAYER                       │  │
│  │                                                                 │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │  │
│  │  │ Host    │  │ CORS    │  │ Rate    │  │ Request │          │  │
│  │  │ Router  │  │ Middleware│  │ Limiter │  │ ID      │          │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                │                                      │
│  ┌─────────────────────────────┼─────────────────────────────────────┐│
│  │                    APPLICATION LAYER                              ││
│  │                             │                                     ││
│  │  ┌─────────┐  ┌─────────┐  │  ┌─────────┐  ┌─────────┐         ││
│  │  │  AUTH   │  │   POS   │◄─┘  │ BOOKING │  │ PAYMENT │         ││
│  │  │ Module  │  │ Module  │     │ Module  │  │ Module  │         ││
│  │  └─────────┘  └─────────┘     └─────────┘  └─────────┘         ││
│  │                                                                  ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           ││
│  │  │ STAFF   │  │PRODUCT/ │  │CUSTOMER │  │FINANCE  │           ││
│  │  │ Module  │  │SERVICE  │  │& LOYALTY│  │ Module  │           ││
│  │  └─────────┘  │ Module  │  │ Module  │  └─────────┘           ││
│  │               └─────────┘  └─────────┘                         ││
│  │                                                                  ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                        ││
│  │  │INVENTORY│  │DASHBOARD│  │  AUDIT  │                        ││
│  │  │ Module  │  │ Module  │  │ Module  │                        ││
│  │  └─────────┘  └─────────┘  └─────────┘                        ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                │                                      │
│  ┌─────────────────────────────┼─────────────────────────────────────┐│
│  │                    DOMAIN LAYER (Business Logic)                  ││
│  │                             │                                     ││
│  │  ┌─────────┐  ┌─────────┐  │  ┌─────────┐  ┌─────────┐         ││
│  │  │ Shift   │  │ Booking │  │  │ Loyalty │  │ Journal │         ││
│  │  │ Domain  │  │ Domain  │  │  │ Domain  │  │ Domain  │         ││
│  │  └─────────┘  └─────────┘  │  └─────────┘  └─────────┘         ││
│  │                             │                                     ││
│  │  ┌─────────┐  ┌─────────┐  │  ┌─────────┐                      ││
│  │  │ Staff   │  │ Payment │◄─┘  │ Receipt │                      ││
│  │  │ Lock    │  │ Domain  │     │ Domain  │                      ││
│  │  └─────────┘  └─────────┘     └─────────┘                      ││
│  └──────────────────────────────────────────────────────────────────┘│
│                                │                                      │
│  ┌─────────────────────────────┼─────────────────────────────────────┐│
│  │                    INFRASTRUCTURE LAYER                           ││
│  │                             │                                     ││
│  │  ┌─────────┐  ┌─────────┐  │  ┌─────────┐  ┌─────────┐         ││
│  │  │Database │  │ Payment │  │  │   WA    │  │ Printer │         ││
│  │  │ (PG16)  │  │Gateway  │  │  │  API    │  │ (ESC/POS│         ││
│  │  └─────────┘  └─────────┘  │  └─────────┘  └─────────┘         ││
│  │                             │                                     ││
│  │  ┌─────────┐  ┌─────────┐  │                                    ││
│  │  │  File   │  │ Logging │◄─┘                                    ││
│  │  │ Storage │  │ System  │                                        ││
│  │  └─────────┘  └─────────┘                                        ││
│  └──────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Layer Descriptions

| Layer | Responsibility | Key Components |
|---|---|---|
| **Client** | UI rendering, user interaction | HTML, CSS, Vanilla JS |
| **Gateway** | Request routing, security, rate limiting | FastAPI middleware stack |
| **Application** | Business orchestration, API endpoints | FastAPI routers (11 modules) |
| **Domain** | Pure business logic, no I/O | Domain models, validation rules |
| **Infrastructure** | External I/O, persistence, integrations | PostgreSQL, Payment API, WA API, Printer |

---

## 4. Component Design

### 4.1 Module Dependency Graph

```
                    ┌─────────┐
                    │  AUTH   │ (foundation — all modules depend on)
                    └────┬────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────┴────┐     ┌─────┴─────┐    ┌─────┴─────┐
   │  STAFF  │     │   POS     │    │  BOOKING  │
   └────┬────┘     └─────┬─────┘    └─────┬─────┘
        │                │                │
        │          ┌─────┴─────┐          │
        │          │  PAYMENT  │◄─────────┘
        │          └─────┬─────┘
        │                │
   ┌────┴────┐     ┌─────┴─────┐     ┌─────────┐
   │PRODUCT/ │     │ CUSTOMER  │     │FINANCE  │
   │ SERVICE │     │& LOYALTY  │     │(Journal)│
   └────┬────┘     └─────┬─────┘     └─────┬───┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                   ┌─────┴─────┐
                   │INVENTORY  │
                   └─────┬─────┘
                         │
                   ┌─────┴─────┐
                   │ DASHBOARD │ (read-only aggregation)
                   └─────┬─────┘
                         │
                   ┌─────┴─────┐
                   │  AUDIT    │ (cross-cutting concern)
                   └───────────┘
```

### 4.2 Module Internal Structure

Setiap module mengikuti struktur konsisten:

```
src/pos_erp/
├── modules/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── router.py          # API endpoints
│   │   ├── service.py         # Business logic
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic request/response
│   │   ├── repository.py      # Database operations
│   │   └── exceptions.py      # Module-specific errors
│   │
│   ├── pos/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── receipt.py         # Receipt generation (ESC/POS, PDF)
│   │   └── exceptions.py
│   │
│   ├── payment/
│   │   ├── __init__.py
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── bca_gateway.py     # BCA VA integration
│   │   ├── midtrans_gateway.py # Midtrans integration
│   │   └── exceptions.py
│   │
│   └── ... (other modules follow same pattern)
│
├── shared/
│   ├── __init__.py
│   ├── database.py            # SQLAlchemy engine, session
│   ├── security.py            # JWT, password hashing
│   ├── middleware.py           # Auth, CORS, rate limit
│   ├── exceptions.py          # Global exception handlers
│   ├── logging.py             # Structured logging
│   └── config.py              # Environment configuration
│
├── static/                    # Frontend assets
│   ├── index.html             # Landing page
│   ├── login.html             # Login page
│   ├── pos_index.html         # POS terminal
│   └── dashboard.html         # Dashboard
│
├── main.py                    # FastAPI app factory
└── config.py                  # Settings loader
```

### 4.3 Component Interaction: POS Transaction

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ POS UI   │────→│ POS      │────→│ POS      │────→│ Payment  │
│ (JS)     │     │ Router   │     │ Service  │     │ Service  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                      │                  │
                                      │                  ▼
                                      │           ┌──────────┐
                                      │           │ BCA/Mid  │
                                      │           │ Gateway  │
                                      │           └──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                  │
              ┌─────┴─────┐    ┌─────┴─────┐    ┌─────┴─────┐
              │ Inventory │    │  Finance  │    │  Receipt  │
              │ Service   │    │  Service  │    │  Service  │
              └───────────┘    └───────────┘    └───────────┘
                    │                 │                  │
                    ▼                 ▼                  ▼
              ┌──────────┐    ┌──────────┐    ┌──────────┐
              │ Stock    │    │ Journal  │    │ Printer/ │
              │ Update   │    │ Entry    │    │ WhatsApp │
              └──────────┘    └──────────┘    └──────────┘
```

---

## 5. Data Architecture

### 5.1 Database Design Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL 16                             │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   pos_erp   │  │  Extensions │  │   Schemas   │        │
│  │   (main DB) │  │  - uuid-ossp│  │   - public  │        │
│  │             │  │  - pgcrypto │  │   - audit   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  Tables (21):                                               │
│  ─────────────                                              │
│  Core:       branch, staff, customer, shift                 │
│  Catalog:    product, service                               │
│  Transaction:booking, transaction, transaction_item,        │
│              payment                                        │
│  Finance:    coa, journal_entry, journal_line               │
│  Support:    inventory_movement, loyalty_transaction,       │
│              audit_log, room, promo, notification,          │
│              attachment, supplier                           │
│                                                             │
│  Indexes: 30+ (see ERD for details)                        │
│  Constraints: FK, UNIQUE, CHECK, NOT NULL                  │
│  Triggers: updated_at auto-touch (all tables)              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Data Access Patterns

| Pattern | Implementation | Use Case |
|---|---|---|
| **CRUD** | SQLAlchemy ORM | All entity operations |
| **Read-heavy** | Query optimization + indexes | Dashboard, reports |
| **Aggregation** | Raw SQL with GROUP BY | Revenue reports, analytics |
| **Pagination** | OFFSET/LIMIT with cursor option | List endpoints |
| **Full-text Search** | PostgreSQL `ts_vector` | Customer/product search |
| **Audit Trail** | Application-level logging | All mutations |

### 5.3 Data Consistency Strategy

```
┌─────────────────────────────────────────────────────┐
│              CONSISTENCY MODEL                       │
│                                                     │
│  POS Transaction:                                   │
│  ┌─────────────────────────────────────────────┐   │
│  │ BEGIN TRANSACTION                           │   │
│  │   1. Create TRANSACTION record              │   │
│  │   2. Create TRANSACTION_ITEM records        │   │
│  │   3. Update PRODUCT stock_qty               │   │
│  │   4. Create PAYMENT record                  │   │
│  │   5. Create JOURNAL_ENTRY + JOURNAL_LINE    │   │
│  │   6. Create LOYALTY_TRANSACTION (if member) │   │
│  │   7. Create ATTACHMENT (receipt)            │   │
│  │   8. Create NOTIFICATION (WhatsApp)         │   │
│  │ COMMIT                                      │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  If ANY step fails → ROLLBACK all                   │
│  Exception: Payment gateway (external) → retry      │
└─────────────────────────────────────────────────────┘
```

---

## 6. Integration Architecture

### 6.1 Integration Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTEGRATION LANDSCAPE                         │
│                                                                 │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐                  │
│  │ Beauty  │────→│ FastAPI │────→│ BCA API │ (Virtual Account) │
│  │ & Shine │     │ Backend │     └─────────┘                  │
│  │  POS    │     │         │     ┌─────────┐                  │
│  └─────────┘     │         │────→│ Midtrans│ (QRIS/Card)      │
│                  │         │     └─────────┘                  │
│  ┌─────────┐     │         │     ┌─────────┐                  │
│  │Customer │────→│         │────→│ Fonnte  │ (WhatsApp)       │
│  │ Browser │     │         │     └─────────┘                  │
│  └─────────┘     │         │     ┌─────────┐                  │
│                  │         │────→│ Thermal │ (Receipt Print)  │
│  ┌─────────┐     │         │     │ Printer │                  │
│  │Cloudflare────→│         │     └─────────┘                  │
│  │ Tunnel  │     │         │                                  │
│  └─────────┘     └────┬────┘                                  │
│                       │                                       │
│                  ┌────┴────┐                                  │
│                  │PostgreSQL│                                  │
│                  │   16    │                                  │
│                  └─────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Integration Patterns

| Integration | Pattern | Retry | Fallback |
|---|---|---|---|
| BCA VA | Request-Reply (sync) | 3x with backoff | Mark pending, manual check |
| Midtrans | Request-Reply + Webhook | 3x with backoff | Mark pending, manual check |
| WhatsApp | Fire-and-Forget (async) | 3x with backoff | Log failure, offer print |
| Printer | Direct (sync) | 1x retry | Browser print fallback |
| Database | Connection pool | Auto-reconnect | Queue writes |

### 6.3 API Gateway Middleware Stack

```python
# Middleware execution order (outer → inner)
middleware_stack = [
    RequestIDMiddleware,      # Assign unique request ID
    TimingMiddleware,         # Track request duration
    CORSMiddleware,           # Handle CORS preflight
    BodySizeLimitMiddleware,  # Enforce body/query size limits (1MB API, 10MB upload)
    RateLimitMiddleware,      # Per-IP rate limiting
    CSRFMiddleware,           # Double-submit cookie CSRF protection
    SecurityHeadersMiddleware,# Add security headers (HSTS, CSP, X-Frame-Options)
    AuthenticationMiddleware, # JWT validation
    AuditMiddleware,          # Log all mutations
    ErrorHandlerMiddleware,   # Global exception handler
]
```

---

## 7. Security Architecture

### 7.1 Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY DEFENSE IN DEPTH                 │
│                                                             │
│  Layer 1: NETWORK                                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Cloudflare WAF + DDoS Protection                    │   │
│  │ HTTPS-only (TLS 1.3) via Universal SSL              │   │
│  │ Cloudflare Tunnel (no public ports on VPS)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Layer 2: APPLICATION                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ CORS: Whitelist origins only                        │   │
│  │ Rate Limiting: Per-IP (100 req/min)                 │   │
│  │ CSRF: Double-submit cookie pattern                  │   │
│  │ Input Validation: Pydantic schemas (strict mode)    │   │
│  │ Body Size Limits: 1MB API / 10MB uploads            │   │
│  │ Query Limits: max 10 params, 500 chars each         │   │
│  │ Security Headers: HSTS, CSP, X-Frame-Options        │   │
│  │   (custom Python middleware, equivalent to Helmet)   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Layer 3: AUTHENTICATION                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ JWT: HS256, 30-min access, 7-day refresh            │   │
│  │ Password: bcrypt (12 rounds)                        │   │
│  │ PIN: bcrypt (12 rounds)                             │   │
│  │ Brute Force: Lock after 3 failed attempts           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Layer 4: AUTHORIZATION                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ RBAC: 5 roles (super_admin, owner, manager,         │   │
│  │        kasir, therapist)                             │   │
│  │ Endpoint-level permission checks                    │   │
│  │ Data-level: branch isolation                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Layer 5: DATA                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Passwords: Never stored in plaintext                │   │
│  │ Secrets: Environment variables only                 │   │
│  │ SQL: ORM (SQLAlchemy) prevents injection            │   │
│  │ Audit: All mutations logged                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Authentication Flow

```
┌──────────┐                    ┌──────────┐                ┌──────────┐
│  Client  │                    │  FastAPI │                │ Database │
└────┬─────┘                    └────┬─────┘                └────┬─────┘
     │                               │                           │
     │  POST /auth/login             │                           │
     │  {username, password}         │                           │
     │──────────────────────────────→│                           │
     │                               │  SELECT user WHERE        │
     │                               │  username = ?             │
     │                               │──────────────────────────→│
     │                               │                           │
     │                               │  user record              │
     │                               │←──────────────────────────│
     │                               │                           │
     │                               │  bcrypt.verify(password,  │
     │                               │    user.password_hash)    │
     │                               │                           │
     │                               │  IF valid:                │
     │                               │    generate JWT           │
     │                               │    record audit log       │
     │                               │  ELSE:                    │
     │                               │    increment fail_count   │
     │                               │    IF fail >= 3: lock     │
     │                               │                           │
     │  {token, role, redirect}      │                           │
     │←──────────────────────────────│                           │
     │                               │                           │
     │  GET /dashboard               │                           │
     │  Authorization: Bearer <jwt>  │                           │
     │──────────────────────────────→│                           │
     │                               │  validate JWT             │
     │                               │  check role permission    │
     │                               │  execute query            │
     │  {data}                       │                           │
     │←──────────────────────────────│                           │
```

---

## 8. Sequence Diagrams

### 8.1 POS Transaction (Complete Flow)

```
  Kasir        POS UI      POS Router    POS Service    Payment    Inventory    Finance     Receipt
    │             │             │             │            │           │            │           │
    │ Scan/PIN    │             │             │            │           │            │           │
    │────────────→│             │             │            │           │            │           │
    │             │ POST /pos   │             │            │           │            │           │
    │             │ /auth       │             │            │           │            │           │
    │             │────────────→│             │            │           │            │           │
    │             │             │  validate   │            │           │            │           │
    │             │             │  create     │            │           │            │           │
    │             │             │  SHIFT      │            │           │            │           │
    │             │  {shift_id} │             │            │           │            │           │
    │             │←────────────│             │            │           │            │           │
    │             │             │             │            │           │            │           │
    │ Select item │             │             │            │           │            │           │
    │────────────→│             │             │            │           │            │           │
    │             │ Add to cart │             │            │           │            │           │
    │             │ (client)    │             │            │           │            │           │
    │             │             │             │            │           │            │           │
    │ Click Pay   │             │             │            │           │            │           │
    │────────────→│             │             │            │           │            │           │
    │             │ POST /pos   │             │            │           │            │           │
    │             │ /transactions             │            │           │            │           │
    │             │────────────→│             │            │           │            │           │
    │             │             │  BEGIN TXN  │            │           │            │           │
    │             │             │────────────→│            │           │            │           │
    │             │             │             │  validate  │           │            │           │
    │             │             │             │  calculate │           │            │           │
    │             │             │             │            │           │            │           │
    │             │             │             │  process   │           │            │           │
    │             │             │             │  payment   │           │            │           │
    │             │             │             │───────────→│           │            │           │
    │             │             │             │  confirmed │           │            │           │
    │             │             │             │←───────────│           │            │           │
    │             │             │             │            │           │            │           │
    │             │             │             │  update    │           │            │           │
    │             │             │             │  stock     │           │            │           │
    │             │             │             │───────────────────────→│            │           │
    │             │             │             │            │           │ done       │           │
    │             │             │             │←───────────────────────│            │           │
    │             │             │             │            │           │            │           │
    │             │             │             │  journal   │           │            │           │
    │             │             │             │  entry     │           │            │           │
    │             │             │             │───────────────────────────────────→│           │
    │             │             │             │            │           │            │ done      │
    │             │             │             │←───────────────────────────────────│           │
    │             │             │             │            │           │            │           │
    │             │             │             │  COMMIT    │           │            │           │
    │             │             │             │            │           │            │           │
    │             │             │  {success,  │            │           │            │           │
    │             │             │  invoice}   │            │           │            │           │
    │             │  {receipt}  │←────────────│            │           │            │           │
    │             │←────────────│             │            │           │            │           │
    │             │             │             │            │           │            │           │
    │ Show options│             │             │            │           │            │           │
    │ [Print][WA] │             │             │            │           │            │           │
    │←────────────│             │             │            │           │            │           │
    │             │             │             │            │           │            │           │
    │ Click Print │             │             │            │           │            │           │
    │────────────→│             │             │            │           │            │           │
    │             │             │             │  ESC/POS   │           │            │           │
    │             │             │             │────────────────────────────────────────────────→│
    │             │             │             │            │           │            │   print   │
    │ Receipt out │             │             │            │           │            │           │
    │←─────────────────────────────────────────────────────────────────────────────────────────│
```

### 8.2 Booking Flow

```
  Customer      Booking UI    Booking Svc    Staff Svc     Notification
    │               │              │             │              │
    │ Select service│              │             │              │
    │──────────────→│              │             │              │
    │               │ GET /booking │             │              │
    │               │ /availability│             │              │
    │               │─────────────→│             │              │
    │               │              │ check staff │              │
    │               │              │────────────→│              │
    │               │              │ {available} │              │
    │               │              │←────────────│              │
    │               │ {slots}      │             │              │
    │               │←─────────────│             │              │
    │               │              │             │              │
    │ Choose slot   │              │             │              │
    │──────────────→│              │             │              │
    │               │ POST /booking│             │              │
    │               │─────────────→│             │              │
    │               │              │ create      │              │
    │               │              │ BOOKING     │              │
    │               │              │             │              │
    │               │              │ send notif  │              │
    │               │              │────────────────────────────→│
    │               │              │             │     sent      │
    │               │              │←────────────────────────────│
    │               │ {confirmed}  │             │              │
    │               │←─────────────│             │              │
    │ Confirmation  │              │             │              │
    │←──────────────│              │             │              │
```

---

## 9. Error Handling Architecture

### 9.1 Error Classification

```
┌─────────────────────────────────────────────────────────────┐
│                    ERROR HIERARCHY                           │
│                                                             │
│  BaseException                                              │
│  └── BeautyShineException (base)                            │
│      ├── AuthenticationError (401)                          │
│      │   ├── InvalidCredentials                             │
│      │   ├── TokenExpired                                   │
│      │   └── AccountLocked                                  │
│      │                                                      │
│      ├── AuthorizationError (403)                           │
│      │   └── InsufficientPermissions                        │
│      │                                                      │
│      ├── ValidationError (400)                              │
│      │   ├── InvalidInput                                   │
│      │   ├── MissingField                                   │
│      │   └── DuplicateEntry                                 │
│      │                                                      │
│      ├── NotFoundError (404)                                │
│      │   ├── ShiftNotFound                                  │
│      │   ├── CustomerNotFound                               │
│      │   └── TransactionNotFound                            │
│      │                                                      │
│      ├── BusinessRuleError (422)                            │
│      │   ├── ShiftNotActive                                 │
│      │   ├── InsufficientStock                              │
│      │   ├── BookingConflict                                │
│      │   ├── PaymentFailed                                  │
│      │   └── PeriodLocked                                   │
│      │                                                      │
│      ├── ExternalServiceError (502)                         │
│      │   ├── PaymentGatewayError                            │
│      │   ├── WhatsAppAPIError                               │
│      │   └── PrinterError                                   │
│      │                                                      │
│      └── SystemError (500)                                  │
│          ├── DatabaseError                                  │
│          └── InternalError                                  │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Error Response Format

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Stok produk 'Facial Cream' tidak mencukupi (tersisa: 2)",
    "details": {
      "product_id": "uuid-xxx",
      "product_name": "Facial Cream",
      "requested": 5,
      "available": 2
    },
    "request_id": "req-uuid-xxx",
    "timestamp": "2026-05-27T14:30:00Z"
  }
}
```

### 9.3 Global Exception Handler

```python
from fastapi import Request
from fastapi.responses import JSONResponse

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging."""
    
    request_id = getattr(request.state, "request_id", "unknown")
    
    if isinstance(exc, BeautyShineException):
        # Known business error — log as WARNING
        logger.warning(
            exc.message,
            extra={
                "request_id": request_id,
                "error_code": exc.code,
                "status_code": exc.status_code,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
        )
    
    # Unknown error — log as ERROR with full traceback
    logger.error(
        str(exc),
        exc_info=True,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Terjadi kesalahan internal. Silakan coba lagi.",
                "request_id": request_id,
            }
        },
    )
```

---

## 10. Performance Design

### 10.1 Caching Strategy

| Layer | Strategy | TTL | Invalidation |
|---|---|---|---|
| Static assets | Browser cache + Cloudflare CDN | 7 days | Version hash in filename |
| Service catalog | Application cache (dict) | 5 min | On CRUD operation |
| Branch config | Application cache | 30 min | On config change |
| Dashboard data | No cache (real-time) | - | - |
| Session/JWT | No cache (stateless) | - | - |

### 10.2 Database Optimization

```python
# Connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Max persistent connections
    max_overflow=10,       # Extra connections if pool full
    pool_timeout=30,       # Wait timeout for connection
    pool_recycle=3600,     # Recycle connections every hour
    pool_pre_ping=True,    # Verify connection before use
)
```

### 10.3 Query Optimization Patterns

```python
# BAD: N+1 query
transactions = db.query(Transaction).all()
for txn in transactions:
    items = db.query(TransactionItem).filter_by(txn_id=txn.id).all()
    # 1 + N queries!

# GOOD: Eager loading
transactions = (
    db.query(Transaction)
    .options(
        selectinload(Transaction.items),
        selectinload(Transaction.payments),
    )
    .all()
)
# 1-2 queries total!
```

---

## 11. Deployment Architecture

### 11.1 Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS (Ubuntu 24.04)                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Docker Network: pos-erp-network                     │   │
│  │                                                     │   │
│  │  ┌─────────────┐         ┌─────────────┐           │   │
│  │  │ pos-erp-api │         │ pos-erp-pg  │           │   │
│  │  │             │────────→│             │           │   │
│  │  │ FastAPI     │         │ PostgreSQL  │           │   │
│  │  │ :8000       │         │ :5432       │           │   │
│  │  └─────────────┘         └─────────────┘           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ systemd Services                                    │   │
│  │                                                     │   │
│  │  ┌─────────────┐         ┌─────────────┐           │   │
│  │  │ cloudflared │         │ hermes      │           │   │
│  │  │ (tunnel)    │         │ (dashboard) │           │   │
│  │  │ :47474      │         │ :9119       │           │   │
│  │  └─────────────┘         └─────────────┘           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Cron Jobs                                           │   │
│  │  - DB backup (daily 02:00 WIB)                      │   │
│  │  - Health watchdog (every 5 min)                    │   │
│  │  - Log rotation (daily)                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 Request Flow (Production)

```
User Browser
    │
    ▼
Cloudflare CDN (cache static, SSL termination)
    │
    ▼
Cloudflare Tunnel (QUIC, encrypted)
    │
    ▼
cloudflared agent (localhost:8000)
    │
    ▼
Docker: FastAPI (Uvicorn, 4 workers)
    │
    ├──→ Middleware: CORS, Auth, Rate Limit
    │
    ├──→ Router: /pos/*, /auth/*, /booking/*, etc.
    │
    ├──→ Service: Business logic
    │
    └──→ Repository: SQLAlchemy → PostgreSQL
```

---

## 12. Frontend Architecture

### 12.1 Page Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND PAGES                           │
│                                                             │
│  beauty.beautynshine.web.id/                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LANDING PAGE                                        │   │
│  │ - Hero: "Where Radiance Meets Refinement"           │   │
│  │ - Services: 6 interactive cards                      │   │
│  │ - Testimonials: 3 client stories                    │   │
│  │ - Portal: ERP + POS access cards                    │   │
│  │ - CTA: "Begin Your Glow →"                          │   │
│  │ - Nav: Services, Stories, Portal, Sign In           │   │
│  │ - Effects: Scroll animations, shimmer text          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  erp.beautynshine.web.id/login                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ LOGIN PAGE                                          │   │
│  │ - Split-screen: Brand (left) + Form (right)         │   │
│  │ - Username + Password inputs                        │   │
│  │ - Sign In button → POST /auth/login                 │   │
│  │ - Redirect: admin→dashboard, kasir→POS              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  pos.beautynshine.web.id/                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ POS TERMINAL                                        │   │
│  │ - Login: Staff ID + PIN                             │   │
│  │ - Products: 12 service cards (emoji + name + price) │   │
│  │ - Cart: Items, qty +/-, subtotal, tax, total        │   │
│  │ - Checkout: [Print] [WhatsApp] [Done]               │   │
│  │ - Nav: Brand, Staff badge, End Shift                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  erp.beautynshine.web.id/dashboard                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ MEMBER GLOW DASHBOARD                               │   │
│  │ - Hero: Revenue, Transactions, Satisfaction, Staff  │   │
│  │ - Metrics: Facial, Nail, Body, New Members          │   │
│  │ - Activity: Recent transactions table               │   │
│  │ - Quick Actions: POS, API Docs, Staff, Reports      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 Design System

```css
/* Brand Colors (CSS Custom Properties) */
:root {
    --ivory:          #FDFBF7;    /* Background */
    --ivory-warm:     #F8F4ED;    /* Card background */
    --gold:           #C9A96E;    /* Primary accent */
    --gold-light:     #E8D5A8;    /* Hover accent */
    --gold-shimmer:   #D4AF37;    /* Shimmer animation */
    --charcoal:       #2C2C2E;    /* Text primary */
    --charcoal-deep:  #1C1C1E;    /* Dark background */
    --rose:           #C08081;    /* Secondary accent */
    --text-secondary: #6E6E73;    /* Text secondary */
    --text-light:     #AEAEB2;    /* Text muted */
}

/* Typography */
h1, h2, h3, h4 { font-family: 'Playfair Display', serif; }
body            { font-family: 'Inter', sans-serif; }

/* Effects */
.shimmer-text { animation: shimmer 4s linear infinite; }
.animate-on-scroll { opacity: 0; transition: all 0.8s; }
.animate-on-scroll.visible { opacity: 1; transform: translateY(0); }
```

### 12.3 Multi-Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MULTI-PLATFORM POS ARCHITECTURE                  │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │  Android    │  │   iPhone    │  │    iPad     │                │
│  │  Phone      │  │   Safari    │  │   Safari    │                │
│  │  Chrome     │  │             │  │             │                │
│  │  ┌───────┐  │  │  ┌───────┐  │  │  ┌───────┐  │                │
│  │  │  PWA  │  │  │  │  PWA  │  │  │  │  PWA  │  │                │
│  │  │Install│  │  │  │Add HS │  │  │  │Add HS │  │                │
│  │  └───┬───┘  │  │  └───┬───┘  │  │  └───┬───┘  │                │
│  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘                │
│         │                │                │                        │
│         └────────────────┼────────────────┘                        │
│                          │                                         │
│                    ┌─────┴─────┐                                   │
│                    │  SERVICE  │                                   │
│                    │  WORKER   │                                   │
│                    │ (sw.js)   │                                   │
│                    └─────┬─────┘                                   │
│                          │                                         │
│                    ┌─────┴─────┐                                   │
│                    │   FASTAPI │                                   │
│                    │  Backend  │                                   │
│                    │   API     │                                   │
│                    └───────────┘                                   │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐                                 │
│  │  Android    │  │  Desktop    │                                 │
│  │  Tablet     │  │  Browser    │                                 │
│  │  Chrome     │  │  Chrome/    │                                 │
│  │             │  │  Safari/    │                                 │
│  │  ┌───────┐  │  │  Firefox    │                                 │
│  │  │Split  │  │  │             │                                 │
│  │  │View   │  │  │  ┌───────┐  │                                 │
│  │  │(L+R)  │  │  │  │ Full  │  │                                 │
│  │  └───────┘  │  │  │ Grid  │  │                                 │
│  └─────────────┘  │  └───────┘  │                                 │
│                    └─────────────┘                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.4 Responsive Layout Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYOUT BY DEVICE                              │
│                                                                 │
│  MOBILE (320-767px)          TABLET (768-1023px)               │
│  ┌─────────────┐             ┌─────────────┬─────────────┐    │
│  │ Header      │             │             │             │    │
│  ├─────────────┤             │  Products   │    Cart     │    │
│  │ Products    │             │  (Grid)     │   (Panel)   │    │
│  │ (2-col)     │             │             │             │    │
│  ├─────────────┤             │             │             │    │
│  │ Cart (Fixed │             │             │             │    │
│  │  Bottom)    │             │             │             │    │
│  └─────────────┘             └─────────────┴─────────────┘    │
│                                                                 │
│  DESKTOP (1024px+)          iPAD (1024px+ Landscape)           │
│  ┌─────────────┬────────┐   ┌─────────────┬─────────────┐    │
│  │             │        │   │             │             │    │
│  │  Products   │  Cart  │   │  Products   │    Cart     │    │
│  │  (4-col)    │ (Panel)│   │  (4-col)    │   (Panel)   │    │
│  │             │        │   │             │             │    │
│  │             │        │   │             │             │    │
│  └─────────────┴────────┘   └─────────────┴─────────────┘    │
│                                                                 │
│  Key CSS:                                                       │
│  - Mobile: flex-direction: column, cart fixed bottom           │
│  - Tablet: flex-direction: row, side cart (380px)              │
│  - Desktop: grid 4-col, side cart (380px)                      │
│  - iPad: Same as desktop, orientation-aware                    │
│  - Touch: min 44px tap targets, safe-area-inset               │
└─────────────────────────────────────────────────────────────────┘
```

### 12.5 PWA Installation Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PWA INSTALLATION                          │
│                                                             │
│  ANDROID (Chrome)              iOS/iPAD (Safari)            │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ User visits POS  │         │ User visits POS  │         │
│  │ pos.beautynshine │         │ pos.beautynshine │         │
│  │ .web.id          │         │ .web.id          │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│           ▼                            ▼                    │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ Chrome shows     │         │ Safari: tap      │         │
│  │ "Install App"    │         │ Share → Add to   │         │
│  │ banner/bottom    │         │ Home Screen      │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│           ▼                            ▼                    │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ User taps        │         │ User confirms    │         │
│  │ "Install"        │         │ "Add"            │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│           ▼                            ▼                    │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ App icon added   │         │ App icon added   │         │
│  │ to home screen   │         │ to home screen   │         │
│  │ Opens standalone │         │ Opens standalone │         │
│  │ (no browser UI)  │         │ (Safari chrome)  │         │
│  └──────────────────┘         └──────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Monitoring & Observability

### 13.1 Observability Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY                             │
│                                                             │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│  │ Logs    │     │ Metrics │     │ Traces  │              │
│  │ (JSON)  │     │ (system)│     │ (req_id)│              │
│  └────┬────┘     └────┬────┘     └────┬────┘              │
│       │               │               │                    │
│       ▼               ▼               ▼                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Monitoring Dashboard                                │  │
│  │ - CPU / RAM / Disk                                  │  │
│  │ - Request rate / Error rate                         │  │
│  │ - Response time (p50, p95, p99)                     │  │
│  │ - Active connections                                │  │
│  │ - Payment success rate                              │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Alerts:                                                    │
│  - P1: API down → SMS owner                                │
│  - P2: Error rate > 1% → Email manager                     │
│  - P3: Disk > 85% → Daily report                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Testing Architecture

### 14.1 Test Pyramid

```
                    ┌─────────┐
                   /│  E2E    │\        5 tests (critical paths)
                  / │ (Manual)│ \
                 /  └─────────┘  \
                /                  \
               /    ┌─────────┐    \
              /     │Integration│    \   20 tests (API endpoints)
             /      │ (httpx)  │     \
            /       └─────────┘      \
           /                          \
          /        ┌─────────┐         \
         /         │  Unit   │          \  100+ tests (business logic)
        /          │ (pytest)│           \
       /           └─────────┘            \
      /____________________________________\
```

### 14.2 Test Structure

```
tests/
├── conftest.py              # Fixtures (db, client, auth)
├── unit/
│   ├── test_shift.py        # Shift domain logic
│   ├── test_booking.py      # Booking domain logic
│   ├── test_payment.py      # Payment calculations
│   ├── test_receipt.py      # Receipt generation
│   ├── test_loyalty.py      # Loyalty points
│   └── test_journal.py      # Journal entry
├── integration/
│   ├── test_auth_api.py     # Auth endpoints
│   ├── test_pos_api.py      # POS endpoints
│   ├── test_booking_api.py  # Booking endpoints
│   └── test_payment_api.py  # Payment endpoints
└── e2e/
    └── test_pos_flow.py     # Full POS transaction flow
```

---

## 15. Design Decision Summary

| # | Decision | Chosen | Rationale |
|---|---|---|---|
| ADR-01 | Architecture | Modular Monolith | Simple deploy, clear boundaries |
| ADR-02 | Processing | Sync + Async external | POS instant, callbacks async |
| ADR-03 | Data Access | ORM + Raw SQL | Productivity + performance |
| ADR-04 | Auth | JWT stateless | No Redis dependency |
| ADR-05 | Frontend | Vanilla HTML/JS | No build toolchain |
| ADR-06 | Payment | Dual gateway | BCA + Midtrans flexibility |
| ADR-07 | Error Handling | Exception hierarchy | Structured, typed errors |
| ADR-08 | Logging | Structured JSON | Parseable, searchable |
| ADR-09 | Caching | Application dict | Simple, no Redis |
| ADR-10 | Deployment | Docker Compose | Reproducible, isolated |

---

*Document ini adalah panduan arsitektur utama untuk development team. Semua design decisions harus di-review sebelum implementasi.*
