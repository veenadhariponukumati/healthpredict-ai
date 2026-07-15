"""JWT Authentication middleware and dependency."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token, has_permission, has_role

# Bearer token scheme for OpenAPI documentation
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT Bearer token obtained from /auth/login",
)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Validate the JWT token and return the current user.

    This is a FastAPI dependency. Use it in any protected route:

        @router.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            ...

    Returns:
        Dict with user_id, role, and token claims.
    """
    if credentials is None:
        raise AuthenticationError(
            message="Authentication required",
            code="MISSING_TOKEN",
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError as exc:
        raise AuthenticationError(
            message="Invalid or expired token",
            code="INVALID_TOKEN",
        ) from exc

    # Validate token type
    token_type = payload.get("type")
    if token_type != "access":
        raise AuthenticationError(
            message="Invalid token type. Use an access token.",
            code="INVALID_TOKEN_TYPE",
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise AuthenticationError(
            message="Token missing required claims",
            code="INVALID_TOKEN_CLAIMS",
        )

    # Set user_id on request state so middleware layers can access it
    if request is not None:
        request.state.user_id = user_id
        request.state.role = role

    return {
        "user_id": user_id,
        "role": role,
        "token_payload": payload,
    }


def require_role(minimum_role: str):
    """Dependency factory: requires the user to have at least the specified role.

    Usage:
        @router.get("/admin")
        async def admin_only(current_user: dict = Depends(require_role("admin"))):
            ...
    """

    async def role_checker(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if not has_role(current_user["role"], minimum_role):
            raise AuthorizationError(
                message=f"Role '{current_user['role']}' does not meet minimum requirement '{minimum_role}'",
                required_role=minimum_role,
            )
        return current_user

    return role_checker


def require_permission(permission: str):
    """Dependency factory: requires the user to have a specific permission.

    Usage:
        @router.get("/audit-logs")
        async def view_audit(
            current_user: dict = Depends(require_permission("audit:read")),
        ):
            ...
    """

    async def permission_checker(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if not has_permission(current_user["role"], permission):
            raise AuthorizationError(
                message=f"Permission '{permission}' required",
                required_permission=permission,
            )
        return current_user

    return permission_checker


def require_active_user(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Verify the user account is active (not disabled)."""
    # In production, this would check the database for is_active status
    # For now, rely on token validity
    return current_user