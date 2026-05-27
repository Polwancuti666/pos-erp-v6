
from pos_erp.audit_log import AuditLog, AuditSeverity


def test_audit_log_records_state_change_with_actor_branch_device_and_metadata():
    log = AuditLog()
    entry = log.record(
        action="PAYMENT_APPROVED",
        actor_id="finance-1",
        branch_code="JKT01",
        device_id="BACKOFFICE",
        reference_id="TRX-001",
        severity=AuditSeverity.INFO,
        metadata={"from": "PAYMENT_REVIEW_REQUIRED", "to": "PAID"},
    )
    assert entry.audit_id == "AUD-000001"
    assert entry.metadata["to"] == "PAID"
    assert log.for_reference("TRX-001") == [entry]


def test_audit_log_filters_by_severity():
    log = AuditLog()
    log.record("OK", "u1", "JKT01", "POSA", "TRX-1", AuditSeverity.INFO, {})
    warning = log.record("DENIED", "u2", "JKT01", "POSA", "TRX-2", AuditSeverity.WARNING, {})
    assert log.by_severity(AuditSeverity.WARNING) == [warning]
