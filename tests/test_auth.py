
from pos_erp.auth import AuthService, SessionStatus
from pos_erp.permissions import Role


def test_auth_service_creates_session_with_role_and_branch_scope():
    auth = AuthService(secret_key="session-secret")
    session = auth.create_session(user_id="cashier-1", role=Role.CASHIER, branch_code="JKT01", device_id="POSA")
    verified = auth.verify_session(session.token, branch_code="JKT01", device_id="POSA")
    assert verified.status is SessionStatus.ACTIVE
    assert verified.user_id == "cashier-1"
    assert verified.role is Role.CASHIER


def test_session_rejects_wrong_branch_or_device_binding():
    auth = AuthService(secret_key="session-secret")
    session = auth.create_session(user_id="cashier-1", role=Role.CASHIER, branch_code="JKT01", device_id="POSA")
    assert auth.verify_session(session.token, branch_code="BDG01", device_id="POSA").status is SessionStatus.BRANCH_OR_DEVICE_MISMATCH
    assert auth.verify_session(session.token, branch_code="JKT01", device_id="POSB").status is SessionStatus.BRANCH_OR_DEVICE_MISMATCH


def test_tampered_session_token_is_rejected():
    auth = AuthService(secret_key="session-secret")
    session = auth.create_session(user_id="owner-1", role=Role.OWNER, branch_code="HQ", device_id="WEB")
    assert auth.verify_session(session.token + "tamper", branch_code="HQ", device_id="WEB").status is SessionStatus.INVALID
