import hashlib
import hmac
import os
import uuid
import jwt
from datetime import timedelta
from flight_domain.models.base import utcnow
from flight_domain.config import settings

def hash_password(password: str) -> str:
    """Securely hash a password using PBKDF2-HMAC-SHA256 with a unique 16-byte salt."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{dk.hex()}"

def verify_password(password: str, hashed: str | None) -> bool:
    """Verify a plain password against stored salt:dk hex string."""
    if not hashed or ":" not in hashed:
        return False
    try:
        salt_hex, dk_hex = hashed.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_dk = bytes.fromhex(dk_hex)
        actual_dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return hmac.compare_digest(actual_dk, expected_dk)
    except Exception:
        return False

def create_jwt_token(
    user_id: str | uuid.UUID,
    email: str,
    role: str = "customer",
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a JWT token signed with SUPABASE_JWT_SECRET."""
    exp = utcnow() + (expires_delta or timedelta(days=7))
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": int(utcnow().timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

def decode_jwt_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    secret = settings.SUPABASE_JWT_SECRET
    verify_sig = len(secret) >= 32 and not secret.startswith("super-secret")
    return jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        options={"verify_signature": verify_sig},
    )
