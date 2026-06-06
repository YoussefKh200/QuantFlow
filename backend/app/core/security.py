"""
Security utilities: JWT RS256 token management + Argon2 password hashing.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Argon2 is the winner of the Password Hashing Competition — use it
pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def _load_key(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"JWT key not found: {path}")
    return p.read_text().strip()


class JWTManager:
    ALGORITHM = "RS256"

    def __init__(self) -> None:
        self._private_key: str | None = None
        self._public_key: str | None = None

    def _ensure_keys(self) -> None:
        if self._private_key is None:
            self._private_key = _load_key(settings.JWT_PRIVATE_KEY_PATH)
        if self._public_key is None:
            self._public_key = _load_key(settings.JWT_PUBLIC_KEY_PATH)

    def create_access_token(self, user_id: str, role: str) -> str:
        self._ensure_keys()
        now = datetime.now(tz=timezone.utc)
        payload = {
            "sub": user_id,
            "role": role,
            "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_TTL_MINUTES),
            "iat": now,
            "type": "access",
        }
        return jwt.encode(payload, self._private_key, algorithm=self.ALGORITHM)

    def create_refresh_token(self, user_id: str) -> tuple[str, str]:
        """Returns (token, jti) — jti is stored in Redis for revocation."""
        self._ensure_keys()
        now = datetime.now(tz=timezone.utc)
        jti = secrets.token_urlsafe(32)
        payload = {
            "sub": user_id,
            "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_TTL_DAYS),
            "iat": now,
            "type": "refresh",
            "jti": jti,
        }
        token = jwt.encode(payload, self._private_key, algorithm=self.ALGORITHM)
        return token, jti

    def verify_token(self, token: str, expected_type: str = "access") -> dict:
        """
        Raises jwt.InvalidTokenError on failure.
        Caller should wrap in try/except.
        """
        self._ensure_keys()
        payload = jwt.decode(
            token,
            self._public_key,
            algorithms=[self.ALGORITHM],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
        if payload.get("type") != expected_type:
            raise jwt.InvalidTokenError(f"Expected token type '{expected_type}'")
        return payload

    def decode_unverified(self, token: str) -> dict:
        """Extract payload without verification — used for getting jti on logout."""
        return jwt.decode(token, options={"verify_signature": False})


jwt_manager = JWTManager()
