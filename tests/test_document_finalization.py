from pos_erp.document_finalization import (
    DocumentFinalizationStatus,
    DocumentNumbers,
    FinalizationConflict,
    OfflineTransactionRecord,
    apply_erp_finalization,
    mark_finalization_failed,
)


def test_synced_offline_transaction_receives_final_pos_trm_jrn_numbers():
    transaction = OfflineTransactionRecord(
        local_temp_id="TMP-JKT01-POSA-20260526-000007",
        branch_code="JKT01",
        device_id="POSA",
        synced_to_erp=True,
    )

    finalized = apply_erp_finalization(
        transaction,
        numbers=DocumentNumbers(
            pos_number="POS/JKT01/20260526/000123",
            trm_number="TRM/JKT01/20260526/000456",
            journal_number="JRN/JKT01/20260526/000789",
        ),
        erp_response_id="erp-finalize-1",
    )

    assert finalized.status is DocumentFinalizationStatus.FINALIZED
    assert finalized.local_temp_id == "TMP-JKT01-POSA-20260526-000007"
    assert finalized.final_numbers.pos_number == "POS/JKT01/20260526/000123"
    assert finalized.final_numbers.trm_number == "TRM/JKT01/20260526/000456"
    assert finalized.final_numbers.journal_number == "JRN/JKT01/20260526/000789"
    assert finalized.erp_response_id == "erp-finalize-1"
    assert finalized.pending_finalization is False


def test_local_temporary_id_remains_immutable_after_finalization():
    transaction = OfflineTransactionRecord(
        local_temp_id="TMP-BDG01-POSB-20260526-000012",
        branch_code="BDG01",
        device_id="POSB",
        synced_to_erp=True,
    )

    finalized = apply_erp_finalization(
        transaction,
        numbers=DocumentNumbers(
            pos_number="POS/BDG01/20260526/000001",
            trm_number="TRM/BDG01/20260526/000002",
            journal_number="JRN/BDG01/20260526/000003",
        ),
        erp_response_id="erp-finalize-2",
    )

    assert transaction.local_temp_id == "TMP-BDG01-POSB-20260526-000012"
    assert finalized.local_temp_id == transaction.local_temp_id
    assert finalized.original_local_temp_id == transaction.local_temp_id


def test_duplicate_numbering_response_is_idempotent_when_numbers_match():
    finalized = OfflineTransactionRecord(
        local_temp_id="TMP-JKT01-POSA-20260526-000007",
        branch_code="JKT01",
        device_id="POSA",
        synced_to_erp=True,
        status=DocumentFinalizationStatus.FINALIZED,
        final_numbers=DocumentNumbers(
            pos_number="POS/JKT01/20260526/000123",
            trm_number="TRM/JKT01/20260526/000456",
            journal_number="JRN/JKT01/20260526/000789",
        ),
        erp_response_id="erp-finalize-1",
    )

    repeated = apply_erp_finalization(
        finalized,
        numbers=DocumentNumbers(
            pos_number="POS/JKT01/20260526/000123",
            trm_number="TRM/JKT01/20260526/000456",
            journal_number="JRN/JKT01/20260526/000789",
        ),
        erp_response_id="erp-finalize-duplicate",
    )

    assert repeated is finalized
    assert repeated.status is DocumentFinalizationStatus.FINALIZED
    assert repeated.erp_response_id == "erp-finalize-1"


def test_conflicting_duplicate_numbering_response_is_rejected():
    finalized = OfflineTransactionRecord(
        local_temp_id="TMP-JKT01-POSA-20260526-000007",
        branch_code="JKT01",
        device_id="POSA",
        synced_to_erp=True,
        status=DocumentFinalizationStatus.FINALIZED,
        final_numbers=DocumentNumbers(
            pos_number="POS/JKT01/20260526/000123",
            trm_number="TRM/JKT01/20260526/000456",
            journal_number="JRN/JKT01/20260526/000789",
        ),
    )

    try:
        apply_erp_finalization(
            finalized,
            numbers=DocumentNumbers(
                pos_number="POS/JKT01/20260526/999999",
                trm_number="TRM/JKT01/20260526/000456",
                journal_number="JRN/JKT01/20260526/000789",
            ),
            erp_response_id="erp-conflict-1",
        )
    except FinalizationConflict as exc:
        assert exc.local_temp_id == "TMP-JKT01-POSA-20260526-000007"
        assert exc.existing_numbers.pos_number == "POS/JKT01/20260526/000123"
        assert exc.incoming_numbers.pos_number == "POS/JKT01/20260526/999999"
    else:
        raise AssertionError("Expected conflicting numbering response to be rejected")


def test_failed_finalization_remains_queued_without_corrupting_local_state():
    transaction = OfflineTransactionRecord(
        local_temp_id="TMP-SBY01-POSC-20260526-000009",
        branch_code="SBY01",
        device_id="POSC",
        synced_to_erp=True,
    )

    failed = mark_finalization_failed(
        transaction,
        error_code="ERP_TIMEOUT",
        error_message="ERP finalization timed out",
    )

    assert failed.status is DocumentFinalizationStatus.FINALIZATION_FAILED
    assert failed.pending_finalization is True
    assert failed.local_temp_id == transaction.local_temp_id
    assert failed.final_numbers is None
    assert failed.last_error_code == "ERP_TIMEOUT"
    assert failed.last_error_message == "ERP finalization timed out"


def test_unsynced_transaction_cannot_receive_final_erp_numbers():
    transaction = OfflineTransactionRecord(
        local_temp_id="TMP-DPS01-POSD-20260526-000010",
        branch_code="DPS01",
        device_id="POSD",
        synced_to_erp=False,
    )

    try:
        apply_erp_finalization(
            transaction,
            numbers=DocumentNumbers(
                pos_number="POS/DPS01/20260526/000001",
                trm_number="TRM/DPS01/20260526/000002",
                journal_number="JRN/DPS01/20260526/000003",
            ),
            erp_response_id="erp-finalize-unsynced",
        )
    except FinalizationConflict as exc:
        assert exc.local_temp_id == "TMP-DPS01-POSD-20260526-000010"
        assert "not synced" in str(exc)
    else:
        raise AssertionError("Expected unsynced transaction finalization to be rejected")
