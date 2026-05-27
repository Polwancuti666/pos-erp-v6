# Database Design

## POS-ERP Integration Engine V6

---

## 1. Storage Strategy

| Environment | Implementation | Module |
|---|---|---|
| Development | InMemoryRepository | persistence.py |
| Production | PostgreSQL (async) | postgresql.py |

The system uses a **Repository + Unit of Work** pattern, allowing seamless switching between in-memory and PostgreSQL backends.

---

## 2. Entity Overview

### Entity Relationship Diagram

```
┌──────────────────┐     ┌──────────────────┐
│   Transaction    │────▶│  PaymentIntent   │
│                  │     │                  │
│  • id            │     │  • id            │
│  • status        │     │  • provider      │
│  • payment_type  │     │  • status        │
│  • total         │     │  • amount        │
└────────┬─────────┘     └──────────────────┘
         │
         ├──▶ ┌──────────────────┐
         │    │  StockMovement   │
         │    │                  │
         │    │  • id            │
         │    │  • movement_type │
         │    │  • quantity      │
         │    └──────────────────┘
         │
         ├──▶ ┌──────────────────┐
         │    │   JournalEntry   │
         │    │                  │
         │    │  • id            │
         │    │  • debit         │
         │    │  • credit        │
         │    └──────────────────┘
         │
         └──▶ ┌──────────────────┐
              │   SyncOutbox     │
              │                  │
              │  • id            │
              │  • retries       │
              │  • status        │
              └──────────────────┘

┌──────────────────┐     ┌──────────────────┐
│   StaffLock      │     │  DocumentNumber  │
│                  │     │                  │
│  • resource_id   │     │  • prefix        │
│  • staff_id      │     │  • sequence      │
│  • expires_at    │     │  • date          │
└──────────────────┘     └──────────────────┘

┌──────────────────┐
│  ExceptionItem   │
│                  │
│  • id            │
│  • type          │
│  • severity      │
│  • sla_hours     │
└──────────────────┘
```

---

## 3. Entity Details

### transactions

Represents POS checkout transactions.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| staff_id | VARCHAR | Staff who created transaction |
| status | ENUM | PENDING, CONFIRMED, PAID, VOID, REVERSED |
| payment_type | ENUM | CASH, QRIS, BANK_TRANSFER |
| total_amount | DECIMAL | Transaction total |
| items | JSONB | Transaction line items |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |
| synced_at | TIMESTAMP | ERP sync timestamp (nullable) |

**Source**: `checkout.py` — `OfflineTransaction`, `TransactionStatus`, `PaymentType`

### payment_intents

Tracks payment lifecycle for online payment methods.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| transaction_id | UUID | FK → transactions |
| provider | VARCHAR | Payment provider name |
| external_id | VARCHAR | Provider's payment ID |
| status | ENUM | PENDING, PAID, FAILED, EXPIRED |
| amount | DECIMAL | Payment amount |
| callback_data | JSONB | Raw callback payload |
| created_at | TIMESTAMP | Creation timestamp |
| verified_at | TIMESTAMP | Verification timestamp (nullable) |

**Source**: `payment.py` — `PaymentIntent`

### inventory_movements

Tracks stock changes for consumable items.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| product_id | VARCHAR | Product identifier |
| movement_type | ENUM | IN, OUT |
| reason | ENUM | PURCHASE, SALE, ADJUSTMENT, RETURN, DAMAGED, EXPIRED |
| quantity | DECIMAL | Movement quantity |
| reference_id | VARCHAR | Related transaction/document ID |
| staff_id | VARCHAR | Staff who recorded movement |
| created_at | TIMESTAMP | Movement timestamp |
| escalated | BOOLEAN | Negative stock escalation flag |

**Source**: `inventory.py` — `StockMovement`, `MovementType`, `MovementReason`

### staff_locks

Optimistic locks for concurrent resource access.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| resource_id | VARCHAR | Locked resource identifier |
| staff_id | VARCHAR | Staff holding the lock |
| acquired_at | TIMESTAMP | Lock acquisition time |
| expires_at | TIMESTAMP | Lock expiry time |

**Source**: `staff_lock.py` — `StaffLockManager`

Lock timeout: **10 minutes** (configurable).

### journal_entries

Double-entry accounting journals.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| journal_number | VARCHAR | Formatted: JRN-YYYYMMDD-NNNN |
| transaction_id | UUID | FK → transactions |
| account_code | VARCHAR | COA account code |
| debit | DECIMAL | Debit amount |
| credit | DECIMAL | Credit amount |
| description | VARCHAR | Entry description |
| period | VARCHAR | Accounting period (YYYY-MM) |
| created_at | TIMESTAMP | Posting timestamp |

