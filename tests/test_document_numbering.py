
from pos_erp.document_numbering import DocumentKind, NumberingService


def test_pos_trm_jrn_numbers_are_unique_by_branch_date_and_server_sequence():
    service = NumberingService()
    jkt = service.issue(DocumentKind.POS, branch_code="JKT01", business_date="20260526")
    bdg = service.issue(DocumentKind.POS, branch_code="BDG01", business_date="20260526")
    next_jkt = service.issue(DocumentKind.POS, branch_code="JKT01", business_date="20260526")
    assert jkt == "POS-JKT01-20260526-000001"
    assert bdg == "POS-BDG01-20260526-000001"
    assert next_jkt == "POS-JKT01-20260526-000002"
    assert len({jkt, bdg, next_jkt}) == 3


def test_treatment_and_journal_sequences_are_independent_per_document_kind():
    service = NumberingService()
    trm = service.issue(DocumentKind.TRM, branch_code="JKT01", business_date="20260526")
    jrn = service.issue(DocumentKind.JRN, branch_code="JKT01", business_date="20260526")
    inv = service.issue(DocumentKind.INVENTORY_MOVEMENT, branch_code="JKT01", business_date="20260526")
    assert trm == "TRM-JKT01-20260526-000001"
    assert jrn == "JRN-JKT01-20260526-000001"
    assert inv == "INV-MOV-JKT01-20260526-000001"


def test_numbering_service_can_replay_existing_sequence_without_collision():
    service = NumberingService(existing_counters={(DocumentKind.POS, "JKT01", "20260526"): 41})
    assert service.issue(DocumentKind.POS, branch_code="JKT01", business_date="20260526") == "POS-JKT01-20260526-000042"
