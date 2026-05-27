from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class DocumentFinalizationStatus(str, Enum):
    PENDING_FINALIZATION = "PENDING_FINALIZATION"
    FINALIZED = "FINALIZED"
    FINALIZATION_FAILED = "FINALIZATION_FAILED"


@dataclass(frozen=True)
class DocumentNumbers:
    pos_number: str
    trm_number: str
    journal_number: str


@dataclass(frozen=True)
class OfflineTransactionRecord:
    local_temp_id: str
    branch_code: str
    device_id: str
    synced_to_erp: bool
    status: DocumentFinalizationStatus = DocumentFinalizationStatus.PENDING_FINALIZATION
    final_numbers: DocumentNumbers | None = None
    erp_response_id: str | None = None
    original_local_temp_id: str | None = None
    pending_finalization: bool = True
    last_error_code: str | None = None
    last_error_message: str | None = None


class FinalizationConflict(Exception):
    def __init__(
        self,
        message: str,
        *,
        local_temp_id: str,
        existing_numbers: DocumentNumbers | None = None,
        incoming_numbers: DocumentNumbers | None = None,
    ):
        super().__init__(message)
        self.local_temp_id = local_temp_id
        self.existing_numbers = existing_numbers
        self.incoming_numbers = incoming_numbers


def apply_erp_finalization(
    transaction: OfflineTransactionRecord,
    *,
    numbers: DocumentNumbers,
    erp_response_id: str,
) -> OfflineTransactionRecord:
    if not transaction.synced_to_erp:
        raise FinalizationConflict(
            f"Transaction {transaction.local_temp_id} is not synced to ERP; final numbers cannot be applied.",
            local_temp_id=transaction.local_temp_id,
            incoming_numbers=numbers,
        )

    if transaction.status is DocumentFinalizationStatus.FINALIZED:
        if transaction.final_numbers == numbers:
            return transaction
        raise FinalizationConflict(
            f"Conflicting final document numbers for {transaction.local_temp_id}.",
            local_temp_id=transaction.local_temp_id,
            existing_numbers=transaction.final_numbers,
            incoming_numbers=numbers,
        )

    return replace(
        transaction,
        status=DocumentFinalizationStatus.FINALIZED,
        final_numbers=numbers,
        erp_response_id=erp_response_id,
        original_local_temp_id=transaction.local_temp_id,
        pending_finalization=False,
        last_error_code=None,
        last_error_message=None,
    )


def mark_finalization_failed(
    transaction: OfflineTransactionRecord,
    *,
    error_code: str,
    error_message: str,
) -> OfflineTransactionRecord:
    return replace(
        transaction,
        status=DocumentFinalizationStatus.FINALIZATION_FAILED,
        pending_finalization=True,
        final_numbers=None,
        last_error_code=error_code,
        last_error_message=error_message,
    )
