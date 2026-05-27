
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    CASHIER = "cashier"
    BRANCH_MANAGER = "branch_manager"
    ACCOUNTING_LEAD = "accounting_lead"
    IT_ADMIN = "it_admin"
    OWNER = "owner"


class Action(str, Enum):
    CREATE_SALE = "create_sale"
    EDIT_TREATMENT_BEFORE_PAYMENT = "edit_treatment_before_payment"
    APPROVE_MANUAL_SYNC = "approve_manual_sync"
    RELEASE_STAFF_LOCK = "release_staff_lock"
    DISCOUNT_OVERRIDE = "discount_override"
    VOID_BEFORE_POSTING = "void_before_posting"
    VERIFY_MANUAL_PAYMENT = "verify_manual_payment"
    REFUND_AFTER_POSTING = "refund_after_posting"
    COA_MAPPING_CHANGE = "coa_mapping_change"
    PERIOD_LOCK = "period_lock"
    PERIOD_UNLOCK = "period_unlock"


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    action: Action
    role: Role
    required_roles: tuple[Role, ...]
    audit_required: bool
    denial_reason: str | None = None


_POLICY: dict[Action, tuple[Role, ...]] = {
    Action.CREATE_SALE: (Role.CASHIER, Role.BRANCH_MANAGER, Role.OWNER),
    Action.EDIT_TREATMENT_BEFORE_PAYMENT: (Role.CASHIER, Role.BRANCH_MANAGER, Role.OWNER),
    Action.APPROVE_MANUAL_SYNC: (Role.BRANCH_MANAGER, Role.OWNER, Role.IT_ADMIN),
    Action.RELEASE_STAFF_LOCK: (Role.BRANCH_MANAGER, Role.IT_ADMIN),
    Action.DISCOUNT_OVERRIDE: (Role.BRANCH_MANAGER, Role.OWNER),
    Action.VOID_BEFORE_POSTING: (Role.BRANCH_MANAGER, Role.ACCOUNTING_LEAD),
    Action.VERIFY_MANUAL_PAYMENT: (Role.ACCOUNTING_LEAD, Role.BRANCH_MANAGER, Role.OWNER),
    Action.REFUND_AFTER_POSTING: (Role.ACCOUNTING_LEAD, Role.OWNER),
    Action.COA_MAPPING_CHANGE: (Role.ACCOUNTING_LEAD, Role.OWNER),
    Action.PERIOD_LOCK: (Role.ACCOUNTING_LEAD, Role.OWNER),
    Action.PERIOD_UNLOCK: (Role.OWNER,),
}


def authorize_action(role: Role, action: Action) -> AuthorizationDecision:
    required = _POLICY[action]
    allowed = role in required
    return AuthorizationDecision(
        allowed=allowed,
        action=action,
        role=role,
        required_roles=required,
        audit_required=not allowed or action not in {Action.CREATE_SALE, Action.EDIT_TREATMENT_BEFORE_PAYMENT},
        denial_reason=None if allowed else "ROLE_NOT_AUTHORIZED",
    )
