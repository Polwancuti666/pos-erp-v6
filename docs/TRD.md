# 🔧 Technical Requirements Document (TRD)
## Beauty & Shine — POS-ERP Integration Engine V6

---

| Field | Value |
|---|---|
| **Project** | Beauty & Shine — Radiance & Refinement |
| **Document** | TRD v1.0 |
| **Author** | System Analyst |
| **Date** | 2026-05-27 |
| **Reference** | BRD v1.0, FRD v1.0, ERD v1.0, PRD v1.0 |
| **Status** | DRAFT — Pending Stakeholder Approval |

---

## 1. Document Purpose

TRD mendefinisikan kebutuhan teknis (infrastructure, architecture, integrations) yang diperlukan untuk mengimplementasikan sistem Beauty & Shine sesuai BRD dan FRD.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │   CLOUDFLARE    │
                    │   (CDN + SSL)   │
                    │   Free Plan     │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │  CLOUDFLARED    │
                    │  (Tunnel Agent) │
                    │  ea8eabfe-...   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───┐  ┌──────┴──────┐  ┌───┴────────┐
     │ beauty.*   │  │ erp.*       │  │ pos.*      │
     │ (Landing)  │  │ (Login+ERP) │  │ (POS)      │
     │ :8000      │  │ :8000       │  │ :8000      │
     └────────┬───┘  └──────┬──────┘  └───┬────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴────────┐
                    │   FASTAPI APP   │
                    │   (Docker)      │
                    │   Port 8000     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───┐  ┌──────┴──────┐  ┌───┴────────┐
     │ PostgreSQL │  │   Redis     │  │  Payment   │
     │ 16 (Docker)│  │  (Future)   │  │  Gateways  │
     │ Port 5432  │  │  Port 6379  │  │  (External)│
     └────────────┘  └─────────────┘  └────────────┘
```

### 2.2 Container Architecture

```yaml
# Docker Compose Services
services:
  postgres:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: pg_isready

  api:
    build: ./Dockerfile
    ports: ["8000:8000"]
    depends_on: postgres (healthy)
    env_file: .env

  # Future services
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  worker:
    build: ./Dockerfile
    command: celery -A pos_erp.worker worker
    depends_on: [postgres, redis]
```

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| Language | Python | 3.12+ | Core application |
| Framework | FastAPI | 0.100+ | REST API framework |
| ORM | SQLAlchemy | 2.0+ | Database abstraction |
| Migration | Alembic | 1.12+ | Schema migrations |
| Validation | Pydantic | 2.0+ | Data validation |
| Server | Uvicorn | 0.29+ | ASGI server |
| Auth | python-jose | - | JWT token |
| Password | bcrypt | - | Password hashing |
| HTTP Client | httpx | 0.27+ | Async HTTP (payment gateway) |

### 3.2 Frontend

| Component | Technology | Purpose |
|---|---|---|
| HTML | HTML5 | Structure |
| CSS | CSS3 + Custom Properties | Styling |
| JavaScript | Vanilla ES6+ | Interactivity |
| Fonts | Google Fonts (Playfair Display, Inter) | Typography |
| Animations | CSS Animations + Intersection Observer | Scroll effects |
| **PWA** | Web App Manifest + Service Worker | Installable app experience |
| **Responsive** | CSS Grid + Flexbox + Media Queries | Multi-device support |

### 3.2.1 PWA (Progressive Web App) Technical Spec

#### Web App Manifest (`manifest.json`)
```json
{
  "name": "Beauty & Shine POS",
  "short_name": "B&S POS",
  "description": "Point of Sale terminal for Beauty & Shine",
  "start_url": "/pos",
  "display": "standalone",
  "background_color": "#FDFBF7",
  "theme_color": "#C9A96E",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/static/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/static/screenshots/pos-login.png",
      "sizes": "1080x1920",
      "type": "image/png",
      "form_factor": "narrow"
    },
    {
      "src": "/static/screenshots/pos-cart.png",
      "sizes": "1080x1920",
      "type": "image/png",
      "form_factor": "narrow"
    }
  ]
}
```

#### Service Worker (`sw.js`)
```javascript
const CACHE_NAME = 'beauty-shine-v1';
const STATIC_ASSETS = [
  '/pos',
  '/static/css/pos.css',
  '/static/js/pos.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
});

