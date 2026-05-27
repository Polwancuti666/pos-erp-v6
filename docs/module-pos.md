# POS Module Documentation

## POS-ERP Integration Engine V6

The POS module handles point-of-sale operations including checkout processing, staff authentication, resource locking, and treatment management.

---

## Module Files

| File | Responsibility |
|---|---|
| checkout.py | Transaction processing, offline/online checkout |
| pos_auth.py | Staff PIN authentication, shift management |
| staff_lock.py | Optimistic resource locking with timeout |
| treatment.py | Service management, staff reassignment |

---

## checkout.py

### Overview

Handles POS checkout transactions with support for offline-first processing.

### Data Models

#### PaymentType
```python
class PaymentType(Enum):
    CASH = "CASH"
    QRIS = "QRIS"
    BANK_TRANSFER = "BANK_TRANSFER"
```

#### TransactionStatus
```python
class TransactionStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    VOID = "VOID"
    REVERSED = "REVERSED"
```

#### OfflineTransaction
Represents a transaction processed at the POS terminal.

| Field | Type | Description |
|---|---|---|
| id | UUID | Unique transaction identifier |
| staff_id | str | Staff member who created the transaction |
| payment_type | PaymentType | Payment method used |
| status | TransactionStatus | Current transaction status |
| items | list | Transaction line items |
| total_amount | Decimal | Transaction total |
| created_at | datetime | Transaction creation timestamp |

### Business Rules

1. **CASH transactions** complete immediately with status `CONFIRMED`
2. **QRIS transactions** create a `PaymentIntent` with status `PENDING`
3. **BANK_TRANSFER transactions** create a `PaymentIntent` with status `PENDING`
4. **Offline mode**: Only CASH transactions are allowed when offline
5. All transactions are queued in the sync outbox for ERP synchronization

### Key Functions

#### `complete_offline_checkout(staff_id, payment_type, items, total) -> OfflineTransaction`
Creates and completes a cash transaction in offline mode.

**Flow**:
1. Validate staff authorization
2. Create transaction record
3. Set status to CONFIRMED (for CASH) or PENDING (for online methods)
4. Queue for sync
5. Return transaction

---

## pos_auth.py

### Overview

Handles POS staff authentication via PIN codes and shift lifecycle management.

### Staff Credentials

| Staff ID | Role | PIN |
|---|---|---|
| KSR001 | Kasir (Cashier) | Configured at setup |
| KSR002 | Kasir (Cashier) | Configured at setup |
| ADM001 | Admin | Configured at setup |
| MGR001 | Manager | Configured at setup |

### Shift Management

**Shift Lifecycle**:
```
Staff arrives → PIN auth → Shift starts → [Transactions] → End shift → Reconciliation
```

### Key Functions

#### `authenticate(pin: str) -> dict`
Authenticates staff via PIN and starts a new shift.

**Returns**:
```python
{
    "staff_id": "KSR001",
    "role": "kasir",
    "shift_started": datetime
}
```

**Business Rules**:
- Each staff member can only have one active shift at a time
- PIN attempts are rate-limited to prevent brute force
- Shift start is recorded for reconciliation purposes

#### `end_shift(staff_id: str, physical_cash: Decimal) -> dict`
Ends the current shift and triggers reconciliation.

**Parameters**:
- `staff_id`: Staff ending the shift
- `physical_cash`: Physical cash count for reconciliation

---

## staff_lock.py

### Overview

Implements optimistic locking with automatic timeout for concurrent resource access.

### StaffLockManager

Manages resource locks to prevent concurrent modifications.

### Data Model

| Field | Type | Description |
|---|---|---|
| resource_id | str | Identifier of the locked resource |
| staff_id | str | Staff member holding the lock |
| acquired_at | datetime | When the lock was acquired |
| expires_at | datetime | When the lock expires |

### Lock Timeout

**Default**: 10 minutes

Locks automatically expire if not released, preventing deadlocks from abandoned sessions.

### Key Functions

#### `reserve(resource_id: str, staff_id: str) -> bool`
Attempts to acquire a lock on a resource.

**Returns**: `True` if lock acquired, `False` if resource is already locked

**Business Rules**:
- A resource can only be locked by one staff member at a time
- Expired locks are automatically cleaned up during reserve attempts
- Lock acquisition is atomic

#### `release(resource_id: str, staff_id: str) -> bool`
Releases a lock held by a staff member.

**Returns**: `True` if lock released, `False` if lock not found or held by different staff

#### `release_expired() -> int`
Releases all expired locks.

**Returns**: Number of locks released

**Usage**: Called periodically to clean up abandoned locks

### Lock Flow

```
Staff A requests lock on Treatment #123
      │
      ▼
  reserve("treatment:123", "KSR001")
      │
      ├── Lock available → Lock granted (expires in 10 min)
      │       │
      │       ├── Staff completes work → release()
      │       │
      │       └── 10 minutes pass → release_expired()
      │
      └── Lock held by Staff B → return False
```

---

## treatment.py

### Overview

Manages treatment services, allowing modification before payment.

### TreatmentService

Handles adding/removing services and staff reassignment.

### Key Functions

#### `add_service(treatment_id: str, service: dict) -> dict`
Adds a service to an existing treatment.

**Business Rules**:
- Can only modify treatments before payment is initiated
- Adding a service updates the treatment total
- Inventory is checked for consumable availability

#### `remove_service(treatment_id: str, service_id: str) -> dict`
Removes a service from a treatment.

**Business Rules**:
- Can only remove services before payment is initiated
- Removing a service returns allocated consumables to inventory
- Treatment total is updated accordingly

#### `suggest_staff_reassignment(treatment_id: str, reason: str) -> dict`
Suggests alternative staff when the original staff is unavailable.

**Parameters**:
- `treatment_id`: Treatment requiring reassignment
- `reason`: Reason for reassignment (e.g., "staff unavailable", "shift ended")

**Returns**:
```python
{
    "suggested_staff": "KSR002",
    "reason": "Original staff shift ended",
    "available_staff": ["KSR001", "KSR002"]
}
```

---

## Integration Points

### With Payment Module
- Checkout creates `PaymentIntent` for online payment methods
- Payment verification updates transaction status

### With Inventory Module
- Checkout triggers stock movements for consumable items
- Service removal returns stock

### With Sync Module
- All transactions are queued in sync outbox
- Offline transactions sync when connectivity is restored

### With Reconciliation Module
- Shift end triggers reconciliation evaluation
- Transaction totals are compared against physical cash

### With Staff Lock Module
- Treatment modifications require staff lock acquisition
- Prevents concurrent edits to the same treatment

---

## Error Handling

| Error | Handler | Action |
|---|---|---|
| Invalid PIN | pos_auth.py | Return 401 |
| Lock conflict | staff_lock.py | Return conflict error |
| Offline + online payment | checkout.py | Reject transaction |
| Treatment already paid | treatment.py | Reject modification |
| Negative stock | inventory.py | Escalate to exception queue |