**Source**: `accounting.py` — COAMapping, `document_numbering.py` — JRN format

**Invariant**: For every journal_number, SUM(debit) = SUM(credit)

### exception_items

Exception queue entries with SLA tracking.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| type | ENUM | PAYMENT, SYNC, INVENTORY, ACCOUNTING, DOCUMENT, SYSTEM |
| severity | ENUM | LOW, MEDIUM, HIGH, CRITICAL |
| sla_hours | INT | SLA deadline in hours |
| description | TEXT | Exception description |
| context_data | JSONB | Related entity data |
| status | ENUM | OPEN, IN_PROGRESS, RESOLVED, ESCALATED |
| created_at | TIMESTAMP | Exception timestamp |
| resolved_at | TIMESTAMP | Resolution timestamp (nullable) |

**Source**: `exception_queue.py` — SLA tiers: 2h, 4h, 8h, 24h

### sync_outbox

Outbox pattern for reliable ERP synchronization.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| entity_type | VARCHAR | Type of entity to sync |
| entity_id | UUID | Entity identifier |
| payload | JSONB | Serialized entity data |
| status | ENUM | PENDING, PROCESSING, COMPLETED, FAILED, ESCALATED |
| retries | INT | Retry count (max 3) |
| last_error | TEXT | Last error message |
| created_at | TIMESTAMP | Enqueue timestamp |
| processed_at | TIMESTAMP | Processing timestamp (nullable) |

**Source**: `sync.py` — SyncQueue, max 3 retries before escalation

### document_numbers

Sequential document number tracking.

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| prefix | VARCHAR | Document prefix (POS, TRM, JRN, INV-MOV) |
| date | DATE | Date component of document number |
| sequence | INT | Current sequence number |
| created_at | TIMESTAMP | Record creation |

**Source**: `document_numbering.py` — NumberingService

Document number formats:
- **POS**: POS-YYYYMMDD-NNNN
- **TRM**: TRM-YYYYMMDD-NNNN
- **JRN**: JRN-YYYYMMDD-NNNN
- **INV-MOV**: INV-MOV-YYYYMMDD-NNNN

---

## 4. Repository Interface

The `InMemoryRepository` (persistence.py) and PostgreSQL implementation share a common interface:

```python
class Repository(Protocol):
    async def get(self, entity_type: str, id: str) -> Optional[dict]: ...
    async def list(self, entity_type: str, filters: dict = None) -> list: ...
    async def save(self, entity_type: str, data: dict) -> dict: ...
    async def update(self, entity_type: str, id: str, data: dict) -> dict: ...
    async def delete(self, entity_type: str, id: str) -> bool: ...
```

The `UnitOfWork` pattern ensures transactional consistency across multiple repository operations.

---

## 5. Migrations

Schema migrations are managed by `MigrationRunner` (migrations.py):

- Migrations are versioned and executed sequentially
- Each migration has an `up()` and `down()` method
- Migration state is tracked in a `schema_migrations` table

**Current Status**: In-memory storage for development; full PostgreSQL schema migration (Planned).

---

## 6. PostgreSQL Configuration

Production database settings via `PostgreSQLSettings` (postgresql.py):

| Setting | Environment Variable | Default |
|---|---|---|
| Host | PG_HOST | localhost |
| Port | PG_PORT | 5432 |
| Database | PG_DATABASE | pos_erp |
| User | PG_USER | pos_erp |
| Password | PG_PASSWORD | (required) |
| SSL Mode | PG_SSLMODE | prefer |

Connection URL is built via `build_async_database_url()` using the `asyncpg` driver.

---

## 7. Indexes (Planned)

| Table | Index | Purpose |
|---|---|---|
| transactions | idx_txn_status | Filter by transaction status |
| transactions | idx_txn_created | Sort/filter by creation date |
| transactions | idx_txn_staff | Filter by staff |
| payment_intents | idx_pi_status | Filter by payment status |
| payment_intents | idx_pi_external | Lookup by external payment ID |
| sync_outbox | idx_outbox_status | Find pending items to process |
| sync_outbox | idx_outbox_created | Sort by creation time |
| staff_locks | idx_lock_resource | Unique constraint on active locks |
| staff_locks | idx_lock_expiry | Find expired locks for cleanup |
| exception_items | idx_ex_status | Filter open exceptions |
| exception_items | idx_ex_sla | Find items approaching SLA breach |
