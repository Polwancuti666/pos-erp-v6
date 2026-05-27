
from __future__ import annotations
import base64, hashlib, hmac
from dataclasses import dataclass

@dataclass(frozen=True)
class SecretPolicy:
    allowed: bool
    violations: tuple[str, ...]

class EncryptionService:
    def __init__(self, secret_key: str):
        self._key = hashlib.sha256(secret_key.encode()).digest()
    def encrypt(self, plaintext: str) -> str:
        data = plaintext.encode()
        stream = self._keystream(len(data))
        cipher = bytes(b ^ stream[i] for i, b in enumerate(data))
        mac = hmac.new(self._key, cipher, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(mac + cipher).decode()
    def decrypt(self, ciphertext: str) -> str | None:
        try:
            raw = base64.urlsafe_b64decode(ciphertext.encode())
            mac, cipher = raw[:32], raw[32:]
            expected = hmac.new(self._key, cipher, hashlib.sha256).digest()
            if not hmac.compare_digest(mac, expected):
                return None
            stream = self._keystream(len(cipher))
            return bytes(b ^ stream[i] for i, b in enumerate(cipher)).decode()
        except Exception:
            return None
    def _keystream(self, size: int) -> bytes:
        out = b""
        counter = 0
        while len(out) < size:
            out += hashlib.sha256(self._key + counter.to_bytes(4, "big")).digest()
            counter += 1
        return out[:size]

def verify_production_security(*, environment: str, secret_key: str, local_store_encrypted: bool) -> SecretPolicy:
    violations = []
    if environment == "production":
        if secret_key == "dev-only-change-me":
            violations.append("PLACEHOLDER_SECRET")
        if not local_store_encrypted:
            violations.append("LOCAL_STORE_NOT_ENCRYPTED")
    return SecretPolicy(allowed=not violations, violations=tuple(violations))
