# POS-ERP Integration Engine V6 Foundation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the V6 modular-monolith foundation for multi-branch salon POS-ERP transaction lifecycle, starting with offline cash checkout and payment boundary rules.

**Architecture:** Python modular monolith with domain modules under `src/pos_erp`. The first vertical slice implements PRD acceptance criteria AC-OFF-01 and AC-OFF-02: cash can be locally confirmed offline with a temporary ID; QRIS/bank cannot become PAID offline and remain payment pending. Later slices add outbox sync, staff locks, accounting posting, reconciliation, and dashboard projections.

**Tech Stack:** Python 3.11+, pytest, dataclasses/Decimal/Enum for domain model. API layer can be added after core behavior is stable.

---

## PRD Requirements Covered in First Slice

- FR-SYNC-02: Local Temporary ID format `TMP-[BranchCode]-[DeviceId]-[YYYYMMDD]-[LocalSeq]`.
- Payment Lifecycle: Cash Offline can become `OFFLINE_CASH_CONFIRMED` locally only.
- Payment Lifecycle: QRIS Offline and Bank Transfer Offline cannot become `PAID` offline.
- AC-OFF-01: Offline cash checkout creates `OFFLINE_CASH_CONFIRMED` transaction with Local Temporary ID.
- AC-OFF-02: Offline QRIS attempt to mark paid is prevented and kept `PAYMENT_PENDING`.

## Task 1: Create Failing Domain Tests

**Objective:** Define expected behavior before production code.

**Files:**
- Create: `tests/test_offline_checkout.py`

**Tests:**
- `test_offline_cash_checkout_creates_temp_id_and_offline_confirmed_status`
- `test_offline_qris_cannot_be_marked_paid_and_remains_payment_pending`
- `test_offline_bank_transfer_cannot_be_marked_paid_and_remains_payment_pending`

**Run:** `python -m pytest tests/test_offline_checkout.py -v`

Expected: FAIL because `pos_erp.checkout` does not exist yet.

## Task 2: Implement Minimal Checkout Domain

**Objective:** Add enough domain code to pass the offline payment boundary tests.

**Files:**
- Create: `src/pos_erp/__init__.py`
- Create: `src/pos_erp/checkout.py`

**Domain Concepts:**
- `PaymentType`: `CASH`, `QRIS`, `BANK_TRANSFER`
- `TransactionStatus`: `PAYMENT_PENDING`, `OFFLINE_CASH_CONFIRMED`
- `OfflinePaymentNotAllowed`: raised when a digital payment is marked paid offline
- `complete_offline_checkout(...)`: service function implementing PRD payment rules

**Run:** `python -m pytest tests/test_offline_checkout.py -v`

Expected: PASS.

## Task 3: Add Project Metadata

**Objective:** Make the project easy to install and test.

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`

**Run:** `python -m pytest -q`

Expected: all tests pass.

## Task 4: Next Slice Candidates

After this slice passes, implement one of:
1. Sync outbox + idempotency + retry isolation (`FR-SYNC-03` to `FR-SYNC-08`).
2. Staff lock timeout + audit logging (`FR-LOCK-01`, `FR-LOCK-02`).
3. Accounting journal balanced posting (`FR-ACC-01` to `FR-ACC-04`).
4. Reconciliation dual-threshold closing block (`AC-RECON-01`).
