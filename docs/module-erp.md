# ERP Module Documentation

## POS-ERP Integration Engine V6

The ERP module handles back-office operations including accounting, reconciliation, document management, period locking, and correction processing.

---

## Module Files

| File | Responsibility |
|---|---|
| accounting.py | Journal posting, COA mapping, double-entry bookkeeping |
| reconciliation.py | Shift closing, variance detection, dual-threshold evaluation |
| document_finalization.py | ERP document finalization, document number assignment |
| document_numbering.py | Sequential document number generation |
| period_lock.py | Accounting period protection |
| correction.py | Transaction correction decisions based on state |

---

## accounting.py

### Overview

Implements double-entry accounting with Chart of Accounts (COA) mapping.

### Key Concepts

#### Double-Entry Bookkeeping
Every transaction creates balanced journal entries where:
```
SUM(debit) = SUM(credit)
```

#### COA Mapping
`COAMapping` determines which accounts are debited and credited based on transaction type.

### Data Model

#### Journal Entry

| Field | Type | Description |
|---|---|---|
| journal_number | str | Formatted: JRN-YYYYMMDD-NNNN |
| transaction_id | UUID | Related POS transaction |
| account_code | str | COA account code |
| debit | Decimal | Debit amount |
| credit | Decimal | Credit amount |
| description | str | Entry description |
| period | str | Accounting period (YYYY-MM) |

### Journal Posting Flow

```
Transaction Paid
      │
      ▼
┌──────────────────────┐
│  Determine Accounts   │
│  via COAMapping       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Create Journal Lines │
│  • Debit entry        │
│  • Credit entry       │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Validate Balance     │
│  Σ debit = Σ credit   │
└──────┬───────────────┘
       │
       ▼
  Journal Posted ✓
```

### Business Rules

1. Every paid transaction MUST generate a balanced journal entry
2. Journal numbers are sequential per date: `JRN-YYYYMMDD-NNNN`
3. Journals cannot be posted to locked periods
4. Failed journal posting triggers exception queue entry

---

## reconciliation.py

### Overview

Handles end-of-shift reconciliation with dual-threshold variance detection.

### Key Function

#### `evaluate_shift_closing(physical_cash, system_total) -> dict`

Evaluates shift closing and determines action based on variance.

**Parameters**:
- `physical_cash`: Actual cash counted at end of shift
- `system_total`: System-recorded cash total for the shift

**Returns**:
```python
{
    "status": "ALLOW" | "ACKNOWLEDGE" | "BLOCK",
    "variance": 0,
    "variance_percentage": 0.0,
    "threshold_absolute": 100000,  # Rp 100,000
    "threshold_percentage": 0.05   # 5%
}
```

### Dual Threshold System

| Threshold | Value | Description |
|---|---|---|
| Absolute | Rp 100,000 | Maximum allowed variance in Rupiah |
| Percentage | 5% | Maximum allowed variance as percentage of total |

### Decision Matrix

| Variance vs Absolute | Variance vs Percentage | Result | Action |
|---|---|---|---|
| Within | Within | ALLOW | Shift closes automatically |
| Exceeds | Within | ACKNOWLEDGE | Requires acknowledgment note |
| Within | Exceeds | ACKNOWLEDGE | Requires acknowledgment note |
| Exceeds | Exceeds | BLOCK | Manager approval required |

### Business Rules

1. **ALLOW**: Variance is within both thresholds — shift closes automatically
2. **ACKNOWLEDGE**: Variance exceeds one threshold — requires cashier acknowledgment
3. **BLOCK**: Variance exceeds both thresholds — requires manager approval
4. All reconciliations are recorded for audit purposes

---

## document_finalization.py

### Overview

Handles finalization of documents in the ERP system, ensuring proper numbering and status transitions.

### Key Function

#### `apply_erp_finalization(document: dict) -> dict`

Finalizes a document for ERP submission.

**Process**:
1. Assign document number via NumberingService
2. Validate document completeness
3. Mark document as finalized
4. Queue for ERP sync

### DocumentNumbers

Tracks document number prefixes:

| Prefix | Format | Description |
|---|---|---|
| POS | POS-YYYYMMDD-NNNN | POS transactions |
| TRM | TRM-YYYYMMDD-NNNN | Treatment records |
| JRN | JRN-YYYYMMDD-NNNN | Journal entries |

