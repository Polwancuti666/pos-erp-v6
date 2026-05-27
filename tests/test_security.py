
from pos_erp.security import EncryptionService, SecretPolicy, verify_production_security


def test_encryption_service_round_trips_local_store_payload_without_plaintext_token():
    service = EncryptionService(secret_key="unit-test-secret")
    ciphertext = service.encrypt("customer=Jane;amount=100000")
    assert ciphertext != "customer=Jane;amount=100000"
    assert "Jane" not in ciphertext
    assert service.decrypt(ciphertext) == "customer=Jane;amount=100000"


def test_ciphertext_detects_tampering():
    service = EncryptionService(secret_key="unit-test-secret")
    ciphertext = service.encrypt("offline payload")
    assert service.decrypt(ciphertext[:-2] + "xx") is None


def test_production_security_fails_when_placeholder_secret_or_unencrypted_store():
    policy = verify_production_security(
        environment="production",
        secret_key="dev-only-change-me",
        local_store_encrypted=False,
    )
    assert policy.allowed is False
    assert "PLACEHOLDER_SECRET" in policy.violations
    assert "LOCAL_STORE_NOT_ENCRYPTED" in policy.violations


def test_non_production_security_allows_placeholder_for_local_dev():
    policy = verify_production_security(
        environment="local",
        secret_key="dev-only-change-me",
        local_store_encrypted=False,
    )
    assert policy.allowed is True
    assert policy.violations == ()
