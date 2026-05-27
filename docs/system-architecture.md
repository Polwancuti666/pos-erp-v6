# System Architecture

## POS-ERP Integration Engine V6

---

## 1. Architectural Style

**Modular Monolith with Clean Architecture Layers**

The system is designed as a single deployable unit with clear internal module boundaries. Each module encapsulates a specific domain concern and communicates through well-defined interfaces.

---

## 2. Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                           │
│  Browser / POS Terminal / Mobile Device                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI GATEWAY LAYER                     │
│  Routes, Request Validation, Response Formatting             │
│  fastapi_app.py                                             │
├─────────────────────────────────────────────────────────────┤
│                   MIDDLEWARE STACK                           │
│  RequestID → Timing → CORS → BodySizeLimit → RateLimit →   │
│  CSRF → SecurityHeaders → Auth → Audit → ErrorHandler      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               APPLICATION SERVICE LAYER                     │
│  api.py (AppService)                                        │
│  • complete_offline_checkout()                              │
│  • authorize()                                              │
│  • owner_dashboard()                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   DOMAIN LOGIC LAYER                         │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Checkout │ │ Payment  │ │Inventory │ │  Treatment   │   │
│  │          │ │          │ │          │ │              │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │Accounting│ │  Sync    │ │  Auth    │ │  Reconcile   │   │
│  │          │ │          │ │          │ │              │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │ Staff    │ │ Security │ │Document  │ │  Correction  │   │
│  │  Lock    │ │          │ │ Finalize │ │              │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER                          │
│  persistence.py (InMemoryRepository + UnitOfWork)           │
│  postgresql.py (PostgreSQLSettings, async driver)           │
│  migrations.py (MigrationRunner)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   EXTERNAL SYSTEMS                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────┐    │
│  │ BCA VA   │ │ Midtrans │ │  Cloudflare Tunnel       │    │
│  │          │ │          │ │                          │    │
│  └──────────┘ └──────────┘ └──────────────────────────┘    │
│  ┌──────────┐ ┌──────────┐                                 │
│  │ ERP API  │ │PostgreSQL│                                 │
│  │          │ │ Database │                                 │
│  └──────────┘ └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Middleware Stack

Request processing follows a strict middleware pipeline:

| Order | Middleware | Responsibility |
|---|---|---|
| 1 | RequestID | Assign unique request identifier for tracing |
| 2 | Timing | Measure request duration |
| 3 | CORS | Cross-origin resource sharing policy |
| 4 | BodySizeLimit | Reject oversized request bodies |
| 5 | RateLimit | Throttle excessive requests per client |
| 6 | CSRF | Cross-site request forgery protection |
| 7 | SecurityHeaders | Set security-related HTTP headers |
| 8 | Auth | Authenticate and authorize requests |
| 9 | Audit | Log request/response for audit trail |
| 10 | ErrorHandler | Catch and format unhandled exceptions |

---

## 4. Module Map

### Core Domain Modules

| Module | File | Responsibility |
|---|---|---|
| Checkout | checkout.py | Offline/online transaction processing |
| Payment | payment.py | Payment intent lifecycle, verification |
| Payment Providers | payment_providers.py | BCA VA and Midtrans adapters |
| Inventory | inventory.py | Stock movement tracking |
| Treatment | treatment.py | Service management, staff reassignment |
| Accounting | accounting.py | Journal posting, COA mapping |
| Reconciliation | reconciliation.py | Shift closing, variance detection |
| Auth | auth.py | ERP authentication |
| POS Auth | pos_auth.py | Staff PIN authentication, shift management |
| Staff Lock | staff_lock.py | Resource locking with timeout |
| Sync | sync.py | Outbox queue, retry, escalation |
| Sync Control | sync_control.py | Connectivity, approval, branch cache |
| Document Finalization | document_finalization.py | ERP document finalization |
| Document Numbering | document_numbering.py | Sequential document number generation |
| Period Lock | period_lock.py | Accounting period protection |
| Correction | correction.py | Transaction correction decisions |
| Exception Queue | exception_queue.py | Error handling with SLA management |
| Security | security.py | Encryption, HMAC verification |
| Permissions | permissions.py | Role-based access control |
| Dashboard | dashboard.py | Owner dashboard, branch snapshots |
| Observability | observability.py | Health checks, metrics |