// Fetch: cache-first for static, network-first for API
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/pos/')) {
    // Network-first for API calls
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
  } else {
    // Cache-first for static assets
    event.respondWith(
      caches.match(event.request).then((response) => response || fetch(event.request))
    );
  }
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
});
```

#### POS HTML PWA Integration
```html
<!-- In <head> -->
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#C9A96E">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="B&S POS">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">

<!-- Before </body> -->
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
      .then((reg) => console.log('SW registered:', reg.scope))
      .catch((err) => console.error('SW registration failed:', err));
  }
</script>
```

### 3.2.2 Responsive Design Strategy

#### Mobile-First Approach
```css
/* Base: Mobile (320px+) */
.pos-container {
  display: flex;
  flex-direction: column;
  height: 100dvh; /* dynamic viewport height for mobile */
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
  padding: 0.5rem;
}

.cart-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-height: 40vh;
  overflow-y: auto;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
}

/* Tablet (768px+) */
@media (min-width: 768px) {
  .pos-container {
    flex-direction: row;
  }
  .product-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
  .cart-panel {
    position: static;
    max-height: none;
    width: 380px;
    border-radius: 0;
    box-shadow: none;
    border-left: 1px solid rgba(0,0,0,0.04);
  }
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
  .product-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
  }
}

/* iPad Landscape (1024px+) */
@media (min-width: 1024px) and (orientation: landscape) {
  .product-grid {
    grid-template-columns: repeat(4, 1fr);
  }
  .cart-panel {
    width: 400px;
  }
}
```

#### Touch Optimization
```css
/* Touch-friendly tap targets (min 44x44px per WCAG) */
.product-card {
  min-height: 44px;
  min-width: 44px;
  padding: 1rem;
  touch-action: manipulation; /* prevent double-tap zoom */
}

.qty-btn {
  width: 40px;
  height: 40px;
  font-size: 1.2rem;
}

/* Prevent pull-to-refresh on mobile */
body {
  overscroll-behavior-y: contain;
}

/* Safe area for notched devices */
.pos-header {
  padding-top: env(safe-area-inset-top);
}

.pos-footer {
  padding-bottom: env(safe-area-inset-bottom);
}
```

### 3.2.3 Device-Specific Optimizations

| Device | Optimization |
|---|---|
| **Android Phone** | PWA installable, portrait lock, bottom cart panel |
| **Android Tablet** | Split view (products left, cart right), landscape support |
| **iPhone** | Safari PWA, safe-area-inset, bounce scroll prevention |
| **iPad** | Multi-tasking support, split view, keyboard shortcuts |
| **Desktop** | Full grid layout, hover states, keyboard navigation |

### 3.3 Database

| Component | Technology | Version | Purpose |
|---|---|---|---|
| RDBMS | PostgreSQL | 16 | Primary database |
| Connection | psycopg | 3.3+ | Database driver |
| Pooling | SQLAlchemy pool | - | Connection pooling |

### 3.4 Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| VPS | Ubuntu 24.04 LTS | Server |
| Container | Docker + Docker Compose | Deployment |
| Tunnel | Cloudflare Tunnel | HTTPS + CDN |
| DNS | Cloudflare (Free) | Domain management |
| SSL | Cloudflare (Universal SSL) | HTTPS certificates |

### 3.5 External Services

| Service | Provider | Purpose | Integration |
|---|---|---|---|
| Payment (VA) | BCA | Virtual Account | REST API |
| Payment (QRIS) | Midtrans | QRIS, Card, Transfer | Snap API |
| Notification | WhatsApp Business API | Booking reminder | REST API (future) |
| Email | SMTP (any provider) | Password reset | SMTP |

---

## 4. Infrastructure Requirements

### 4.1 VPS Specifications

| Resource | Current | Minimum | Recommended |
|---|---|---|---|
| vCPU | 1 | 2 | 4 |
| RAM | 961 MB | 4 GB | 8 GB |
| Disk | 20 GB (11 GB free) | 40 GB SSD | 80 GB SSD |
| OS | Ubuntu 24.04 | Ubuntu 24.04 | Ubuntu 24.04 |
| Bandwidth | 1 TB | 2 TB | 4 TB |

### 4.2 Network Architecture

```
Internet
    │
    ▼
