"""Security utilities: JWT, password hashing, RBAC."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Password Hashing ────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ──────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str,
    additional_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: User ID (sub claim).
        role: User role for RBAC.
        additional_claims: Extra claims to include.
        expires_delta: Token expiry duration (default: 15 minutes).

    Returns:
        Signed JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    if additional_claims:
        claims.update(additional_claims)

    return jwt.encode(claims, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token.

    Args:
        subject: User ID (sub claim).
        role: User role.
        expires_delta: Token expiry (default: 7 days).

    Returns:
        Signed JWT string.
    """
    if expires_delta is None:
        expires_delta = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
        "type": "refresh",
    }
    return jwt.encode(claims, settings.jwt_private_key, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: The encoded JWT string.

    Returns:
        Decoded payload dictionary.

    Raises:
        JWTError: If the token is invalid or expired.
    """
    return jwt.decode(
        token,
        settings.jwt_public_key,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ── RBAC ────────────────────────────────────────────────────────────

ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 0,
    "coordinator": 1,
    "clinician": 2,
    "admin": 3,
}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "viewer": [
        "dashboard:read",
        "patients:read",
        "predictions:read",
        "models:read",
    ],
    "coordinator": [
        "dashboard:read",
        "patients:read",
        "predictions:read",
        "models:read",
        "workflows:read",
        "workflows:write",
    ],
    "clinician": [
        "dashboard:read",
        "patients:read",
        "patients:write",
        "predictions:read",
        "predictions:write",
        "models:read",
    ],
    "admin": [
        "dashboard:read",
        "patients:read",
        "patients:write",
        "predictions:read",
        "predictions:write",
        "models:read",
        "models:write",
        "workflows:read",
        "workflows:write",
        "audit:read",
        "users:read",
        "users:write",
        "training:read",
        "training:write",
    ],
}


def has_permission(role: str, required_permission: str) -> bool:
    """Check if a role has a specific permission.

    Args:
        role: The user's role.
        required_permission: The permission string to check.

    Returns:
        True if the role has the permission.
    """
    permissions = ROLE_PERMISSIONS.get(role, [])
    return required_permission in permissions


def has_role(user_role: str, minimum_role: str) -> bool:
    """Check if a user's role meets or exceeds a minimum role level.

    Args:
        user_role: The user's current role.
        minimum_role: The minimum required role.

    Returns:
        True if the user's role level >= minimum role level.
    """
    user_level = ROLE_HIERARCHY.get(user_role, -1)
    required_level = ROLE_HIERARCHY.get(minimum_role, -1)
    return user_level >= required_level