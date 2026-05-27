# Business Process Flows

## POS-ERP Integration Engine V6

This document describes the core business processes implemented in the POS-ERP system.

---

## 1. POS Checkout Flow

The checkout flow supports both offline and online payment modes.

### Flow Diagram

```
Customer Ready to Pay
        │
        ▼
┌─────────────────────┐
│  Select Payment Type │
└─────┬───────┬───────┘
      │       │
      ▼       ▼
   [CASH]  [QRIS/BANK_TRANSFER]
      │       │
      ▼       ▼
  Complete   Create PaymentIntent
  Offline    (pending status)
  Txn            │
      │          ▼
      │     ┌──────────────┐
      │     │ Online Verify │
      │     └──────┬───────┘
      │            │
      │     ┌──────┴──────┐
      │     ▼             ▼
      │  [QRIS:         [Bank Transfer:
      │  callback       manual proof
      │  verified]      submitted]
      │     │             │
      │     ▼             ▼
      │  Status →      Status →
      │  PAID           PAID
      │     │             │
      ▼     ▼             ▼
┌─────────────────────────────┐
│    Post-Payment Processing  │
│  • Update inventory         │
│  • Post accounting journal  │
│  • Record sync outbox       │
│  • Generate receipt         │
└─────────────────────────────┘
```

### Business Rules

| Payment Type | Initial Status | Verification Method | Final Status |
|---|---|---|---|
| CASH | CONFIRMED | N/A (immediate) | PAID |
| QRIS | PENDING | Callback verification | PAID / FAILED |
| BANK_TRANSFER | PENDING | Manual proof upload | PAID / REJECTED |

- **Offline Cash**: Transactions complete locally with `OfflineTransaction` and are queued for sync.
- **Online QRIS**: `PaymentIntent` created; awaits callback via `verify_qris_callback()`.
- **Bank Transfer**: `PaymentIntent` created; manual proof submitted via `submit_manual_proof()`.

---

## 2. Treatment Editing Flow

Services can be added or removed from a treatment before payment is completed.

### Flow Diagram

```
Open Treatment
      │
      ▼
┌─────────────────────┐
│  Add/Remove Services │
└─────┬───────────────┘
      │
      ▼
┌──────────────────────────┐
│  Staff Reassignment Check │
│  suggest_staff_reassignment() │
└─────┬────────────────────┘
      │
      ▼
┌──────────────────┐
│  Confirm Changes │
└─────┬────────────┘
      │
      ▼
┌──────────────────┐
│  Proceed to       │
│  Checkout         │
└──────────────────┘
```

### Business Rules

- Services can only be modified **before payment** is initiated.
- Removing a service triggers stock return if consumables were allocated.
- Staff reassignment is suggested when the original staff is unavailable.
- `TreatmentService.add_service()` and `remove_service()` handle modifications.

---

## 3. Daily Closing Flow

End-of-day shift reconciliation with dual-threshold variance detection.

### Flow Diagram

```
End of Shift
      │
      ▼
┌────────────────────┐
│  Count Physical Cash │
└─────┬──────────────┘
      │
      ▼
┌─────────────────────────────┐
│  evaluate_shift_closing()    │
│  Compare: physical vs system │
└─────┬───────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│  Dual Threshold Check               │
│  • Absolute: Rp 100,000             │
│  • Percentage: 5%                   │
└─────┬──────────┬──────────┬─────────┘
      │          │          │
      ▼          ▼          ▼
  [Within     [Minor      [Major
   Threshold]  Variance]   Variance]
      │          │          │
      ▼          ▼          ▼
   ALLOW      ACKNOWLEDGE   BLOCK
   (auto)     (note)        (manager required)
```

### Business Rules

- Variance within both thresholds: **ALLOW** — shift closes automatically.
- Variance exceeds one threshold: **ACKNOWLEDGE** — requires acknowledgment note.
- Variance exceeds both thresholds: **BLOCK** — manager approval required.
- Cashiers: `KSR001`, `KSR002` | Admin: `ADM001` | Manager: `MGR001`.

---

## 4. Sync Flow

Outbox pattern with retry and escalation for reliable ERP synchronization.

### Flow Diagram

