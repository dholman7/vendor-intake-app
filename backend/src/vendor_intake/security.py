import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

import jwt

from vendor_intake.db import User, utcnow

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, salt_hex, digest_hex = stored.split("$")
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **_SCRYPT)
    return hmac.compare_digest(digest.hex(), digest_hex)


# Verified against when the email is unknown, so both failure paths cost the same time.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def check_credentials(user: User | None, password: str) -> bool:
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return False
    return verify_password(password, user.password_hash)


def issue_token(user: User, secret: str, ttl_minutes: int) -> str:
    now = utcnow()
    claims = {
        "sub": user.id,
        "tid": user.tenant_id,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
    }
    return jwt.encode(claims, secret, algorithm=_ALGORITHM)


def decode_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        claims: dict[str, Any] = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return claims
