from pos_erp.correction import (
    CorrectionAction,
    TransactionAccountingState,
    TransactionSyncState,
    decide_correction_action,
)


def test_local_only_not_synced_uses_local_correction_not_erp_reversal():
    decision = decide_correction_action(
        sync_state=TransactionSyncState.LOCAL_ONLY,
        accounting_state=TransactionAccountingState.NOT_POSTED,
    )

    assert decision.action is CorrectionAction.LOCAL_CORRECTION
    assert decision.requires_reversal_journal is False
    assert decision.keeps_original_immutable is False
    assert decision.audit_required is True
    assert decision.reason_code == "LOCAL_ONLY_NOT_SYNCED"


def test_synced_to_erp_but_not_posted_uses_void_or_correction_document():
    decision = decide_correction_action(
        sync_state=TransactionSyncState.SYNCED_TO_ERP,
        accounting_state=TransactionAccountingState.NOT_POSTED,
    )

    assert decision.action is CorrectionAction.ERP_VOID_OR_CORRECTION
    assert decision.requires_reversal_journal is False
    assert decision.keeps_original_immutable is True
    assert decision.reason_code == "SYNCED_NOT_POSTED"


def test_posted_journal_requires_reversal_and_correction_journal():
    decision = decide_correction_action(
        sync_state=TransactionSyncState.SYNCED_TO_ERP,
        accounting_state=TransactionAccountingState.POSTED,
    )

    assert decision.action is CorrectionAction.REVERSAL_AND_CORRECTION_JOURNAL
    assert decision.requires_reversal_journal is True
    assert decision.requires_correction_journal is True
    assert decision.keeps_original_immutable is True
    assert decision.reason_code == "POSTED_JOURNAL_EXISTS"


def test_verified_payment_cancelled_uses_refund_workflow_linked_to_original():
    decision = decide_correction_action(
        sync_state=TransactionSyncState.SYNCED_TO_ERP,
        accounting_state=TransactionAccountingState.POSTED,
        payment_verified=True,
        service_cancelled=True,
    )

    assert decision.action is CorrectionAction.REFUND_WORKFLOW
    assert decision.requires_linked_original_payment is True
    assert decision.requires_reversal_journal is True
    assert decision.reason_code == "PAYMENT_VERIFIED_SERVICE_CANCELLED"


def test_duplicate_event_detected_is_ignored_and_audited_by_idempotency_key():
    decision = decide_correction_action(
        sync_state=TransactionSyncState.DUPLICATE_EVENT,
        accounting_state=TransactionAccountingState.NOT_POSTED,
        idempotency_key="JKT01:POSA:TMP-JKT01-POSA-20260526-000007",
    )

    assert decision.action is CorrectionAction.IGNORE_DUPLICATE
    assert decision.audit_required is True
    assert decision.idempotency_key == "JKT01:POSA:TMP-JKT01-POSA-20260526-000007"
    assert decision.reason_code == "DUPLICATE_EVENT_DETECTED"