```
Transaction Completed
      │
      ▼
┌────────────────────┐
│  enqueue() to       │
│  SyncQueue Outbox   │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│  Connectivity Check │
│  ConnectivityNotice │
└─────┬──────────────┘
      │
      ├── Online ──▶ run_once() ──▶ Success? ──▶ Done
      │                    │
      │                    ▼
      │               [Retry: max 3]
      │                    │
      │                    ▼
      │               [Escalate to ERP]
      │
      └── Offline ──▶ Queue for later
                           │
                           ▼
                    ┌──────────────┐
                    │  Connectivity │
                    │  Recovered    │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  SyncApproval │
                    │  Required     │
                    └──────────────┘
```

### Business Rules

- Maximum **3 retries** before escalation to ERP admin.
- Connectivity recovery requires **SyncApproval** before resuming.
- `BranchCache` stores offline transaction data locally.
- `DeviceBinding` ensures sync from authorized devices only.

---

## 5. Accounting Flow

Double-entry journal posting triggered by paid transactions.

### Flow Diagram

```
Transaction Status → PAID
      │
      ▼
┌──────────────────────┐
│  COA Mapping          │
│  COAMapping           │
└─────┬────────────────┘
      │
      ▼
┌──────────────────────┐
│  Create Journal Entry │
│  debit = credit       │
└─────┬────────────────┘
      │
      ▼
┌──────────────────────┐
│  Validate Balance     │
│  Σ debit = Σ credit   │
└─────┬────────────────┘
      │
      ▼
  Journal Posted ✓
```

### Business Rules

- Every paid transaction generates a **balanced journal entry** (debit = credit).
- COA mapping determines account codes based on transaction type.
- Journal numbers follow format: `JRN-YYYYMMDD-NNNN`.
- Period lock checks prevent posting to locked periods via `evaluate_period_action()`.

---

## 6. Correction Flow

Correction actions determined by transaction state (sync status + accounting status).

### Flow Diagram

```
Correction Requested
      │
      ▼
┌───────────────────────────┐
│  decide_correction_action()│
│  Check: sync state +       │
│         accounting state    │
└─────┬─────────────────────┘
      │
      ▼
┌───────────────────────────────────────┐
│  Correction Actions                   │
├──────────┬──────────┬────────┬────────┤
│ LOCAL    │ ERP      │        │        │
│ VOID     │ REVERSAL │ REFUND │ REJECT │
└──────────┴──────────┴────────┴────────┘
```

### Correction Actions

| Action | Condition | Description |
|---|---|---|
| LOCAL_VOID | Not synced, not posted | Void locally, remove from outbox |
| ERP_REVERSAL | Synced, posted | Create reversal entry in ERP |
| REFUND | Synced, posted, customer request | Process refund through payment provider |
| REJECT | Correction not applicable | Reject correction request |
| MANUAL_REVIEW | Ambiguous state | Flag for manual review |

---

## 7. Staff Lock Flow

Optimistic locking with timeout for concurrent access management.

### Flow Diagram

```
Staff Needs Resource
      │
      ▼
┌──────────────────────┐
│  reserve(resource_id) │
└─────┬────────────────┘
      │
      ├── Available ──▶ Lock Granted (10 min)
      │                      │
      │                      ├── Task Complete ──▶ release()
      │                      │
      │                      └── Timeout (10 min) ──▶ release_expired()
      │
      └── Locked ──▶ Wait / Error
```

### Business Rules

- Lock duration: **10 minutes** (configurable).
- Automatic expiry via `release_expired()` for abandoned locks.
- `StaffLockManager` tracks: resource_id, staff_id, timestamp.
- Prevents concurrent modifications to the same treatment/transaction.

---

## Cross-Cutting Concerns

### Exception Handling

All flows integrate with `ExceptionQueue` for error management:

- **SLA Tiers**: 2h (critical), 4h (high), 8h (medium), 24h (low)
- **Exception Types**: 6 types covering payment, sync, inventory, accounting, document, and system errors
- Exceptions are escalated automatically when SLA is breached

### Observability

- `health_check()` monitors system status
- `MetricsRegistry` tracks business and technical metrics
- Request ID propagation across all flows
