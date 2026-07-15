"""Application exception hierarchy and error handling."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str = "resource",
        resource_id: str | None = None,
    ) -> None:
        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class DuplicateError(AppException):
    """Resource already exists."""

    def __init__(
        self,
        message: str = "Resource already exists",
        resource_type: str = "resource",
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        details: dict[str, Any] = {"resource_type": resource_type}
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        super().__init__(
            message=message,
            code="DUPLICATE_RESOURCE",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationError(AppException):
    """Request validation failure."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"errors": errors or []},
        )


class AuthenticationError(AppException):
    """Authentication failure."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"scheme": "Bearer"},
        )


class AuthorizationError(AppException):
    """Insufficient permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_role: str | None = None,
        required_permission: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if required_role:
            details["required_role"] = required_role
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after_seconds: int = 60,
    ) -> None:
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after_seconds},
        )


class ServiceUnavailableError(AppException):
    """External dependency unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service: str = "unknown",
    ) -> None:
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service},
        )


# ── FastAPI Exception Handler ───────────────────────────────────────

STANDARD_ERROR_RESPONSE = {
    "error": {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "details": {},
        "request_id": "",
        "timestamp": "",
    }
}


def app_exception_to_http(exc: AppException) -> HTTPException:
    """Convert an AppException to a FastAPI HTTPException."""
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )