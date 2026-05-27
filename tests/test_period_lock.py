
from pos_erp.period_lock import PeriodLock, PeriodLockDecision, evaluate_period_action
from pos_erp.permissions import Action, Role


def test_open_period_allows_normal_edit_or_void_before_posting():
    decision = evaluate_period_action(PeriodLock(is_locked=False), Action.VOID_BEFORE_POSTING, Role.BRANCH_MANAGER)
    assert decision is PeriodLockDecision.ALLOWED


def test_locked_period_blocks_direct_edit_or_void():
    decision = evaluate_period_action(PeriodLock(is_locked=True), Action.VOID_BEFORE_POSTING, Role.BRANCH_MANAGER)
    assert decision is PeriodLockDecision.BLOCKED_PERIOD_LOCKED


def test_locked_period_allows_accounting_reversal_or_refund_workflow():
    decision = evaluate_period_action(PeriodLock(is_locked=True), Action.REFUND_AFTER_POSTING, Role.ACCOUNTING_LEAD)
    assert decision is PeriodLockDecision.ALLOWED_CONTROLLED_ADJUSTMENT


def test_unlock_requires_owner_role_and_reason():
    locked = PeriodLock(is_locked=True)
    assert evaluate_period_action(locked, Action.PERIOD_UNLOCK, Role.ACCOUNTING_LEAD, reason="month end fix") is PeriodLockDecision.BLOCKED_ROLE_NOT_AUTHORIZED
    assert evaluate_period_action(locked, Action.PERIOD_UNLOCK, Role.OWNER, reason="approved correction") is PeriodLockDecision.ALLOWED_CONTROLLED_ADJUSTMENT
    assert evaluate_period_action(locked, Action.PERIOD_UNLOCK, Role.OWNER, reason="") is PeriodLockDecision.BLOCKED_REASON_REQUIRED
