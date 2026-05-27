
from pos_erp.permissions import Action, Role, authorize_action


def test_cashier_can_create_sale_and_edit_treatment_before_payment():
    assert authorize_action(Role.CASHIER, Action.CREATE_SALE).allowed is True
    decision = authorize_action(Role.CASHIER, Action.EDIT_TREATMENT_BEFORE_PAYMENT)
    assert decision.allowed is True
    assert decision.audit_required is False


def test_manager_can_approve_manual_sync_release_lock_and_void_before_posting():
    assert authorize_action(Role.BRANCH_MANAGER, Action.APPROVE_MANUAL_SYNC).allowed is True
    assert authorize_action(Role.BRANCH_MANAGER, Action.RELEASE_STAFF_LOCK).allowed is True
    assert authorize_action(Role.BRANCH_MANAGER, Action.VOID_BEFORE_POSTING).allowed is True


def test_accounting_lead_can_verify_manual_payment_refund_after_posting_and_lock_period():
    assert authorize_action(Role.ACCOUNTING_LEAD, Action.VERIFY_MANUAL_PAYMENT).allowed is True
    assert authorize_action(Role.ACCOUNTING_LEAD, Action.REFUND_AFTER_POSTING).allowed is True
    assert authorize_action(Role.ACCOUNTING_LEAD, Action.PERIOD_LOCK).allowed is True


def test_owner_is_backup_approver_for_manager_and_accounting_controls():
    assert authorize_action(Role.OWNER, Action.APPROVE_MANUAL_SYNC).allowed is True
    assert authorize_action(Role.OWNER, Action.DISCOUNT_OVERRIDE).allowed is True
    assert authorize_action(Role.OWNER, Action.PERIOD_UNLOCK).allowed is True


def test_unauthorized_action_is_rejected_with_auditable_denial_reason():
    decision = authorize_action(Role.CASHIER, Action.REFUND_AFTER_POSTING)
    assert decision.allowed is False
    assert decision.audit_required is True
    assert decision.denial_reason == "ROLE_NOT_AUTHORIZED"
    assert Role.ACCOUNTING_LEAD in decision.required_roles
