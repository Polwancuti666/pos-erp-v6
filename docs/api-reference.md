# API Reference

## POS-ERP Integration Engine V6

Base URL: Configured via `AppConfig` (typically `https://pos.beautynshine.web.id`)

---

## Endpoints

### Health Check

#### `GET /health`

Returns system health status.

**Response** `200 OK`:
```json
{
  "status": "ok",
  "service": "pos-erp-v6"
}
```

**Source**: `observability.py` — `health_check()`

---

### Root Redirect

#### `GET /`

Redirects based on subdomain:
- `pos.*` subdomain → POS interface
- Other → ERP dashboard login

**Response**: `302 Found` (redirect)

---

### ERP Authentication

#### `POST /auth/login`

Authenticate ERP user (admin/manager roles).

**Request Body**:
```json
{
  "username": "admin",
  "password": "password"
}
```

**Response** `200 OK`:
- Admin users → redirected to `/dashboard`
- Kasir users → redirected to `pos.beautynshine.web.id`

**Response** `401 Unauthorized`:
```json
{
  "detail": "Invalid credentials"
}
```

**Source**: `auth.py`

---

### POS Staff Authentication

#### `POST /pos/auth`

Authenticate POS staff via PIN and start shift.

**Request Body**:
```json
{
  "pin": "1234"
}
```

**Staff PINs**:
| Staff ID | Role |
|---|---|
| KSR001 | Kasir (Cashier) |
| KSR002 | Kasir (Cashier) |
| ADM001 | Admin |
| MGR001 | Manager |

**Response** `200 OK`:
```json
{
  "staff_id": "KSR001",
  "role": "kasir",
  "shift_started": "2026-05-27T08:00:00Z"
}
```

**Response** `401 Unauthorized`:
```json
{
  "detail": "Invalid PIN"
}
```

**Source**: `pos_auth.py`

---

### End Shift

#### `POST /pos/end-shift`

End the current staff shift and trigger reconciliation.

**Request Body**:
```json
{
  "staff_id": "KSR001",
  "physical_cash": 5000000
}
```

**Response** `200 OK`:
```json
{
  "status": "ALLOW",
  "variance": 0,
  "variance_percentage": 0.0,
  "shift_ended": "2026-05-27T17:00:00Z"
}
```

Possible status values: `ALLOW`, `ACKNOWLEDGE`, `BLOCK`

**Source**: `reconciliation.py` — `evaluate_shift_closing()`

---

### Owner Dashboard

#### `GET /dashboard`

HTML dashboard view for owners/managers.

**Response** `200 OK`: HTML content rendered by `beauty_ui.py`

**Authentication**: Required (admin/manager role)

**Source**: `beauty_ui.py`, `dashboard.py`

---

### Owner Dashboard Data

#### `GET /dashboard/owner`

JSON dashboard data for programmatic access.

**Response** `200 OK`:
```json
{
  "branches": [
    {
      "branch_id": "BR001",
      "today_revenue": 15000000,
      "transaction_count": 45,
      "pending_sync": 2,
      "open_exceptions": 1
    }
  ],
  "summary": {
    "total_revenue": 15000000,
    "total_transactions": 45
  }
}
```

**Authentication**: Required (owner/admin role)

**Source**: `dashboard.py` — `OwnerDashboard`, `BranchSnapshot`

---

### Payment Providers

#### `GET /payments/providers`

List available payment providers.

**Response** `200 OK`:
```json
{
  "providers": [
    {
      "name": "bca_va",
      "display_name": "BCA Virtual Account",
      "type": "bank_transfer"
    },
    {
      "name": "midtrans",
      "display_name": "Midtrans (QRIS)",
      "type": "qris"
    }
  ]
}
```

**Source**: `payment_providers.py`

---

### POS Checkout

#### `POST /pos/checkout`

Process a POS checkout transaction.

**Request Body**:
```json
{
  "staff_id": "KSR001",
  "payment_type": "CASH",
  "items": [
    {
      "product_id": "PROD001",
      "name": "Facial Treatment",
      "quantity": 1,
      "price": 250000
    }
  ],
  "total_amount": 250000
}
```

**Payment Types**: `CASH`, `QRIS`, `BANK_TRANSFER`

**Response** `200 OK`:
```json
{
  "transaction_id": "POS-20260527-0001",
  "status": "CONFIRMED",
  "payment_type": "CASH",
  "total_amount": 250000,
  "created_at": "2026-05-27T10:30:00Z"
}
```

**Offline Behavior**: When offline, CASH transactions complete immediately and are queued for sync. QRIS/BANK_TRANSFER transactions are rejected when offline.

**Source**: `checkout.py`, `api.py` — `complete_offline_checkout()`

---

### POS Checkout (Planned)

#### `POST /pos/checkout/online`

Process checkout with online payment verification.

*(Planned)*

---

### Payment Callback

#### `POST /payments/callback/midtrans`

Receive Midtrans payment callback.

**Request Body**: Midtrans callback payload

**Response** `200 OK`:
```json
{
  "status": "ok"
}
```

**Source**: `payment.py` — `verify_qris_callback()`

---

### Payment Verification

#### `POST /payments/verify`

Manual payment verification for bank transfers.

**Request Body**:
```json
{
  "payment_intent_id": "uuid",
  "proof_url": "https://example.com/proof.jpg"
}
```

**Source**: `payment.py` — `submit_manual_proof()`, `verify_bank_transfer()`

---

## Error Responses

All endpoints return consistent error formats:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "request_id": "uuid"
}
```

---

## Authentication

| Endpoint | Auth Method | Required Role |
|---|---|---|
| GET /health | None | — |
| GET / | None | — |
| POST /auth/login | None | — |
| POST /pos/auth | None | — |
| POST /pos/end-shift | Session | kasir, admin, manager |
| GET /dashboard | Session | admin, manager, owner |
| GET /dashboard/owner | Session | admin, owner |
| GET /payments/providers | None | — |
| POST /pos/checkout | Session | kasir, admin, manager |
| POST /payments/callback/* | Signature | — (verified by HMAC) |

---

## Rate Limiting

| Endpoint Category | Limit | Window |
|---|---|---|
| Authentication | 5 requests | 1 minute |
| Checkout | 30 requests | 1 minute |
| Dashboard | 60 requests | 1 minute |
| Health | 120 requests | 1 minute |
| Payment callbacks | 100 requests | 1 minute |

---

## Request ID

Every request is assigned a unique `X-Request-ID` header for tracing. This ID is included in all log entries and error responses.

---

## Planned Endpoints

The following endpoints are planned for future releases:

| Endpoint | Description | Status |
|---|---|---|
| POST /pos/checkout/online | Online checkout with real-time verification | Planned |
| GET /inventory/stock | Current stock levels | Planned |
| POST /inventory/adjust | Manual stock adjustment | Planned |
| GET /reports/daily | Daily sales report | Planned |
| GET /reports/monthly | Monthly sales report | Planned |
| POST /sync/manual | Trigger manual sync | Planned |
| GET /exceptions | List open exceptions | Planned |
| POST /exceptions/{id}/resolve | Resolve exception | Planned |
