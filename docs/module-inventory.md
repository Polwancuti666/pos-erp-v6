# Inventory Module Documentation

## POS-ERP Integration Engine V6

The inventory module tracks stock movements for consumable items used in treatments and retail sales.

---

## Module File

| File | Responsibility |
|---|---|
| inventory.py | Stock movement tracking, inventory policy enforcement |

---

## Data Models

### MovementType

```python
class MovementType(Enum):
    IN = "IN"    # Stock increase
    OUT = "OUT"  # Stock decrease
```

### MovementReason

```python
class MovementReason(Enum):
    PURCHASE = "PURCHASE"      # Stock purchased from supplier
    SALE = "SALE"              # Stock sold to customer
    ADJUSTMENT = "ADJUSTMENT"  # Manual stock adjustment
    RETURN = "RETURN"          # Customer return
    DAMAGED = "DAMAGED"        # Damaged stock write-off
    EXPIRED = "EXPIRED"        # Expired stock write-off
```

### StockMovement

| Field | Type | Description |
|---|---|---|
| id | UUID | Unique movement identifier |
| product_id | str | Product identifier |
| movement_type | MovementType | IN or OUT |
| reason | MovementReason | Reason for movement |
| quantity | Decimal | Quantity moved (always positive) |
| reference_id | str | Related transaction/document ID |
| staff_id | str | Staff who recorded the movement |
| created_at | datetime | Movement timestamp |
| escalated | bool | Whether negative stock was escalated |

---

## InventoryService

### Overview

Manages stock movements and enforces inventory policies.

### Key Functions

#### `record_movement(product_id, movement_type, reason, quantity, reference_id, staff_id) -> StockMovement`

Records a stock movement and enforces inventory policies.

**Parameters**:
- `product_id`: Product being moved
- `movement_type`: IN or OUT
- `reason`: Movement reason (PURCHASE, SALE, etc.)
- `quantity`: Quantity to move
- `reference_id`: Related transaction or document ID
- `staff_id`: Staff recording the movement

**Returns**: `StockMovement` record

**Flow**:
```
record_movement() called
      │
      ▼
┌──────────────────────┐
│  Validate Parameters  │
│  • product_id exists  │
│  • quantity > 0       │
│  • valid reason       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Check Current Stock  │
│  (for OUT movements)  │
└──────┬───────────────┘
       │
       ├── Sufficient stock ──▶ Record movement
       │
       └── Insufficient stock ──▶ InventoryPolicy check
              │
              ├── Allow negative ──▶ Record + Escalate
              │
              └── Block negative ──▶ Raise error
```

---

## InventoryPolicy

### Overview

Defines rules for stock management behavior.

### Negative Stock Policy

| Policy | Behavior | Use Case |
|---|---|---|
| ALLOW_NEGATIVE | Record movement, escalate to exception queue | High-priority items |
| BLOCK_NEGATIVE | Reject movement, raise error | Critical items |
| WARN_NEGATIVE | Record movement, log warning | Low-priority items |

### Escalation

When negative stock is detected and policy allows it:

1. Movement is recorded with `escalated = True`
2. Exception entry is created in `ExceptionQueue`
3. Exception type: `INVENTORY`
4. Severity: `HIGH`
5. SLA: 4 hours

---

## Business Rules

### Stock Movements

| Scenario | MovementType | Reason | Trigger |
|---|---|---|---|
| Purchase from supplier | IN | PURCHASE | Manual entry or PO receipt |
| Treatment consumable | OUT | SALE | POS checkout |
| Retail sale | OUT | SALE | POS checkout |
| Stock count adjustment | IN/OUT | ADJUSTMENT | Manual adjustment |
| Customer return | IN | RETURN | Return processing |
| Damaged goods | OUT | DAMAGED | Manual write-off |
| Expired goods | OUT | EXPIRED | Manual write-off |

### Document Numbering

Inventory movements generate document numbers:
- Format: `INV-MOV-YYYYMMDD-NNNN`
- Sequential per date
- Zero-padded to 4 digits

### Integration with Checkout

When a POS checkout is completed:

1. For each consumable item in the transaction:
   - `record_movement()` is called with `movement_type=OUT`, `reason=SALE`
   - `reference_id` is set to the transaction ID
2. If stock is insufficient:
   - Policy determines whether to block or allow with escalation
   - Blocked transactions cannot complete
   - Allowed transactions proceed with negative stock exception

### Integration with Treatment

When a service is removed from a treatment:

1. Previously allocated consumables are returned
2. `record_movement()` is called with `movement_type=IN`, `reason=RETURN`
3. Stock is restored

---

## Negative Stock Escalation

### Flow

```
OUT movement requested
      │
      ▼
┌──────────────────────┐
│  Current stock < 0?   │
└──────┬───────────────┘
       │
       ├── No ──▶ Record normally
       │
       └── Yes ──▶ Check InventoryPolicy
              │
              ├── ALLOW_NEGATIVE
              │     │
              │     ├── Record movement (escalated=True)
              │     └── Create ExceptionItem
              │           • type: INVENTORY
              │           • severity: HIGH
              │           • sla_hours: 4
              │
              ├── BLOCK_NEGATIVE
              │     └── Raise InsufficientStockError
              │
              └── WARN_NEGATIVE
                    │
                    ├── Record movement (escalated=True)
                    └── Log warning
```

---

## Integration Points

### With POS Module (checkout.py)
- Checkout triggers stock OUT movements for consumable items
- Treatment service removal triggers stock IN returns

### With Sync Module (sync.py)
- Stock movements are queued for ERP synchronization
- Document numbers are generated before sync

### With Exception Queue (exception_queue.py)
- Negative stock creates INVENTORY exception entries
- Exceptions follow SLA tiers for resolution

### With Document Numbering (document_numbering.py)
- Each movement receives a sequential document number
- Format: INV-MOV-YYYYMMDD-NNNN

---

## Error Handling

| Error | Condition | Action |
|---|---|---|
| Invalid product_id | Product not found | Raise ValueError |
| Invalid quantity | quantity <= 0 | Raise ValueError |
| Insufficient stock | BLOCK_NEGATIVE policy | Raise InsufficientStockError |
| Negative stock | ALLOW_NEGATIVE policy | Record + escalate |
| Duplicate movement | Idempotency check | Return existing movement |

---

## Planned Enhancements

| Feature | Description | Status |
|---|---|---|
| Batch tracking | Track stock by batch/lot number | Planned |
| Expiry management | Auto-flag expiring stock | Planned |
| Reorder alerts | Automatic reorder point notifications | Planned |
| Stock transfer | Inter-branch stock transfers | Planned |
| Stock valuation | FIFO/Average cost calculation | Planned |
| Physical count | Periodic stock count workflow | Planned |
