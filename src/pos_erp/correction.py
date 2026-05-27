from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TransactionSyncState(str, Enum):
    LOCAL_ONLY = "LOCAL_ONLY"
    SYNCED_TO_ERP = "SYNCED_TO_ERP"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"


class TransactionAccountingState(str, Enum):
    NOT_POSTED = "NOT_POSTED"
    POSTED = "POSTED"


class CorrectionAction(str, Enum):
    LOCAL_CORRECTION = "LOCAL_CORRECTION"
    ERP_VOID_OR_CORRECTION = "ERP_VOID_OR_CORRECTION"
    REVERSAL_AND_CORRECTION_JOURNAL = "REVERSAL_AND_CORRECTION_JOURNAL"
    REFUND_WORKFLOW = "REFUND_WORKFLOW"
    IGNORE_DUPLICATE = "IGNORE_DUPLICATE"


@dataclass(frozen=True)
class CorrectionDecision:
    action: CorrectionAction
    reason_code: str
    requires_reversal_journal: bool = False
    requires_correction_journal: bool = False
    requires_linked_original_payment: bool = False
    keeps_original_immutable: bool = False
    audit_required: bool = True
    idempotency_key: str | None = None


def decide_correction_action(
    *,
    sync_state: TransactionSyncState,
    accounting_state: TransactionAccountingState,
    payment_verified: bool = False,
    service_cancelled: bool = False,
    idempotency_key: str | None = None,
) -> CorrectionDecision:
    if sync_state is TransactionSyncState.DUPLICATE_EVENT:
        return CorrectionDecision(
            action=CorrectionAction.IGNORE_DUPLICATE,
            reason_code="DUPLICATE_EVENT_DETECTED",
            idempotency_key=idempotency_key,
        )

    if payment_verified and service_cancelled:
        return CorrectionDecision(
            action=CorrectionAction.REFUND_WORKFLOW,
            reason_code="PAYMENT_VERIFIED_SERVICE_CANCELLED",
            requires_reversal_journal=accounting_state is TransactionAccountingState.POSTED,
            requires_linked_original_payment=True,
            keeps_original_immutable=True,
        )

    if sync_state is TransactionSyncState.LOCAL_ONLY:
        return CorrectionDecision(
            action=CorrectionAction.LOCAL_CORRECTION,
            reason_code="LOCAL_ONLY_NOT_SYNCED",
            keeps_original_immutable=False,
        )

    if accounting_state is TransactionAccountingState.POSTED:
        return CorrectionDecision(
            action=CorrectionAction.REVERSAL_AND_CORRECTION_JOURNAL,
            reason_code="POSTED_JOURNAL_EXISTS",
            requires_reversal_journal=True,
            requires_correction_journal=True,
            keeps_original_immutable=True,
        )

    return CorrectionDecision(
        action=CorrectionAction.ERP_VOID_OR_CORRECTION,
        reason_code="SYNCED_NOT_POSTED",
        keeps_original_immutable=True,
    )
