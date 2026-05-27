
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pos_erp.permissions import Action, Role, authorize_action


class PeriodLockDecision(str, Enum):
    ALLOWED = "ALLOWED"
    ALLOWED_CONTROLLED_ADJUSTMENT = "ALLOWED_CONTROLLED_ADJUSTMENT"
    BLOCKED_PERIOD_LOCKED = "BLOCKED_PERIOD_LOCKED"
    BLOCKED_ROLE_NOT_AUTHORIZED = "BLOCKED_ROLE_NOT_AUTHORIZED"
    BLOCKED_REASON_REQUIRED = "BLOCKED_REASON_REQUIRED"


@dataclass(frozen=True)
class PeriodLock:
    is_locked: bool
    period_id: str | None = None


_CONTROLLED_ACTIONS = {Action.REFUND_AFTER_POSTING, Action.PERIOD_UNLOCK}


def evaluate_period_action(lock: PeriodLock, action: Action, role: Role, *, reason: str | None = None) -> PeriodLockDecision:
    auth = authorize_action(role, action)
    if not auth.allowed:
        return PeriodLockDecision.BLOCKED_ROLE_NOT_AUTHORIZED
    if action is Action.PERIOD_UNLOCK and not reason:
        return PeriodLockDecision.BLOCKED_REASON_REQUIRED
    if not lock.is_locked:
        return PeriodLockDecision.ALLOWED
    if action in _CONTROLLED_ACTIONS:
        return PeriodLockDecision.ALLOWED_CONTROLLED_ADJUSTMENT
    return PeriodLockDecision.BLOCKED_PERIOD_LOCKED
