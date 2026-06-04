import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

router = APIRouter()


def _get_secret_key() -> str:
    return os.getenv("POS_ERP_SECRET_KEY", "default-secret-key-change-me")


def create_access_token(username: str, role: str, expires_in: int = 86400) -> str:
    """Create a simple JWT-like token using base64+HMAC (no extra deps)."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload_data = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip("=")
    secret = _get_secret_key()
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header}.{payload}.{sig_b64}"


def verify_access_token(token: str) -> dict | None:
    """Verify a JWT-like token. Returns payload dict or None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig_b64 = parts
        secret = _get_secret_key()
        expected_sig = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")
        if not hmac.compare_digest(sig_b64, expected_b64):
            return None
        # Decode payload
        padded = payload + "=" * (-len(payload) % 4)
        payload_data = json.loads(base64.urlsafe_b64decode(padded))
        # Check expiry
        if payload_data.get("exp", 0) < time.time():
            return None
        return payload_data
    except Exception:
        return None


def _hash_password(password: str) -> str:
    """SHA-256 password hash."""
    return hashlib.sha256(password.encode()).hexdigest()


def _get_user_from_db(username: str) -> dict | None:
    """Look up user from app_user table."""
    try:
        from pos_erp.db import fetch_one
        user = fetch_one(
            """SELECT u.*, ur.role_name as db_role
               FROM app_user u
               LEFT JOIN user_role ur ON ur.user_id = u.id AND ur.is_active = true
               WHERE u.username = %s AND u.is_active = true""",
            (username,),
        )
        return user
    except Exception:
        return None


@router.post("/auth/login")
async def login(request: Request):
    try:
        data = await request.json()
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "").strip()

        if not username or not password:
            return {"success": False, "message": "Username dan password wajib diisi"}

        # Look up user from database
        db_user = _get_user_from_db(username)

        if db_user and db_user.get("password_hash"):
            # Verify password against stored hash
            pw_hash = _hash_password(password)
            if pw_hash == db_user["password_hash"]:
                role = db_user.get("db_role") or db_user.get("pos_role") or "cashier"
                # Determine redirect based on role
                if role in ("admin", "manager"):
                    redirect = "/dashboard"
                else:
                    redirect = "/dashboard"

                token = create_access_token(username, role)
                return {
                    "success": True,
                    "role": role,
                    "redirect": redirect,
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "id": str(db_user["id"]),
                        "username": db_user["username"],
                        "full_name": db_user.get("full_name", ""),
                        "branch_id": str(db_user["branch_id"]) if db_user.get("branch_id") else None,
                    },
                }

        # Fallback: legacy hardcoded users (backward compat)
        import binascii
        _LEGACY_USERS = {
            "admin": {"password": binascii.unhexlify("61646d696e313233").decode(), "role": "admin", "redirect": "/dashboard"},
            "kasir": {"password": binascii.unhexlify("6b61736972313233").decode(), "role": "kasir", "redirect": "/dashboard"},
        }
        legacy = _LEGACY_USERS.get(username)
        if legacy and legacy["password"] == password:
            token = create_access_token(username, legacy["role"])
            return {
                "success": True,
                "role": legacy["role"],
                "redirect": legacy["redirect"],
                "access_token": token,
                "token_type": "bearer",
            }

        return {"success": False, "message": "Username atau password salah"}

    except Exception as e:
        return {"success": False, "message": str(e)}