Cloudflare (CDN + WAF + SSL)
    │
    ▼ (Tunnel - QUIC)
VPS (beautynshine.web.id)
    │
    ├── Cloudflared Agent (systemd)
    ├── Hermes Dashboard (:9119)
    ├── Hermes API Server (:8642)
    └── Docker Network
        ├── FastAPI (:8000)
        └── PostgreSQL (:5432 internal)
```

### 4.3 DNS Configuration

| Subdomain | Type | Target | Purpose |
|---|---|---|---|
| beauty.beautynshine.web.id | CNAME | tunnel | Landing page |
| erp.beautynshine.web.id | CNAME | tunnel | ERP + Login |
| pos.beautynshine.web.id | CNAME | tunnel | POS Terminal |
| dashboard.beautynshine.web.id | CNAME | tunnel | Hermes Dashboard |
| api.beautynshine.web.id | CNAME | tunnel | Hermes API |

---

## 5. Database Technical Requirements

### 5.1 PostgreSQL Configuration

```ini
# postgresql.conf optimizations
max_connections = 100
shared_buffers = 256MB          # 25% of RAM
effective_cache_size = 768MB    # 75% of RAM
work_mem = 4MB
maintenance_work_mem = 128MB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1          # SSD
effective_io_concurrency = 200  # SSD
```

### 5.2 Database Migrations Strategy

```
alembic/
├── versions/
│   ├── 001_initial_schema.py
│   ├── 002_add_booking_module.py
│   ├── 003_add_payment_tables.py
│   ├── 004_add_loyalty_tables.py
│   └── 005_add_audit_log.py
├── env.py
└── script.py.mako
```

### 5.3 Backup Strategy

| Type | Frequency | Retention | Method |
|---|---|---|---|
| Full backup | Daily (02:00 WIB) | 30 days | pg_dump → compressed file |
| WAL archive | Continuous | 7 days | pg_basebackup |
| Manual backup | Before migration | Until verified | pg_dump |

### 5.4 Index Strategy

```sql
-- Critical indexes for performance
CREATE INDEX idx_transaction_created ON transactions(created_at);
CREATE INDEX idx_transaction_status ON transactions(payment_status);
CREATE INDEX idx_transaction_shift ON transactions(shift_id);
CREATE INDEX idx_booking_date ON bookings(booking_date, booking_time);
CREATE INDEX idx_booking_staff ON bookings(staff_id, booking_date);
CREATE INDEX idx_customer_phone ON customers(phone);
CREATE INDEX idx_product_sku ON products(sku);
CREATE INDEX idx_audit_log_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_log_created ON audit_logs(created_at);
```

---

## 6. API Technical Requirements

### 6.1 REST API Standards

| Requirement | Standard |
|---|---|
| Style | RESTful |
| Format | JSON |
| Content-Type | application/json |
| Authentication | Bearer token (JWT) |
| Versioning | URL prefix (/v1/) |
| Pagination | ?page=1&limit=20 |
| Sorting | ?sort=created_at&order=desc |
| Filtering | ?status=active&branch_id=xxx |
| Error format | `{ "error": { "code": "XXX", "message": "..." } }` |

### 6.2 HTTP Status Codes

| Code | Usage |
|---|---|
| 200 | Success (GET, PUT) |
| 201 | Created (POST) |
| 204 | No Content (DELETE) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Unprocessable Entity |
| 429 | Rate Limited |
| 500 | Internal Server Error |

### 6.3 Rate Limiting

| Endpoint Type | Limit | Window |
|---|---|---|
| Public (login, health) | 30 req | 1 minute |
| Authenticated (read) | 100 req | 1 minute |
| Authenticated (write) | 50 req | 1 minute |
| Payment callback | 200 req | 1 minute |

### 6.4 JWT Token Specification

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "staff_uuid",
    "staff_code": "KSR001",
    "name": "Siti Nurhaliza",
    "role": "kasir",
    "branch_id": "branch_uuid",
    "iat": 1716800000,
    "exp": 1716801800,
    "type": "access"
  }
}
```

