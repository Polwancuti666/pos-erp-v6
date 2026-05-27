
from pos_erp.exception_queue import ExceptionQueue, ExceptionStatus, ExceptionType


def test_sync_failure_exception_gets_it_and_manager_owner_with_two_hour_sla():
    queue = ExceptionQueue()
    item = queue.add(ExceptionType.SYNC_FAILURE, reference_id="TMP-001", created_at="2026-05-26T10:00:00+07:00")
    assert item.owner_roles == ("IT_ADMIN", "BRANCH_MANAGER")
    assert item.sla_hours == 2
    assert item.status is ExceptionStatus.OPEN


def test_unmapped_coa_exception_owned_by_accounting_with_one_business_day_sla():
    item = ExceptionQueue().add(ExceptionType.UNMAPPED_COA, reference_id="TRX-001", created_at="2026-05-26T10:00:00+07:00")
    assert item.owner_roles == ("ACCOUNTING_LEAD",)
    assert item.sla_hours == 24


def test_queue_isolates_failed_items_and_allows_unrelated_items_to_continue():
    queue = ExceptionQueue()
    failed = queue.add(ExceptionType.PAYLOAD_VALIDATION, reference_id="TMP-001", created_at="2026-05-26T10:00:00+07:00")
    valid = queue.add(ExceptionType.PAYMENT_REVIEW_REQUIRED, reference_id="TRX-002", created_at="2026-05-26T10:05:00+07:00")
    queue.resolve(failed.exception_id, resolved_by="it-1", resolution="payload corrected")
    assert queue.get(failed.exception_id).status is ExceptionStatus.RESOLVED
    assert queue.get(valid.exception_id).status is ExceptionStatus.OPEN


def test_overdue_exception_is_detected_from_sla():
    queue = ExceptionQueue()
    item = queue.add(ExceptionType.DUPLICATE_EVENT, reference_id="TRX-003", created_at="2026-05-26T10:00:00+07:00")
    assert item.sla_hours == 4
    assert queue.overdue_items(now="2026-05-26T15:00:01+07:00") == [item]