### Infrastructure Modules

| Module | File | Responsibility |
|---|---|---|
| Persistence | persistence.py | In-memory repository, unit of work |
| PostgreSQL | postgresql.py | Database configuration, connection |
| Migrations | migrations.py | Schema migration execution |
| Deployment | deployment.py | Deployment manifest validation |
| Adapters | adapters.py | External service adapters |
| Config | config.py | Application configuration from environment |
| Beauty UI | beauty_ui.py | HTML dashboard rendering |

---

## 5. External Integrations

### BCA Virtual Account

- **Adapter**: `BcaVirtualAccountAdapter` (payment_providers.py)
- **Protocol**: REST API with HMAC-SHA256 signature
- **Purpose**: Bank transfer payment via virtual account numbers

### Midtrans

- **Adapter**: `MidtransAdapter` (payment_providers.py)
- **Protocol**: REST API with SHA-512 signature verification
- **Purpose**: QRIS payment processing, callback verification

### Cloudflare Tunnel

- **Purpose**: Secure tunnel from POS terminals to API server
- **Configuration**: Managed via deployment manifest
- **Benefit**: No inbound firewall rules required

### ERP Integration

- **Adapter**: `ErpAdapter` (adapters.py)
- **Purpose**: Sync transactions, post journals, escalate exceptions

---

## 6. Security Layers

The system implements 5 security layers as defined in the Software Design Document:

```
┌─────────────────────────────────────────────┐
│  Layer 5: Audit & Monitoring                │
│  • Request/response logging                 │
│  • Metrics collection                       │
│  • Exception queue monitoring               │
├─────────────────────────────────────────────┤
│  Layer 4: Application Security              │
│  • CSRF protection                          │
│  • Security headers                         │
│  • Rate limiting                            │
│  • Body size limits                         │
├─────────────────────────────────────────────┤
│  Layer 3: Authorization                     │
│  • RBAC with 5 roles                        │
│  • 11 granular actions                      │
│  • authorize_action() enforcement           │
├─────────────────────────────────────────────┤
│  Layer 2: Authentication                    │
│  • ERP login (auth.py)                      │
│  • POS staff PIN (pos_auth.py)              │
│  • Device binding (sync_control.py)         │
├─────────────────────────────────────────────┤
│  Layer 1: Data Security                     │
│  • EncryptionService (XOR keystream)        │
│  • HMAC-SHA256 message authentication       │
│  • Secure payment callback verification     │
└─────────────────────────────────────────────┘
```

---

## 7. Data Flow Patterns

### Synchronous Flow (Local Operations)
```
Client → FastAPI → AppService → Domain Logic → InMemoryRepository → Response
```

### Asynchronous Flow (ERP Sync)
```
Transaction → SyncQueue.Enqueue → Outbox Table → run_once() → ERP API
                                      │
                                      └── Retry (3x) → Escalate
```

### Offline-First Pattern
```
POS Terminal → Local Transaction → Queue for Sync
      │                                    │
      └── Immediate Response    └── When Online → Sync to ERP
```

---

## 8. Configuration

All configuration is managed through environment variables via `AppConfig.from_env()`:

- Database connection strings
- Payment provider credentials
- Encryption keys
- Sync intervals and retry limits
- Rate limiting thresholds
- Feature flags

See [deployment-guide.md](deployment-guide.md) for complete environment variable reference.

---

## 9. Deployment Architecture

```
┌─────────────────────────────────────────────┐
│              Docker Compose Stack            │
│                                             │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │  PostgreSQL   │    │  POS-ERP API     │   │
│  │  (port 5432)  │◄───│  (FastAPI/uvicorn)│   │
│  └──────────────┘    └────────┬─────────┘   │
│                               │             │
└───────────────────────────────┼─────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  Cloudflare Tunnel   │
                     │  (secure ingress)    │
                     └─────────────────────┘
```