| Token Type | Lifetime | Refresh |
|---|---|---|
| Access | 30 minutes | Via refresh token |
| Refresh | 7 days | Re-authenticate |

---

## 7. Security Technical Requirements

### 7.1 Authentication Security

| Requirement | Implementation |
|---|---|
| Password hashing | bcrypt, 12 rounds minimum |
| PIN hashing | bcrypt, 12 rounds minimum |
| JWT signing | HS256 with secret key (min 256 bit) |
| Token storage | HttpOnly cookie (web) / Memory (POS) |
| CORS | Whitelist specific origins only |
| CSRF | Token-based for form submissions |

### 7.2 Data Security

| Requirement | Implementation |
|---|---|
| Transport | HTTPS (Cloudflare Universal SSL) |
| At rest | PostgreSQL encrypted columns (sensitive data) |
| Secrets | Environment variables, never in code |
| SQL injection | ORM (SQLAlchemy) + parameterized queries |
| XSS | Input sanitization + CSP headers |
| CSRF | Double-submit cookie pattern (csrf_token in cookie + header) |
| Rate limiting | Per-IP + per-user rate limiting |
| Input validation | Pydantic schemas (strict mode, type coercion disabled) |
| Body size limits | Max 1MB for API requests, 10MB for file uploads |
| Query size limits | Max 10 query parameters, string max 500 chars |

### 7.3 Security Headers (Custom Middleware)

> **Note:** Implemented via custom Python middleware (not Helmet.js which is Express-specific).
> Functionally equivalent — adds security headers to every HTTP response.

```python
# Custom middleware — equivalent to Helmet.js for Express
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src fonts.gstatic.com",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

### 7.4 CSRF Protection (Implementation Detail)

```python
# Double-submit cookie pattern (stateless, no server-side session)
# 1. Server sets csrf_token in cookie on every response
# 2. Client reads cookie and sends token in X-CSRF-Token header
# 3. Server compares cookie value vs header value

from fastapi import Request, HTTPException

CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

async def csrf_middleware(request: Request, call_next):
    if request.method not in CSRF_SAFE_METHODS:
        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("X-CSRF-Token")
        if not cookie_token or cookie_token != header_token:
            raise HTTPException(status_code=403, detail="CSRF token mismatch")
    return await call_next(request)
```

### 7.5 Body & Query Size Limits (Implementation Detail)

```python
# FastAPI/Starlette request size limiting
from starlette.middleware.base import BaseHTTPMiddleware

MAX_BODY_SIZE = 1 * 1024 * 1024       # 1MB for API
MAX_UPLOAD_SIZE = 10 * 1024 * 1024    # 10MB for file uploads
MAX_QUERY_PARAMS = 10
MAX_QUERY_STRING_LEN = 500

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = int(request.headers.get("content-length", 0))
        max_size = MAX_UPLOAD_SIZE if "/upload" in request.url.path else MAX_BODY_SIZE
        if content_length > max_size:
            raise HTTPException(413, f"Request body too large (max {max_size // 1024 // 1024}MB)")
        
        # Query parameter limits
        if len(request.query_params) > MAX_QUERY_PARAMS:
            raise HTTPException(400, f"Too many query params (max {MAX_QUERY_PARAMS})")
        if len(str(request.query_params)) > MAX_QUERY_STRING_LEN:
            raise HTTPException(400, "Query string too long")
        
        return await call_next(request)
```

---

## 8. Integration Technical Requirements

### 8.1 BCA Virtual Account Integration

```
Endpoint:   POST https://sandbox.bca.co.id/api/v1/va
Auth:       OAuth 2.0 (client_id + client_secret)
Request:    { "VirtualAccountNo": "...", "TrxAmount": 111000,
              "ExpDate": "2026-05-28T23:59:59" }
Response:   { "VirtualAccountNo": "...", "TrxAmount": 111000 }
Callback:   POST /payments/callback/bca
```

### 8.2 Midtrans Snap Integration

```
Endpoint:   POST https://app.sandbox.midtrans.com/snap/v1/transactions
Auth:       Basic Auth (Server Key)
Request:    { "transaction_details": { "order_id": "INV-...", "gross_amount": 111000 },
              "enabled_payments": ["qris", "credit_card", "bca_va", "bni_va"] }
