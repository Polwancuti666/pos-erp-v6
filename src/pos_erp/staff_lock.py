from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum


class LockStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class LockReleaseReason(str, Enum):
    CANCEL = "CANCEL"
    PAYMENT_EXPIRATION = "PAYMENT_EXPIRATION"
    MANAGER_RELEASE = "MANAGER_RELEASE"
    TIMEOUT = "TIMEOUT"


@dataclass(frozen=True)
class StaffLock:
    lock_id: str
    staff_id: str
    transaction_id: str
    branch_code: str
    device_id: str
    actor_id: str
    locked_at: datetime
    locked_until: datetime
    status: LockStatus = LockStatus.ACTIVE


@dataclass(frozen=True)
class StaffLockAuditLog:
    lock_id: str
    staff_id: str
    transaction_id: str
    branch_code: str
    device_id: str
    actor_id: str
    timestamp: datetime
    reason: LockReleaseReason


class StaffAlreadyLocked(Exception):
    pass


class StaffLockNotFound(Exception):
    pass


class StaffLockManager:
    def __init__(self) -> None:
        self._locks: dict[str, StaffLock] = {}
        self.audit_logs: list[StaffLockAuditLog] = []

    def reserve(
        self,
        *,
        staff_id: str,
        transaction_id: str,
        branch_code: str,
        device_id: str,
        actor_id: str,
        now: datetime,
    ) -> StaffLock:
        for existing in self._locks.values():
            if existing.staff_id == staff_id and existing.status is LockStatus.ACTIVE and existing.locked_until > now:
                raise StaffAlreadyLocked(f"Staff {staff_id} is locked until {existing.locked_until.isoformat()}")

        lock_id = f"LOCK-{branch_code}-{staff_id}-{transaction_id}"
        lock = StaffLock(
            lock_id=lock_id,
            staff_id=staff_id,
            transaction_id=transaction_id,
            branch_code=branch_code,
            device_id=device_id,
            actor_id=actor_id,
            locked_at=now,
            locked_until=now + timedelta(minutes=10),
        )
        self._locks[lock_id] = lock
        return lock

    def get(self, lock_id: str) -> StaffLock:
        try:
            return self._locks[lock_id]
        except KeyError as exc:
            raise StaffLockNotFound(lock_id) from exc

    def release(
        self,
        *,
        lock_id: str,
        reason: LockReleaseReason,
        actor_id: str,
        now: datetime,
    ) -> StaffLock:
        lock = self.get(lock_id)
        released = replace(lock, status=LockStatus.RELEASED)
        self._locks[lock_id] = released
        self.audit_logs.append(
            StaffLockAuditLog(
                lock_id=lock.lock_id,
                staff_id=lock.staff_id,
                transaction_id=lock.transaction_id,
                branch_code=lock.branch_code,
                device_id=lock.device_id,
                actor_id=actor_id,
                timestamp=now,
                reason=reason,
            )
        )
        return released

    def release_expired(self, *, now: datetime) -> list[str]:
        released_ids: list[str] = []
        for lock in list(self._locks.values()):
            if lock.status is LockStatus.ACTIVE and lock.locked_until <= now:
                self.release(
                    lock_id=lock.lock_id,
                    reason=LockReleaseReason.TIMEOUT,
                    actor_id="system",
                    now=now,
                )
                released_ids.append(lock.lock_id)
        return released_ids
