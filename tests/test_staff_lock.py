from datetime import datetime, timedelta, timezone

import pytest

from pos_erp.staff_lock import (
    LockReleaseReason,
    LockStatus,
    StaffAlreadyLocked,
    StaffLockManager,
)


def test_reserving_staff_creates_active_10_minute_lock():
    now = datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc)
    manager = StaffLockManager()

    lock = manager.reserve(
        staff_id="staff-1",
        transaction_id="TMP-JKT01-POSA-20260526-000001",
        branch_code="JKT01",
        device_id="POSA",
        actor_id="cashier-1",
        now=now,
    )

    assert lock.staff_id == "staff-1"
    assert lock.status is LockStatus.ACTIVE
    assert lock.locked_until == now + timedelta(minutes=10)
    assert lock.branch_code == "JKT01"
    assert lock.device_id == "POSA"


def test_active_staff_lock_blocks_second_reservation_until_released():
    now = datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc)
    manager = StaffLockManager()
    manager.reserve(
        staff_id="staff-1",
        transaction_id="TMP-JKT01-POSA-20260526-000001",
        branch_code="JKT01",
        device_id="POSA",
        actor_id="cashier-1",
        now=now,
    )

    with pytest.raises(StaffAlreadyLocked):
        manager.reserve(
            staff_id="staff-1",
            transaction_id="TMP-JKT01-POSA-20260526-000002",
            branch_code="JKT01",
            device_id="POSA",
            actor_id="cashier-2",
            now=now + timedelta(minutes=1),
        )


def test_manager_release_marks_lock_released_and_creates_audit_log():
    now = datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc)
    manager = StaffLockManager()
    lock = manager.reserve(
        staff_id="staff-1",
        transaction_id="TMP-JKT01-POSA-20260526-000001",
        branch_code="JKT01",
        device_id="POSA",
        actor_id="cashier-1",
        now=now,
    )

    released = manager.release(
        lock_id=lock.lock_id,
        reason=LockReleaseReason.MANAGER_RELEASE,
        actor_id="manager-1",
        now=now + timedelta(minutes=2),
    )

    assert released.status is LockStatus.RELEASED
    audit = manager.audit_logs[-1]
    assert audit.lock_id == lock.lock_id
    assert audit.actor_id == "manager-1"
    assert audit.reason is LockReleaseReason.MANAGER_RELEASE
    assert audit.branch_code == "JKT01"
    assert audit.device_id == "POSA"
    assert audit.timestamp == now + timedelta(minutes=2)


def test_expired_lock_auto_releases_with_system_audit_log():
    now = datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc)
    manager = StaffLockManager()
    lock = manager.reserve(
        staff_id="staff-1",
        transaction_id="TMP-JKT01-POSA-20260526-000001",
        branch_code="JKT01",
        device_id="POSA",
        actor_id="cashier-1",
        now=now,
    )

    released = manager.release_expired(now=now + timedelta(minutes=10, seconds=1))

    assert released == [lock.lock_id]
    assert manager.get(lock.lock_id).status is LockStatus.RELEASED
    audit = manager.audit_logs[-1]
    assert audit.actor_id == "system"
    assert audit.reason is LockReleaseReason.TIMEOUT
    assert audit.branch_code == "JKT01"
    assert audit.device_id == "POSA"