Response:   { "token": "...", "redirect_url": "https://app.sandbox.midtrans.com/snap/..." }
Callback:   POST /payments/callback/midtrans
```

### 8.3 Payment Callback Security

```python
# Midtrans signature verification
def verify_midtrans_signature(order_id, status_code, gross_amount, signature_key):
    raw = f"{order_id}{status_code}{gross_amount}{SERVER_KEY}"
    expected = hashlib.sha512(raw.encode()).hexdigest()
    return expected == signature_key
```

### 8.4 Thermal Printer Integration

#### Supported Printers
| Model | Interface | Paper Width | Protocol |
|---|---|---|---|
| Epson TM-T82 | USB + Ethernet | 80mm | ESC/POS |
| Xprinter XP-58IIH | USB | 58mm | ESC/POS |
| Star TSP143IV | USB + LAN | 80mm | Star Line |

#### Connection Methods
```python
# Method 1: USB Direct (kasir desktop)
import usb.core
dev = usb.core.find(idVendor=0x04b8, idProduct=0x0202)  # Epson TM-T82
dev.write(endpoint, escpos_data)

# Method 2: Network (Ethernet/WiFi printer)
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("192.168.1.100", 9100))
sock.send(escpos_data)
sock.close()

# Method 3: Browser Print (fallback)
# JavaScript window.print() with @media print CSS
```

#### ESC/POS Receipt Generation
```python
from escpos.printer import Usb, Network

def print_receipt(transaction_id: str):
    """Print receipt to thermal printer."""
    # Fetch transaction data
    txn = get_transaction(transaction_id)
    
    # Initialize printer
    printer = Network("192.168.1.100")  # or Usb(0x04b8, 0x0202)
    
    # Print header
    printer.set(align="center", bold=True, double_height=True)
    printer.text("✦ BEAUTY & SHINE ✦\n")
    printer.set(align="center", bold=False, double_height=False)
    printer.text("Radiance & Refinement\n")
    printer.text(f"{txn.branch.address}\n")
    printer.text(f"Telp: {txn.branch.phone}\n")
    
    # Separator
    printer.text("-" * 32 + "\n")
    
    # Transaction info
    printer.set(align="left")
    printer.text(f"Invoice: {txn.invoice_number}\n")
    printer.text(f"Date:    {txn.created_at.strftime('%d/%m/%Y %H:%M')}\n")
    printer.text(f"Cashier: {txn.shift.staff.name}\n")
    
    # Separator
    printer.text("-" * 32 + "\n")
    
    # Items
    for item in txn.items:
        printer.text(f"{item.qty}x {item.item_name}\n")
        printer.set(align="right")
        printer.text(f"Rp {item.subtotal:,.0f}\n")
        printer.set(align="left")
    
    # Separator
    printer.text("-" * 32 + "\n")
    
    # Summary
    printer.text(f"Subtotal      Rp {txn.subtotal:>12,.0f}\n")
    printer.text(f"Discount      Rp {txn.discount:>12,.0f}\n")
    printer.text(f"PPN 11%       Rp {txn.tax_amount:>12,.0f}\n")
    printer.set(bold=True)
    printer.text(f"TOTAL         Rp {txn.total:>12,.0f}\n")
    printer.set(bold=False)
    
    # Payment info
    printer.text("-" * 32 + "\n")
    printer.text(f"Payment: {txn.payment_method}\n")
    printer.text(f"Paid:    Rp {txn.amount_paid:,.0f}\n")
    printer.text(f"Change:  Rp {txn.change_amount:,.0f}\n")
    
    # Footer
    printer.set(align="center")
    printer.text("\n")
    printer.text("Terima kasih atas kunjungan Anda\n")
    printer.text("✦ Beauty & Shine ✦\n")
    
    # Cut paper
    printer.cut()
```

#### Paper Size Templates

**58mm (32 chars per line):**
```
    ✦ BEAUTY & SHINE ✦
    Radiance & Refinement
--------------------------------
INV-20260527-0001
27/05/2026 14:30
Cashier: Siti
--------------------------------
1x Facial Treatment
             Rp 150.000