---

## document_numbering.py

### Overview

Generates sequential document numbers with date-based formatting.

### NumberingService

Provides atomic sequence generation for document types.

### Document Formats

| Type | Format | Example |
|---|---|---|
| POS | POS-YYYYMMDD-NNNN | POS-20260527-0001 |
| TRM | TRM-YYYYMMDD-NNNN | TRM-20260527-0001 |
| JRN | JRN-YYYYMMDD-NNNN | JRN-20260527-0001 |
| INV-MOV | INV-MOV-YYYYMMDD-NNNN | INV-MOV-20260527-0001 |

### Key Functions

#### `next_number(doc_type: str) -> str`
Generates the next sequential number for a document type.

**Business Rules**:
- Sequence resets daily (based on date component)
- Numbers are zero-padded to 4 digits
- Generation is atomic to prevent duplicate numbers

---

## period_lock.py

### Overview

Protects accounting periods from unauthorized modifications.

### Key Function

#### `evaluate_period_action(period: str, action: str) -> PeriodLockDecision`

Determines if an action is allowed on a given accounting period.

**Parameters**:
- `period`: Accounting period (YYYY-MM format)
- `action`: Requested action (e.g., "post", "void", "adjust")

**Returns**: `PeriodLockDecision`

### PeriodLockDecision

| Field | Type | Description |
|---|---|---|
| allowed | bool | Whether the action is permitted |
| reason | str | Explanation if action is denied |
| requires_approval | bool | If manager approval is needed |

### Business Rules

1. Locked periods cannot be modified without manager override
2. Current period is always open for posting
3. Previous periods require explicit unlock or approval
4. Period lock status is auditable

---

## correction.py

### Overview

Determines correction actions based on transaction state (sync status + accounting status).

### Key Function

#### `decide_correction_action(transaction: dict) -> CorrectionAction`

Analyzes transaction state and returns the appropriate correction action.

**Parameters**:
- `transaction`: Transaction with sync and accounting metadata

### Correction Actions

| Action | Condition | Description |
|---|---|---|
| LOCAL_VOID | Not synced, not posted | Void locally, remove from sync outbox |
| ERP_REVERSAL | Synced, posted | Create reversal journal entry in ERP |
| REJECT | Correction not applicable | Reject correction request |
| REFUND | Synced, posted, customer request | Process refund via payment provider |
| MANUAL_REVIEW | Ambiguous state | Flag for manual review |

### Correction Flow

```
Correction Requested
      │
      ▼
┌───────────────────────────┐
│  decide_correction_action()│
│                           │
│  Check:                   │
│  • sync_state             │
│  • accounting_state       │
│  • payment_state          │
└─────┬─────────────────────┘
      │
      ├── Not synced + Not posted ──▶ LOCAL_VOID
      │
      ├── Synced + Posted ──▶ ERP_REVERSAL
      │
      ├── Synced + Posted + Refund requested ──▶ REFUND
      │
      ├── Ambiguous state ──▶ MANUAL_REVIEW
      │
      └── Invalid request ──▶ REJECT
```

### Decision Matrix

| Synced | Posted | Customer Request | Action |
|---|---|---|---|
| No | No | — | LOCAL_VOID |
| Yes | Yes | No | ERP_REVERSAL |
| Yes | Yes | Yes | REFUND |
| Ambiguous | Ambiguous | — | MANUAL_REVIEW |
| — | — | Invalid | REJECT |

---

## Integration Points

### With POS Module
- Checkout triggers journal posting after payment
- Shift end triggers reconciliation

### With Sync Module
- Finalized documents are queued for ERP sync
- Sync status affects correction action decisions

### With Exception Queue
- Accounting failures are logged as exceptions
- Blocked reconciliations create exception entries
- Manual review items are added to exception queue

### With Permissions Module
- Period lock overrides require manager role
- Correction approvals require appropriate role

---

## Error Handling

| Error | Handler | Action |
|---|---|---|
| Unbalanced journal | accounting.py | Reject posting, log exception |
| Locked period | period_lock.py | Deny action, notify manager |
| Duplicate document number | document_numbering.py | Retry with new sequence |
| Ambiguous correction state | correction.py | Queue for manual review |
| ERP sync failure | sync.py | Retry (3x), then escalate |