1x Body Massage
             Rp 200.000
--------------------------------
Subtotal     Rp 350.000
PPN 11%      Rp  38.500
TOTAL        Rp 388.500
--------------------------------
Terima kasih ✦
```

**80mm (48 chars per line):**
```
            ✦ BEAUTY & SHINE ✦
           Radiance & Refinement
        Jl. Sudirman No. 123, Jakarta
------------------------------------------------
Invoice: INV-20260527-0001
Date:    27/05/2026 14:30
Cashier: Siti Nurhaliza
------------------------------------------------
1x Facial Treatment              Rp 150.000
1x Body Massage                  Rp 200.000
------------------------------------------------
Subtotal                         Rp 350.000
Discount                         Rp      0
PPN 11%                          Rp  38.500
TOTAL                            Rp 388.500
------------------------------------------------
Payment: Cash
Paid:    Rp 400.000
Change:  Rp  11.500
------------------------------------------------
      Terima kasih atas kunjungan Anda
           ✦ Beauty & Shine ✦
```

---

### 8.5 WhatsApp Business API Integration

#### Provider Options
| Provider | Pricing | Features | Recommendation |
|---|---|---|---|
| Official Meta API | ~Rp 300-500/msg | Full API, templates, media | Production |
| Fonnte | Rp 200-400/msg | Indonesian provider, simple API | MVP/Testing |
| Wablas | Rp 100-300/msg | Cheap, Indonesian support | Budget option |

#### Fonnte Integration (Recommended for MVP)
```python
import httpx

FONNTE_API_URL = "https://api.fonnte.com/send"
FONNTE_TOKEN = "<your_token>"

async def send_receipt_whatsapp(
    phone: str,
    invoice_number: str,
    receipt_text: str,
    pdf_path: str | None = None,
) -> dict:
    """Send receipt via WhatsApp."""
    
    # Format phone (remove leading 0, add 62)
    if phone.startswith("0"):
        phone = "62" + phone[1:]
    
    # Send text message
    async with httpx.AsyncClient() as client:
        response = await client.post(
            FONNTE_API_URL,
            headers={"Authorization": FONNTE_TOKEN},
            data={
                "target": phone,
                "message": receipt_text,
                "typing": True,
            },
        )
        result = response.json()
    
    # Send PDF attachment if available
    if pdf_path and result.get("status"):
        async with httpx.AsyncClient() as client:
            await client.post(
                FONNTE_API_URL,
                headers={"Authorization": FONNTE_TOKEN},
                data={"target": phone, "message": "Receipt PDF terlampir."},
                files={"file": open(pdf_path, "rb")},
            )
    
    # Log to NOTIFICATION table
    await log_notification(
        recipient_type="customer",
        recipient_id=customer_id,
        channel="whatsapp",
        type="payment_receipt",
        title=f"Receipt {invoice_number}",
        body=receipt_text,
        status="sent" if result.get("status") else "failed",
    )
    
    return result
```

#### WhatsApp Receipt Message Template
```python
def format_receipt_whatsapp(txn) -> str:
    """Format receipt for WhatsApp message."""
    items_text = ""
    for item in txn.items:
        items_text += f"• {item.qty}x {item.item_name}  Rp {item.subtotal:,.0f}\n"
    
    return f"""🧾 *Beauty & Shine*
Receipt / Invoice

Invoice: {txn.invoice_number}
Date: {txn.created_at.strftime('%d %b %Y, %H:%M')}
Cashier: {txn.shift.staff.name}

{items_text}
─────────────────────
Subtotal  Rp {txn.subtotal:>12,.0f}
Discount  Rp {txn.discount:>12,.0f}
PPN 11%   Rp {txn.tax_amount:>12,.0f}
*Total*   *Rp {txn.total:>12,.0f}*

Payment: {txn.payment_method.value.title()}
Paid: Rp {txn.amount_paid:,.0f}
Change: Rp {txn.change_amount:,.0f}

Terima kasih atas kunjungan Anda ✦
_Beauty & Shine — Radiance & Refinement_"""
```

---

## 9. Performance Requirements

| Metric | Target | Measurement |
|---|---|---|
| API response time | < 200ms (p95) | Application logs |
| Database query time | < 50ms (p95) | Slow query log |
| Page load time | < 2 seconds | Lighthouse |
| Concurrent users | 50+ per branch | Load testing |
| Uptime | 99.5% | Monitoring |
| Error rate | < 0.1% | Error logs |

---

## 10. Deployment Requirements

### 10.1 CI/CD Pipeline

```
Developer Push
    │
    ▼
Git Repository
    │
    ▼
Run Tests (pytest)
    │
    ▼
Build Docker Image
    │
    ▼
Deploy to VPS (docker compose up -d)
    │
    ▼
Health Check (/health)
    │
    ▼
Smoke Test (curl endpoints)
```

### 10.2 Environment Configuration

```bash
# .env template
POSTGRES_USER=pos_user
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DB=pos_erp
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

JWT_SECRET_KEY=<256_bit_secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

BCA_CLIENT_ID=<bca_client_id>
BCA_CLIENT_SECRET=<bca_client_secret>
BCA_API_URL=https://sandbox.bca.co.id

MIDTRANS_SERVER_KEY=<midtrans_server_key>
MIDTRANS_CLIENT_KEY=<midtrans_client_key>
MIDTRANS_API_URL=https://app.sandbox.midtrans.com

ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 10.3 Monitoring

| Metric | Tool | Alert Threshold |
|---|---|---|
| CPU usage | System | > 80% for 5 min |
| RAM usage | System | > 85% for 5 min |
| Disk usage | System | > 90% |
| API errors | Application logs | > 10 errors/min |
| Response time | Application logs | > 500ms p95 |
| Database connections | PostgreSQL | > 80 active |

### 10.3 Logging Strategy

#### Log Format (Structured JSON)
```json
{
  "timestamp": "2026-05-27T12:00:00.000Z",
  "level": "INFO",
  "logger": "pos_erp.api",
  "message": "Transaction created",
  "request_id": "req-uuid-xxx",
  "user_id": "staff-uuid-xxx",
  "method": "POST",
  "path": "/pos/transactions",
  "status_code": 201,
  "duration_ms": 45,
  "client_ip": "192.168.1.1"
}
```

#### Log Levels

| Level | Usage | Example |
|---|---|---|
| `DEBUG` | Development detail | SQL queries, request body |
| `INFO` | Normal operations | Transaction created, shift started |
| `WARNING` | Recoverable issues | Payment retry, slow query |
| `ERROR` | Failures requiring attention | Payment callback failed, DB error |
| `CRITICAL` | System-level failures | Database down, disk full |

#### Log Rotation

| File | Max Size | Retention | Compression |
|---|---|---|---|
| `app.log` | 50 MB | 30 days | gzip |
| `error.log` | 20 MB | 90 days | gzip |
| `access.log` | 100 MB | 14 days | gzip |
| `audit.log` | 50 MB | 2 years | gzip |

#### Implementation
```python
import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure
logging.basicConfig(level=logging.INFO)
handler = logging.FileHandler("/var/log/pos-erp/app.log")
handler.setFormatter(JSONFormatter())
```

---

### 10.4 Monitoring Stack

#### Architecture
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  FastAPI App │────→│  App Logs    │────→│  Log Rotation│
│  (Uvicorn)   │     │  (JSON)      │     │  (logrotate) │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│  Health      │     │  System      │
│  Endpoint    │     │  Metrics     │
│  /health     │     │  (htop/vmstat│
└──────────────┘     └──────────────┘
```

#### Monitoring Tools (VPS-level)

| Tool | Purpose | Install |
|---|---|---|
| htop | Real-time CPU/RAM | `apt install htop` |
| iotop | Disk I/O | `apt install iotop` |
| docker stats | Container metrics | Built-in |
| pg_stat_activity | DB connections | SQL query |
| curl /health | API health check | Built-in |

#### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    """Comprehensive health check."""
    checks = {}
    
    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database": "error"]
    
    # Disk check
    disk = shutil.disk_usage("/")
    checks["disk_free_gb"] = round(disk.free / (1024**3), 1)
    checks["disk_percent"] = round(disk.used / disk.total * 100, 1)
    
    status = "ok" if checks.get("database") == "ok" else "degraded"
    return {"status": status, "checks": checks}
```

#### Alert Thresholds & Escalation

| Severity | Metric | Threshold | Action | Escalation |
|---|---|---|---|---|
| **P1 Critical** | API down | /health fails 3x | Auto-restart container | SMS owner immediately |
| **P1 Critical** | Disk full | > 95% | Stop logging, alert | SMS owner immediately |
| **P2 High** | Error rate | > 10 errors/min | Alert + log | Email manager |
| **P2 High** | Response time | > 1s p95 for 5 min | Alert | Email manager |
| **P3 Medium** | RAM usage | > 85% for 10 min | Alert | Email manager |
| **P3 Medium** | CPU usage | > 80% for 10 min | Alert | Slack notification |
| **P4 Low** | Disk usage | > 80% | Alert | Daily report |

#### Monitoring Script (Watchdog)
```bash
#!/bin/bash
# /root/scripts/health-watchdog.sh — runs every 5 min via cron

HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)

if [ "$HEALTH" != "200" ]; then
    echo "$(date): API unhealthy (HTTP $HEALTH), restarting..." >> /var/log/watchdog.log
    cd /root/pos-erp-v6 && docker compose restart api
fi

# Disk check
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ]; then
    echo "$(date): Disk usage critical: ${DISK_PCT}%" >> /var/log/watchdog.log
    # Clean old logs
    find /var/log -name "*.gz" -mtime +30 -delete
fi
```

---

### 10.5 Disaster Recovery Runbook

#### Recovery Procedures

| Scenario | RTO | RPO | Steps |
|---|---|---|---|
| API crash | 5 min | 0 | Docker auto-restart (`restart: unless-stopped`) |
| Database crash | 15 min | 0 | Docker restart + WAL replay |
| VPS reboot | 10 min | 0 | All services auto-start (systemd + Docker) |
| Data corruption | 4 hours | 24 hours | Restore from latest pg_dump backup |
| VPS failure | 8 hours | 24 hours | Provision new VPS, restore backup, re-deploy |

#### Backup & Restore Commands
```bash
# Backup (daily cron at 02:00 WIB)
docker exec pos-erp-postgres pg_dump -U pos_user pos_erp | gzip > /backups/pos_erp_$(date +%Y%m%d).sql.gz

# Restore
gunzip < /backups/pos_erp_20260527.sql.gz | docker exec -i pos-erp-postgres psql -U pos_user pos_erp

# Verify backup
gunzip -t /backups/pos_erp_20260527.sql.gz && echo "Backup OK" || echo "Backup CORRUPT"
```

---

### 10.6 CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "https://beauty.beautynshine.web.id",   # Landing page
    "https://erp.beautynshine.web.id",      # ERP + Login
    "https://pos.beautynshine.web.id",      # POS Terminal
    "https://dashboard.beautynshine.web.id", # Hermes Dashboard
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  # Cache preflight 10 min
)
```

---

### 10.7 WebSocket Support (Real-time Dashboard)

```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

class ConnectionManager:
    """Manage WebSocket connections for real-time dashboard."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Push real-time metrics every 5 seconds
            data = await get_realtime_metrics()
            await websocket.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## 11. Testing Requirements

| Type | Tool | Coverage Target |
|---|---|---|
| Unit tests | pytest | 80%+ |
| Integration tests | pytest + httpx | Critical paths |
| API tests | pytest + TestClient | All endpoints |
| Load tests | locust (future) | 50 concurrent users |
| Security tests | bandit, safety | 0 critical findings |

---

## 12. Technical Dependencies

### 12.1 Python Dependencies (requirements.txt)

```
fastapi>=0.100.0
uvicorn[standard]>=0.29.0
sqlalchemy>=2.0.0
alembic>=1.12.0
psycopg[binary]>=3.1.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
bcrypt>=4.0.0
httpx>=0.27.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
python-escpos>=3.1
```

### 12.2 System Dependencies

```
Docker >= 24.0
Docker Compose >= 2.20
PostgreSQL 16 (Docker)
Python 3.12 (Docker)
Cloudflared >= 2024.0
```

---

*Document ini harus di-review dan di-approve oleh stakeholder sebelum development phase dimulai.*
